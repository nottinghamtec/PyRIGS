import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertRedirects

from assets import models
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db


def upload(client, data, name="results.sss"):
    return client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, data)}, follow=True)


def messages_of(response):
    return [str(m) for m in response.context["messages"]]


@pytest.fixture
def pat_asset(test_asset):
    test_asset.asset_id = "4334"
    test_asset.save()
    return test_asset


def test_upload_imports_matched_results(admin_client, pat_asset):
    data = b.sss_file(b.test_result(asset_id="4334"), b.test_result(asset_id="9999"))
    response = upload(admin_client, data)

    batch = models.PATTestBatch.objects.get()
    assertRedirects(response, reverse("pat_batch_detail", kwargs={"pk": batch.pk}))
    assert batch.unmatched_asset_ids == ["9999"]
    assert batch.machine_serial == "31S-0387"
    assert batch.uploaded_by.is_superuser
    record = batch.records.get()
    assert record.asset == pat_asset
    assert record.passed is True
    assert record.tested_at == timezone.make_aware(datetime.datetime(2025, 9, 28, 20, 3, 34))
    assert record.next_full_test_date == datetime.date(2026, 9, 28)
    assert record.details["steps"][0]["kind"] == "IEC lead continuity"
    assert any("Imported 1" in m for m in messages_of(response))
    assert any("don't exist in RIGS" in m for m in messages_of(response))


def test_asset_ids_are_normalised_when_matching(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(asset_id=" 4334 ")))
    assert models.PATTestRecord.objects.filter(asset=pat_asset).count() == 1


def test_identical_file_is_rejected(admin_client, pat_asset):
    data = b.sss_file(b.test_result())
    upload(admin_client, data)
    response = upload(admin_client, data)
    assert "already been uploaded" in response.context["form"].errors["file"][0]
    assert models.PATTestBatch.objects.count() == 1


def test_overlapping_results_are_skipped(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()))
    later = b.test_result(tested_at=datetime.datetime(2026, 1, 1, 9, 0, 0))
    response = upload(admin_client, b.sss_file(b.test_result(), later))
    assert models.PATTestRecord.objects.count() == 2
    assert any("Skipped 1" in m for m in messages_of(response))


@pytest.mark.parametrize(
    "name,data,error",
    [
        ("results.txt", b.sss_file(), "Please upload a .sss file"),
        ("results.sss", b"garbage", "Couldn't read that file"),
        ("results.sss", b.sss_file()[:-5], "Couldn't read that file"),
    ],
)
def test_invalid_uploads_are_rejected(admin_client, name, data, error):
    response = upload(admin_client, data, name)
    assert error in response.context["form"].errors["file"][0]
    assert not models.PATTestBatch.objects.exists()


def test_oversized_upload_is_rejected(admin_client, settings):
    settings.PAT_MAX_UPLOAD_BYTES = 10
    response = upload(admin_client, b.sss_file())
    assert "too large" in response.context["form"].errors["file"][0]


def test_download_returns_original_file(admin_client, pat_asset):
    data = b.sss_file(b.test_result())
    upload(admin_client, data, "march.sss")
    batch = models.PATTestBatch.objects.get()
    response = admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk}))
    assert b"".join(response.streaming_content) == data
    assert 'attachment; filename="march.sss"' in response["Content-Disposition"]


def test_stored_filename_does_not_use_upload_name(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()), "../../evil name.sss")
    batch = models.PATTestBatch.objects.get()
    assert batch.file.name.startswith("pat/")
    assert "evil" not in batch.file.name


def test_views_require_permission(client, django_user_model, pat_asset):
    user = django_user_model.objects.create_user(username="nobody", password="x")
    client.force_login(user)
    batch = models.PATTestBatch.objects.create(original_filename="a.sss", sha256="0" * 64, file="pat/a.sss")
    for name, kwargs in [
        ("pat_upload", {}),
        ("pat_batch_list", {}),
        ("pat_batch_detail", {"pk": batch.pk}),
        ("pat_batch_download", {"pk": batch.pk}),
        ("pat_batch_reprocess", {"pk": batch.pk}),
    ]:
        assert client.get(reverse(name, kwargs=kwargs)).status_code == 403
    assert client.post(reverse("pat_batch_reprocess", kwargs={"pk": batch.pk})).status_code == 403


def test_views_require_login(client):
    response = client.get(reverse("pat_batch_list"))
    assert response.status_code == 302
    assert "login" in response.url


def test_batch_pages_render(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(), b.test_result(asset_id="9999")))
    batch = models.PATTestBatch.objects.get()
    assert admin_client.get(reverse("pat_batch_list")).status_code == 200
    response = admin_client.get(reverse("pat_batch_detail", kwargs={"pk": batch.pk}))
    assert b"9999" in response.content
    assert pat_asset.asset_id.encode() in response.content


