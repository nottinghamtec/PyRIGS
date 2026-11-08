import datetime

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from reversion.models import Revision, Version

from assets import models
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db


def upload(client, data, name="results.sss"):
    return client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, data)}, follow=True)


def result(day, asset_id="4334", **kwargs):
    return b.test_result(asset_id=asset_id, tested_at=datetime.datetime(2025, 11, day, 10, 0, 0), **kwargs)


def delete_url(batch):
    return reverse("pat_batch_delete", kwargs={"pk": batch.pk})


def delete(client, batch, reason="Wrong tester settings"):
    return client.post(delete_url(batch), {"reason": reason}, follow=True)


@pytest.fixture
def two_uploads(admin_client, pat_asset, make_asset):
    make_asset("5555")
    upload(admin_client, b.sss_file(result(1), result(2, "5555")), "first.sss")
    upload(admin_client, b.sss_file(result(3), result(4, "5555")), "second.sss")
    first, second = models.PATTestBatch.objects.order_by("id")
    return first, second


def user_with(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user(username="someone", password="x")
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    client.force_login(user)
    return user


def test_the_confirmation_page_says_what_will_go_and_deletes_nothing(admin_client, two_uploads):
    first, _ = two_uploads
    response = admin_client.get(delete_url(first))
    content = response.content.decode()
    assert response.status_code == 200
    assert "first.sss" in content
    assert "2 results" in content
    assert "2 assets" in content
    assert "stays in storage" in content
    assert models.PATTestBatch.objects.count() == 2
    assert models.PATTestRecord.objects.count() == 4


def test_the_confirmation_page_lists_assets_that_would_be_left_untested(admin_client, pat_asset, make_asset):
    make_asset("5555")
    upload(admin_client, b.sss_file(result(1), result(2, "5555")), "first.sss")
    upload(admin_client, b.sss_file(result(3)), "second.sss")
    first, second = models.PATTestBatch.objects.order_by("id")
    content_first = admin_client.get(delete_url(first)).content.decode()
    assert "1 asset</strong> would have no PAT results left" in content_first
    assert "5555" in content_first
    assert "would have no PAT results left" not in admin_client.get(delete_url(second)).content.decode()


def test_a_reason_is_required(admin_client, two_uploads):
    first, _ = two_uploads
    response = delete(admin_client, first, reason="   ")
    assert "This field is required" in response.content.decode()
    assert models.PATTestBatch.objects.count() == 2
    assert not Revision.objects.filter(comment__startswith="Deleted PAT results").exists()


def test_deleting_removes_the_upload_and_only_its_results(admin_client, two_uploads, pat_asset):
    first, second = two_uploads
    response = delete(admin_client, first)

    assert models.PATTestBatch.objects.get() == second
    assert models.PATTestRecord.objects.count() == 2
    assert {r.batch_id for r in models.PATTestRecord.objects.all()} == {second.pk}
    assert any("Deleted first.sss and its 2 results" in str(m) for m in response.context["messages"])
    assert response.redirect_chain[-1][0] == reverse("pat_batch_list")


def test_an_assets_status_goes_back_to_its_latest_remaining_result(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result(1)), "old.sss")
    upload(admin_client, b.sss_file(result(2, passed=False, steps=[b.polarity(False)])), "new.sss")
    assert pat_asset.pat_status == models.PATTestRecord.FAILED
    new = models.PATTestBatch.objects.get(original_filename="new.sss")
    delete(admin_client, new)
    assert pat_asset.pat_status != models.PATTestRecord.FAILED
    assert pat_asset.pat_tests.count() == 1


def test_the_original_file_is_kept(admin_client, two_uploads):
    first, _ = two_uploads
    name = first.file.name
    delete(admin_client, first)
    assert default_storage.exists(name)


def test_the_deletion_is_audited(admin_client, two_uploads):
    first, _ = two_uploads
    record_ids = [str(pk) for pk in first.records.values_list("pk", flat=True)]
    delete(admin_client, first, reason="  Wrong   tester\nsettings ")

    revision = Revision.objects.get(comment__startswith="Deleted PAT results")
    assert revision.user.is_superuser
    assert revision.comment == "Deleted PAT results first.sss (2 results): Wrong tester settings"
    kinds = {v.content_type.model for v in revision.version_set.all()}
    assert kinds == {"pattestbatch", "pattestrecord"}
    assert {v.object_id for v in revision.version_set.filter(content_type__model="pattestrecord")} == set(record_ids)
    snapshot = revision.version_set.get(content_type__model="pattestbatch").serialized_data
    assert "first.sss" in snapshot
    assert "program_steps" in revision.version_set.filter(content_type__model="pattestrecord").first().serialized_data


def test_deletions_show_in_the_activity_table_and_feed_without_a_dead_link(admin_client, two_uploads):
    first, _ = two_uploads
    delete(admin_client, first, reason="Wrong tester settings")
    table = admin_client.get(reverse("assets_activity_table")).content.decode()
    feed = admin_client.get(reverse("activity_feed")).content.decode()
    for content in (table, feed):
        assert "Deleted PAT results first.sss (2 results): Wrong tester settings" in content
    assert f'href="/assets/pat/{first.pk}/"' not in table.split("Deleted PAT results")[0].split("<tr>")[-1]
    assert "PATTestRecord" not in table


