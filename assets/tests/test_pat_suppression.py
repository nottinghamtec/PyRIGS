import datetime
from io import StringIO

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils.html import escape
from reversion.models import Revision, Version

from assets import models
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db


def upload(client, data, name="results.sss"):
    return client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, data)}, follow=True)


def result(day, asset_id="4334", **kwargs):
    return b.test_result(asset_id=asset_id, tested_at=datetime.datetime(2025, 11, day, 10, 0, 0), **kwargs)


def failed(day, asset_id="4334"):
    return result(day, asset_id, passed=False, steps=[b.polarity(False)])


def suppress_url(record):
    return reverse("pat_result_suppress", kwargs={"pk": record.pk})


def restore_url(record):
    return reverse("pat_result_restore", kwargs={"pk": record.pk})


def suppress(client, record, reason="Entered against the wrong asset", **extra):
    return client.post(suppress_url(record), {"reason": reason, **extra}, follow=True)


def record_on(day, asset_id="4334"):
    return models.PATTestRecord.objects.get(asset__asset_id=asset_id, tested_at__day=day)


def user_with(client, django_user_model, *codenames, username="someone"):
    user = django_user_model.objects.create_user(username=username, password="x", first_name="Sam", last_name="Wrong")
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    client.force_login(user)
    return user


@pytest.fixture
def history(admin_client, pat_asset):
    """An older pass and a newer fail on one asset"""
    upload(admin_client, b.sss_file(result(1), failed(2)), "results.sss")
    return record_on(1), record_on(2)


def test_the_confirmation_page_says_what_will_change_and_changes_nothing(admin_client, history):
    old_pass, new_fail = history
    response = admin_client.get(suppress_url(new_fail))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Failed PAT" in content  # what the asset shows now
    assert "PAT in date" in content or "PAT overdue" in content  # what it would show without this result
    assert not models.PATTestRecord.objects.get(pk=new_fail.pk).is_suppressed


def test_a_reason_is_required(admin_client, history):
    _, new_fail = history
    response = suppress(admin_client, new_fail, reason="   ")
    assert "This field is required" in response.content.decode()
    assert not models.PATTestRecord.objects.get(pk=new_fail.pk).is_suppressed
    assert not Revision.objects.filter(comment__startswith="Suppressed").exists()


def test_suppressing_records_who_when_and_why(admin_client, admin_user, history):
    _, new_fail = history
    response = suppress(admin_client, new_fail, reason="  Entered   against the\nwrong asset ")
    new_fail.refresh_from_db()
    assert new_fail.is_suppressed
    assert new_fail.suppressed_by == admin_user
    assert new_fail.suppressed_reason == "Entered against the wrong asset"
    assert (datetime.datetime.now(datetime.UTC) - new_fail.suppressed_at).total_seconds() < 60
    assert any("Suppressed the PAT result" in str(m) for m in response.context["messages"])
    assert response.redirect_chain[-1][0] == reverse("asset_detail", kwargs={"pk": "4334"})


def test_a_suppressed_result_stops_counting_towards_the_status(admin_client, history, pat_asset):
    _, new_fail = history
    assert pat_asset.pat_status == models.PATTestRecord.FAILED
    suppress(admin_client, new_fail)
    # the older pass takes over
    assert pat_asset.latest_pat_test.pk != new_fail.pk
    assert pat_asset.pat_status != models.PATTestRecord.FAILED


def test_an_asset_with_only_suppressed_results_is_untested(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result(1)))
    suppress(admin_client, record_on(1))
    assert pat_asset.latest_pat_test is None
    assert pat_asset.pat_status == models.PATTestRecord.NOT_TESTED


def test_the_asset_list_and_filters_ignore_suppressed_results(admin_client, history, pat_asset):
    _, new_fail = history

    def ids(**params):
        response = admin_client.get(reverse("asset_list"), params)
        return [a.asset_id for a in response.context["object_list"]]

    assert ids(pat_status="failed") == ["4334"]
    suppress(admin_client, new_fail)
    assert ids(pat_status="failed") == []
    assert ids(pat_status="never") == []  # the older pass still counts
    suppress(admin_client, models.PATTestRecord.objects.get(tested_at__day=1))
    assert ids(pat_status="never") == ["4334"]
    status = admin_client.get(reverse("asset_list")).context["object_list"][0].pat_status
    assert status == models.PATTestRecord.NOT_TESTED