def test_asset_detail_shows_pat_status(admin_client, pat_asset):
    url = reverse("asset_detail", kwargs={"pk": pat_asset.asset_id})
    assert b"Never PAT tested" in admin_client.get(url).content
    upload(admin_client, b.sss_file(b.test_result(passed=False, steps=[b.polarity(False)])))
    assert b"Failed PAT" in admin_client.get(url).content


def record(passed=True, due=None):
    return models.PATTestRecord(tested_at=timezone.now(), passed=passed, next_full_test_date=due)


def test_pat_status_flags():
    today = timezone.localdate()
    tomorrow = today + datetime.timedelta(days=1)
    yesterday = today - datetime.timedelta(days=1)
    status_for = models.PATTestRecord.status_for
    assert status_for(None) == models.PATTestRecord.NOT_TESTED
    assert status_for(record(passed=False, due=tomorrow)) == models.PATTestRecord.FAILED
    assert status_for(record(due=yesterday)) == models.PATTestRecord.OVERDUE
    assert status_for(record(due=today)) == models.PATTestRecord.IN_DATE
    assert status_for(record(due=tomorrow)) == models.PATTestRecord.IN_DATE
    assert status_for(record(due=None)) == models.PATTestRecord.IN_DATE
    assert status_for(record(passed=None, due=tomorrow)) == models.PATTestRecord.IN_DATE


def test_asset_pat_status_uses_latest_test(pat_asset, admin_client):
    batch = models.PATTestBatch.objects.create(original_filename="a.sss", sha256="1" * 64, file="pat/a.sss")
    old = timezone.now() - datetime.timedelta(days=400)
    models.PATTestRecord.objects.create(batch=batch, asset=pat_asset, tested_at=old, passed=False)
    assert pat_asset.pat_status == models.PATTestRecord.FAILED
    models.PATTestRecord.objects.create(
        batch=batch,
        asset=pat_asset,
        tested_at=timezone.now(),
        passed=True,
        next_full_test_date=timezone.localdate() + datetime.timedelta(days=30),
    )
    assert pat_asset.pat_status == models.PATTestRecord.IN_DATE


def failed_result(**kwargs):
    return b.test_result(
        passed=False,
        steps=[b.lead_continuity(), b.insulation(mohm=30, exponent=2, passed=False, less_than=True), b.polarity(False)],
        visuals=[b.visual("Plug"), b.visual("Flex", passed=False)],
        **kwargs,
    )


def test_failure_reasons_and_notes(admin_client, pat_asset):
    upload(admin_client, b.sss_file(failed_result(comments="Bent pin"), b.test_result(asset_id="9999")))
    record = models.PATTestRecord.objects.get()
    assert record.failure_reasons == [
        "Visual check failed: Flex",
        "Failed: Insulation (voltage 500 V, resistance <0.30 Mohm)",
        "Failed: Polarity",
    ]
    assert record.notes == ["Bent pin"]


def test_program_prompts_are_not_notes(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(comments="8", steps=[b.comment("Change Connector"), b.polarity()])))
    record = models.PATTestRecord.objects.get()
    assert record.failure_reasons == []
    assert record.notes == ["8"]


def test_repeated_tests_say_which_repeat_failed(admin_client, pat_asset):
    steps = []
    for passed in (True, True, False, True):
        steps += [b.polarity(passed), b.lead_continuity(), b.comment("Change Connector")]
    upload(admin_client, b.sss_file(b.test_result(passed=False, steps=steps)))
    record = models.PATTestRecord.objects.get()
    assert record.failure_reasons == ["Failed: Polarity [3 of 4]"]


def test_failure_reasons_are_shown_on_asset_and_batch_pages(admin_client, pat_asset):
    upload(admin_client, b.sss_file(failed_result()))
    batch = models.PATTestBatch.objects.get()
    for url in [
        reverse("asset_detail", kwargs={"pk": pat_asset.asset_id}),
        reverse("pat_batch_detail", kwargs={"pk": batch.pk}),
    ]:
        content = admin_client.get(url).content.decode()
        assert "Failed: Polarity" in content
        assert "Visual check failed: Flex" in content


def test_failure_reasons_tolerate_missing_details():
    assert models.PATTestRecord().failure_reasons == []
    assert models.PATTestRecord().notes == []


def test_overlapping_date_ranges_only_import_new_results(admin_client, pat_asset):
    def result(month, day):
        return b.test_result(asset_id="4334", tested_at=datetime.datetime(2025, month, day, 10, 0, 0))

    upload(admin_client, b.sss_file(result(10, 5), result(10, 20), result(11, 3)), "oct-nov.sss")
    response = upload(admin_client, b.sss_file(result(11, 3), result(11, 20), result(12, 1)), "nov-dec.sss")

    assert models.PATTestRecord.objects.count() == 5
    first, second = models.PATTestBatch.objects.order_by("id")
    assert first.records.count() == 3
    assert second.records.count() == 2
    assert any("Imported 2" in m for m in messages_of(response))
    assert any("Skipped 1" in m for m in messages_of(response))