def test_the_deletion_appears_in_each_affected_assets_history(admin_client, two_uploads, pat_asset):
    first, _ = two_uploads
    delete(admin_client, first, reason="Wrong tester settings")
    response = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id}))
    content = response.content.decode()
    assert response.status_code == 200
    assert "PAT test deleted" in content
    assert "Deleted PAT results first.sss (2 results): Wrong tester settings" in content
    # the earlier history of the deleted result is still there, and its details still open
    assert content.count('class="collapse"') == 2  # the surviving result and the deleted one's original entry
    assert "an upload that has since been deleted" in content


def test_another_assets_history_has_only_its_own_deletion(admin_client, two_uploads, make_asset):
    first, _ = two_uploads
    other = make_asset("6666")
    delete(admin_client, first)
    content = admin_client.get(reverse("asset_history", kwargs={"pk": other.asset_id})).content.decode()
    assert "PAT test deleted" not in content


def test_asset_ids_that_share_a_prefix_are_not_confused(admin_client, pat_asset):
    revision = Revision.objects.create(date_created=timezone.now(), comment="Uploaded PAT results x.sss")
    record_type = ContentType.objects.get_for_model(models.PATTestRecord)
    # one asset whose database id is the other's followed by a digit
    for object_id, asset_pk in (("9001", pat_asset.pk), ("9002", int(f"{pat_asset.pk}0"))):
        Version.objects.create(
            revision=revision,
            object_id=object_id,
            content_type=record_type,
            db="default",
            format="json",
            serialized_data=(
                f'[{{"model": "assets.pattestrecord", "pk": {object_id}, "fields": '
                f'{{"asset": {asset_pk}, "passed": true, "details": {{}}}}}}]'
            ),
            object_repr="x",
        )
    response = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id}))
    record_versions = {v.object_id for v in response.context["object_list"] if v.content_type_id == record_type.pk}
    assert record_versions == {"9001"}


def test_only_users_with_the_delete_permission_can_delete(client, django_user_model, two_uploads):
    first, _ = two_uploads
    user_with(client, django_user_model, "view_pattestbatch", "add_pattestbatch")
    assert client.get(delete_url(first)).status_code == 403
    assert client.post(delete_url(first), {"reason": "x"}).status_code == 403
    assert models.PATTestBatch.objects.count() == 2


def test_a_user_with_the_delete_permission_can(client, django_user_model, two_uploads):
    first, _ = two_uploads
    user_with(client, django_user_model, "delete_pattestbatch")
    assert client.get(delete_url(first)).status_code == 200
    client.post(delete_url(first), {"reason": "Duplicate"})
    assert models.PATTestBatch.objects.count() == 1


def test_anonymous_users_are_sent_to_log_in(client, two_uploads):
    first, _ = two_uploads
    response = client.get(delete_url(first))
    assert response.status_code == 302
    assert "login" in response.url


def test_the_delete_button_only_shows_with_the_permission(client, django_user_model, admin_client, two_uploads):
    first, _ = two_uploads
    url = reverse("pat_batch_detail", kwargs={"pk": first.pk})
    assert "Delete Upload" in admin_client.get(url).content.decode()
    user_with(client, django_user_model, "view_pattestbatch")
    assert "Delete Upload" not in client.get(url).content.decode()


def test_deleting_a_missing_upload_is_a_404(admin_client):
    assert admin_client.get(reverse("pat_batch_delete", kwargs={"pk": 99999})).status_code == 404


def test_deleting_an_upload_with_only_conflicts_works(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result(3)), "first.sss")
    upload(admin_client, b.sss_file(result(3, passed=False, steps=[b.polarity(False)])), "conflicting.sss")
    batch = models.PATTestBatch.objects.get(original_filename="conflicting.sss")
    assert batch.records.count() == 0
    delete(admin_client, batch)
    assert models.PATTestBatch.objects.count() == 1
    assert Revision.objects.filter(comment__contains="conflicting.sss (0 results)").exists()


def test_timestamps_are_recent(admin_client, two_uploads):
    first, _ = two_uploads
    delete(admin_client, first)
    revision = Revision.objects.get(comment__startswith="Deleted PAT results")
    assert timezone.now() - revision.date_created < datetime.timedelta(minutes=1)


def test_earlier_entries_for_a_deleted_upload_have_no_dead_link_or_count(admin_client, two_uploads):
    first, second = two_uploads
    delete(admin_client, first)
    table = admin_client.get(reverse("assets_activity_table")).content.decode()
    feed = admin_client.get(reverse("activity_feed")).content.decode()
    for content in (table, feed):
        assert "first.sss (since deleted)" in content or "(since deleted)" in content
        assert f'href="/assets/pat/{first.pk}/"' not in content
        assert f'href="/assets/pat/{second.pk}/"' in content
    assert "(2 imported)" in table


def test_deletions_have_no_icons_in_the_feeds_or_history(admin_client, two_uploads, pat_asset):
    first, _ = two_uploads
    delete(admin_client, first)
    for url in (
        reverse("assets_activity_table"),
        reverse("activity_feed"),
        reverse("asset_history", kwargs={"pk": pat_asset.asset_id}),
    ):
        assert "fa-trash" not in admin_client.get(url).content.decode()