def test_it_stays_listed_marked_with_the_reason_and_who(admin_client, admin_user, history, pat_asset):
    _, new_fail = history
    suppress(admin_client, new_fail, reason="Wrong asset, it was 4335")
    content = admin_client.get(reverse("asset_detail", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert content.count("pat-summary") >= 2  # both results are still listed
    assert "pat-suppressed" in content
    assert "Suppressed" in content
    assert "Wrong asset, it was 4335" in content
    assert escape(admin_user.name) in content
    assert "Why it failed" in content  # the original result is still there to read


def test_the_asset_page_status_ignores_a_suppressed_result(admin_client, history, pat_asset):
    _, new_fail = history
    suppress(admin_client, new_fail)
    response = admin_client.get(reverse("asset_detail", kwargs={"pk": pat_asset.asset_id}))
    assert response.context["pat_status"] != models.PATTestRecord.FAILED


def test_suppression_is_audited_in_the_assets_history(admin_client, admin_user, history, pat_asset):
    _, new_fail = history
    suppress(admin_client, new_fail, reason="Wrong asset")
    revision = Revision.objects.get(comment__startswith="Suppressed PAT result")
    assert revision.comment == "Suppressed PAT result for 4334: Wrong asset"
    assert revision.user == admin_user
    version = revision.version_set.get()
    assert '"suppressed_reason": "Wrong asset"' in version.serialized_data

    content = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert "Suppressed by" in content
    assert "Wrong asset" in content
    assert "Suppress this result" not in content  # a snapshot isn't somewhere to act from


def test_restoring_makes_it_count_again_and_keeps_the_history(admin_client, history, pat_asset):
    _, new_fail = history
    suppress(admin_client, new_fail)
    response = admin_client.post(restore_url(new_fail), follow=True)
    new_fail.refresh_from_db()
    assert not new_fail.is_suppressed
    assert new_fail.suppressed_by is None
    assert new_fail.suppressed_reason == ""
    assert pat_asset.pat_status == models.PATTestRecord.FAILED
    assert any("Restored the PAT result" in str(m) for m in response.context["messages"])
    assert Version.objects.get_for_object(new_fail).count() == 3  # imported, suppressed, restored

    content = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert "Restored" in content
    assert Revision.objects.filter(comment="Restored PAT result for 4334").exists()


def test_the_restore_page_shows_who_suppressed_it_and_the_resulting_status(admin_client, admin_user, history):
    _, new_fail = history
    suppress(admin_client, new_fail, reason="Wrong asset")
    content = admin_client.get(restore_url(new_fail)).content.decode()
    assert "Wrong asset" in content
    assert escape(admin_user.name) in content
    assert "Failed PAT" in content


def test_suppressing_twice_or_restoring_what_is_not_suppressed_does_nothing(admin_client, history):
    old_pass, new_fail = history
    suppress(admin_client, new_fail)
    revisions = Revision.objects.count()
    response = suppress(admin_client, new_fail, reason="Again")
    assert any("already suppressed" in str(m) for m in response.context["messages"])
    assert admin_client.get(suppress_url(new_fail), follow=True).status_code == 200
    response = admin_client.post(restore_url(old_pass), follow=True)
    assert any("isn't suppressed" in str(m) for m in response.context["messages"])
    assert Revision.objects.count() == revisions


def test_only_users_with_the_permission_can_suppress_or_restore(client, django_user_model, history):
    _, new_fail = history
    user_with(client, django_user_model, "view_pattestbatch", "add_pattestbatch")
    for url in (suppress_url(new_fail), restore_url(new_fail)):
        assert client.get(url).status_code == 403
        assert client.post(url, {"reason": "x"}).status_code == 403
    assert not models.PATTestRecord.objects.get(pk=new_fail.pk).is_suppressed


def test_a_user_with_the_permission_can_suppress(client, django_user_model, history):
    _, new_fail = history
    user_with(client, django_user_model, "change_pattestrecord")
    assert client.get(suppress_url(new_fail)).status_code == 200
    client.post(suppress_url(new_fail), {"reason": "Wrong asset"})
    assert models.PATTestRecord.objects.get(pk=new_fail.pk).is_suppressed


def test_anonymous_users_are_sent_to_log_in_and_missing_results_are_404(client, admin_client, history):
    _, new_fail = history
    response = client.get(suppress_url(new_fail))
    assert response.status_code == 302 and "login" in response.url
    assert admin_client.get(reverse("pat_result_suppress", kwargs={"pk": 99999})).status_code == 404
    assert admin_client.get(reverse("pat_result_restore", kwargs={"pk": 99999})).status_code == 404


def test_the_buttons_only_show_with_the_permission(admin_client, client, django_user_model, history, pat_asset):
    _, new_fail = history
    url = reverse("asset_detail", kwargs={"pk": pat_asset.asset_id})
    assert "Suppress this result" in admin_client.get(url).content.decode()
    suppress(admin_client, new_fail)
    assert "Restore this result" in admin_client.get(url).content.decode()
    user_with(client, django_user_model, "view_pattestbatch")
    content = client.get(url).content.decode()
    assert "Suppress this result" not in content and "Restore this result" not in content
    assert "Wrong asset" not in content  # nothing was said about it, but it's still marked
    assert "Suppressed" in content


def test_the_upload_page_marks_suppressed_results_and_returns_there(admin_client, history):
    _, new_fail = history
    batch = models.PATTestBatch.objects.get()
    batch_url = reverse("pat_batch_detail", kwargs={"pk": batch.pk})
    response = admin_client.post(suppress_url(new_fail), {"reason": "Wrong asset", "next": batch_url}, follow=True)
    assert response.redirect_chain[-1][0] == batch_url
    content = response.content.decode()
    assert "pat-suppressed" in content
    assert "Wrong asset" in content


def test_the_return_address_must_be_on_this_site(admin_client, history):
    _, new_fail = history
    response = admin_client.post(
        suppress_url(new_fail), {"reason": "Wrong asset", "next": "https://evil.example/steal"}, follow=True
    )
    assert response.redirect_chain[-1][0] == reverse("asset_detail", kwargs={"pk": "4334"})


def test_uploading_the_same_results_again_does_not_undo_a_suppression(admin_client, history):
    _, new_fail = history
    suppress(admin_client, new_fail)
    upload(admin_client, b.sss_file(failed(2), result(3)), "overlap.sss")
    assert models.PATTestRecord.objects.get(pk=new_fail.pk).is_suppressed
    assert models.PATTestRecord.objects.count() == 3


def test_refreshing_keeps_a_suppression(admin_client, history):
    _, new_fail = history
    suppress(admin_client, new_fail, reason="Wrong asset")
    stale = models.PATTestRecord.objects.get(pk=new_fail.pk)
    stale.details = {k: v for k, v in stale.details.items() if k != "program_steps"}
    stale.save()
    call_command("refresh_pat_results", stdout=StringIO())
    refreshed = models.PATTestRecord.objects.get(pk=new_fail.pk)
    assert "program_steps" in refreshed.details
    assert refreshed.is_suppressed
    assert refreshed.suppressed_reason == "Wrong asset"


def test_suppressing_affects_only_that_result(admin_client, history, make_asset):
    old_pass, new_fail = history
    make_asset("5555")
    suppress(admin_client, new_fail)
    assert not models.PATTestRecord.objects.get(pk=old_pass.pk).is_suppressed
    assert models.PATTestRecord.objects.filter(suppressed_at__isnull=False).count() == 1


def test_a_batch_delete_page_does_not_count_suppressed_results_as_left(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result(1)), "first.sss")
    upload(admin_client, b.sss_file(result(2)), "second.sss")
    first, second = models.PATTestBatch.objects.order_by("id")
    url = reverse("pat_batch_delete", kwargs={"pk": second.pk})
    assert "would have no PAT results left" not in admin_client.get(url).content.decode()
    suppress(admin_client, record_on(1))
    assert "would have no PAT results left" in admin_client.get(url).content.decode()


def test_suppressing_records_on_one_asset_does_not_touch_another_with_the_same_time(
    admin_client, pat_asset, make_asset
):
    make_asset("5555")
    upload(admin_client, b.sss_file(result(1), result(1, "5555")))
    suppress(admin_client, record_on(1, "4334"))
    assert not record_on(1, "5555").is_suppressed
    assert make_asset and models.Asset.objects.get(asset_id="5555").pat_status != models.PATTestRecord.NOT_TESTED