WHEN = datetime.datetime(2025, 11, 3, 10, 0, 0)


def reprocess(client, batch, accept=None):
    data = {"accept": accept} if accept else {}
    return client.post(reverse("pat_batch_reprocess", kwargs={"pk": batch.pk}), data, follow=True)


def test_file_with_nothing_new_is_not_stored(admin_client, pat_asset):
    first = b.sss_file(b.test_result(tested_at=WHEN))
    upload(admin_client, first)
    response = upload(
        admin_client, b.sss_file(b.test_result(tested_at=WHEN), b.test_result(asset_id="NOPE")), "again.sss"
    )

    assertRedirects(response, reverse("pat_upload"))
    assert models.PATTestBatch.objects.count() == 1
    assert any("Nothing was imported" in m for m in messages_of(response))
    assert any("upload the file again" in m for m in messages_of(response))


def test_all_unmatched_file_can_be_uploaded_again_once_assets_exist(admin_client, test_asset):
    data = b.sss_file(b.test_result(asset_id="4334"))
    upload(admin_client, data)
    assert not models.PATTestBatch.objects.exists()

    test_asset.asset_id = "4334"
    test_asset.save()
    upload(admin_client, data)
    assert models.PATTestRecord.objects.filter(asset=test_asset).count() == 1


def test_rejected_duplicate_links_to_existing_upload(admin_client, pat_asset):
    data = b.sss_file(b.test_result(), b.test_result(asset_id="NOPE"))
    upload(admin_client, data)
    response = upload(admin_client, data)
    assert response.context["form"].existing_batch == models.PATTestBatch.objects.get()
    assert b"View that upload" in response.content


def test_same_time_different_result_is_flagged_not_overwritten(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(tested_at=WHEN)))
    response = upload(admin_client, b.sss_file(failed_result(tested_at=WHEN)), "corrected.sss")

    record = models.PATTestRecord.objects.get()
    assert record.passed is True
    batch = models.PATTestBatch.objects.get(original_filename="corrected.sss")
    assert batch.records.count() == 0
    assert [(c["asset_id"], c["existing"], c["new"], c["differs"]) for c in batch.conflicts] == [
        ("4334", "Pass", "Fail", "result")
    ]
    assert any("different outcome" in m for m in messages_of(response))
    assert b"Replace recorded result" in response.content


def test_same_result_but_different_readings_is_a_conflict(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(tested_at=WHEN)))
    upload(admin_client, b.sss_file(b.test_result(tested_at=WHEN, steps=[b.polarity()])), "readings.sss")
    batch = models.PATTestBatch.objects.get(original_filename="readings.sss")
    assert batch.conflicts[0]["differs"] == "readings"


def test_conflict_can_be_accepted(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(tested_at=WHEN)))
    upload(admin_client, b.sss_file(failed_result(tested_at=WHEN)), "corrected.sss")
    batch = models.PATTestBatch.objects.get(original_filename="corrected.sss")

    response = reprocess(admin_client, batch, accept=batch.conflicts[0]["key"])

    record = models.PATTestRecord.objects.get()
    assert record.passed is False
    assert record.batch == batch
    assert "Failed: Polarity" in record.failure_reasons
    batch.refresh_from_db()
    assert batch.conflicts == []
    assert any("Replaced 1" in m for m in messages_of(response))


def test_accepting_an_unknown_conflict_changes_nothing(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(tested_at=WHEN)))
    upload(admin_client, b.sss_file(failed_result(tested_at=WHEN)), "corrected.sss")
    batch = models.PATTestBatch.objects.get(original_filename="corrected.sss")

    response = reprocess(admin_client, batch, accept="4334|2000-01-01T00:00:00+00:00")

    assert models.PATTestRecord.objects.get().passed is True
    assert any("no longer exists" in m for m in messages_of(response))


def test_rematch_imports_results_for_assets_created_since(admin_client, pat_asset, make_asset):
    upload(admin_client, b.sss_file(b.test_result(), b.test_result(asset_id="7777")))
    batch = models.PATTestBatch.objects.get()
    assert batch.unmatched_asset_ids == ["7777"]
    make_asset("7777")

    response = reprocess(admin_client, batch)

    batch.refresh_from_db()
    assert batch.unmatched_asset_ids == []
    assert batch.records.count() == 2
    assert any("Imported 1" in m for m in messages_of(response))

    again = reprocess(admin_client, batch)
    assert models.PATTestRecord.objects.count() == 2
    assert any("Nothing new" in m for m in messages_of(again))


def test_rematch_keeps_still_missing_assets_listed(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(), b.test_result(asset_id="7777")))
    batch = models.PATTestBatch.objects.get()
    reprocess(admin_client, batch)
    batch.refresh_from_db()
    assert batch.unmatched_asset_ids == ["7777"]


def test_duplicate_within_one_file_is_imported_once(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(tested_at=WHEN), b.test_result(tested_at=WHEN)))
    assert models.PATTestRecord.objects.count() == 1
