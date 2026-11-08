import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from reversion.models import Revision, Version

from assets import models
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db

WHEN = datetime.datetime(2025, 11, 3, 10, 0, 0)


def upload(client, data, name="results.sss"):
    return client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, data)}, follow=True)


def reprocess(client, batch, accept=None):
    data = {"accept": accept} if accept else {}
    return client.post(reverse("pat_batch_reprocess", kwargs={"pk": batch.pk}), data, follow=True)


def record_versions():
    ids = [str(pk) for pk in models.PATTestRecord.objects.values_list("pk", flat=True)]
    return Version.objects.filter(object_id__in=ids, content_type__model="pattestrecord")


def test_upload_creates_a_revision_with_the_batch_and_every_record(admin_client, pat_asset, make_asset):
    make_asset("5555")
    upload(admin_client, b.sss_file(b.test_result(), b.test_result(asset_id="5555")), "march.sss")

    revision = Revision.objects.get()
    batch = models.PATTestBatch.objects.get()
    assert revision.comment == "Uploaded PAT results march.sss"
    assert revision.user.is_superuser
    assert Version.objects.get_for_object(batch).count() == 1
    assert record_versions().count() == 2
    assert set(record_versions().values_list("revision_id", flat=True)) == {revision.pk}


def test_nothing_new_makes_no_revision(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()))
    before = Revision.objects.count()
    upload(admin_client, b.sss_file(b.test_result(), b.test_result(asset_id="NOPE")), "again.sss")
    assert Revision.objects.count() == before


def test_asset_history_shows_pat_results_with_full_data(admin_client, pat_asset, make_asset):
    make_asset("5555")
    upload(
        admin_client,
        b.sss_file(
            b.test_result(program="Class 1 Appliance", comments="Bent pin"),
            b.test_result(asset_id="5555", program="Some Other Program"),
        ),
    )
    response = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "PAT test" in content
    assert 'aria-label="Show all test data"' in content
    assert "Class 1 Appliance" in content
    assert "Bent pin" in content
    assert "IEC lead continuity" in content
    assert "0.04" in content
    assert "Some Other Program" not in content
    guid = models.PATTestRecord.objects.get(asset=pat_asset).details["guid"]
    assert guid in content


def test_asset_page_rows_expand_to_all_test_data(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()))
    content = admin_client.get(reverse("asset_detail", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert 'aria-label="Show all test data"' in content
    assert "Electrical tests" in content
    assert "Visual inspection" in content
    assert "Insulation" in content
    assert 'class="collapse" id="pat-' in content


def test_failed_result_in_history_shows_reasons(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(passed=False, steps=[b.polarity(False)])))
    content = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert "Polarity failed" in content


def test_replacing_a_result_keeps_the_old_version_in_history(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(tested_at=WHEN)))
    corrected = b.test_result(tested_at=WHEN, passed=False, steps=[b.polarity(False)])
    upload(admin_client, b.sss_file(corrected), "corrected.sss")
    batch = models.PATTestBatch.objects.get(original_filename="corrected.sss")

    reprocess(admin_client, batch, accept=batch.conflicts[0]["key"])

    record = models.PATTestRecord.objects.get()
    versions = list(Version.objects.get_for_object(record).order_by("revision__date_created"))
    assert len(versions) == 2
    assert versions[0].field_dict["passed"] is True
    assert versions[1].field_dict["passed"] is False
    assert "Replaced PAT results for 4334" in versions[1].revision.comment
    content = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert "Replaced the earlier" in content


def test_rematch_makes_a_revision_only_when_something_changes(admin_client, pat_asset, make_asset):
    upload(admin_client, b.sss_file(b.test_result(), b.test_result(asset_id="7777")))
    batch = models.PATTestBatch.objects.get()
    before = Revision.objects.count()

    reprocess(admin_client, batch)
    assert Revision.objects.count() == before

    make_asset("7777")
    reprocess(admin_client, batch)
    assert Revision.objects.count() == before + 1
    revision = Revision.objects.order_by("-pk").first()
    assert revision.comment == "Re-matched PAT results in results.sss"
    assert Version.objects.get_for_object(batch).count() == 2
    assert record_versions().filter(revision=revision).count() == 1


def test_uploads_appear_in_the_activity_table_but_records_do_not(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()), "march.sss")
    content = admin_client.get(reverse("assets_activity_table")).content.decode()
    assert "Uploaded PAT results" in content
    assert "march.sss" in content
    assert "PATTestRecord" not in content


def test_uploads_appear_in_the_activity_feed(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()), "march.sss")
    content = admin_client.get(reverse("activity_feed")).content.decode()
    assert "Uploaded PAT results" in content
    assert "march.sss" in content
    assert "(1 imported)" in content


def test_other_assets_history_is_unaffected(admin_client, pat_asset, make_asset):
    other = make_asset("6666")
    upload(admin_client, b.sss_file(b.test_result()))
    content = admin_client.get(reverse("asset_history", kwargs={"pk": other.asset_id})).content.decode()
    assert "PAT test" not in content


def test_uploads_are_a_readable_type_in_the_activity_filter(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()), "march.sss")
    content = admin_client.get(reverse("assets_activity_table")).content.decode()
    assert "Portable Appliance Test Upload" in content
    assert "Pat Test Batch" not in content
    filtered = admin_client.get(reverse("assets_activity_table"), {"model": "pattestbatch"})
    assert "march.sss" in filtered.content.decode()


def test_uploads_can_be_exported_with_the_recent_changes(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()), "march.sss")
    response = admin_client.get(reverse("assets_activity_table"), {"export": "csv"})
    body = b"".join(response.streaming_content).decode()
    assert "Portable Appliance Test Upload" in body
    assert "march.sss" in body


def test_an_assets_history_is_a_timeline_that_includes_its_pat_results(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result()), "march.sss")
    response = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id}))
    content = response.content.decode()
    assert response.context["timeline"] is True
    assert "Timeline" in content
    assert "PATTestRecord" in content
    assert "Compare selected versions" in content
