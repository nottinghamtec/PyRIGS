import datetime
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from reversion.models import Revision

from assets import models
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db

WHEN = datetime.datetime(2025, 11, 3, 10, 0, 0)


def upload(client, data, name="results.sss"):
    return client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, data)}, follow=True)


def reprocess(client, batch, accept=None):
    data = {"accept": accept} if accept else {}
    return client.post(reverse("pat_batch_reprocess", kwargs={"pk": batch.pk}), data, follow=True)


def theirs(**kwargs):
    return b.test_result(**{"asset_id": "sb 001", "tested_at": WHEN, **kwargs})


def failed(**kwargs):
    return theirs(passed=False, steps=[b.polarity(False)], **kwargs)


def test_results_for_unknown_ids_are_kept_in_full(admin_client):
    upload(admin_client, b.sss_file(theirs(), theirs()))
    result = models.PATUnmatchedResult.objects.get()
    assert result.asset_id == "SB 001"
    assert result.passed is True
    assert result.details["location"] == "Storeroom"
    assert result.display_steps()
    assert result.batch == models.PATTestBatch.objects.get()
    assert not models.PATTestRecord.objects.exists()


def test_results_with_no_id_are_not_kept(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(), theirs(asset_id="  ")))
    assert not models.PATUnmatchedResult.objects.exists()


def test_a_differing_result_for_an_unknown_id_is_a_conflict_that_can_be_accepted(admin_client):
    upload(admin_client, b.sss_file(theirs()))
    response = upload(admin_client, b.sss_file(failed()), "corrected.sss")
    batch = models.PATTestBatch.objects.get(original_filename="corrected.sss")
    assert batch.conflicts[0]["unmatched"] is True
    assert models.PATUnmatchedResult.objects.get().passed is True
    assert "(not in RIGS)" in response.content.decode()

    reprocess(admin_client, batch, accept=batch.conflicts[0]["key"])

    result = models.PATUnmatchedResult.objects.get()
    assert result.passed is False
    assert result.batch == batch
    batch.refresh_from_db()
    assert batch.conflicts == []


def test_the_refresh_command_keeps_results_missing_from_earlier_uploads(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(), theirs()))
    models.PATUnmatchedResult.objects.all().delete()
    revisions = Revision.objects.count()

    output = StringIO()
    call_command("refresh_pat_results", "--dry-run", stdout=output)
    assert "1 results for assets not in RIGS would be kept" in output.getvalue()
    assert not models.PATUnmatchedResult.objects.exists()

    output = StringIO()
    call_command("refresh_pat_results", stdout=output)
    assert "1 results for assets not in RIGS kept" in output.getvalue()
    assert models.PATUnmatchedResult.objects.count() == 1
    assert Revision.objects.count() == revisions


def test_deleting_an_upload_removes_its_unmatched_results_and_says_so(admin_client, pat_asset):
    upload(admin_client, b.sss_file(b.test_result(), theirs()))
    batch = models.PATTestBatch.objects.get()
    url = reverse("pat_batch_delete", kwargs={"pk": batch.pk})
    assert "for IDs that aren't in RIGS" in admin_client.get(url).content.decode()
    admin_client.post(url, {"reason": "Wrong file"})
    assert not models.PATUnmatchedResult.objects.exists()
