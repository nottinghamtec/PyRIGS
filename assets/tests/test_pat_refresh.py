import datetime
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from reversion.models import Revision, Version

from assets import models
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db

OLD_KEYS = ("program_steps", "standard_visual_checks")


def upload(client, data, name="results.sss"):
    client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, data)})


def make_stale():
    """Make every record look like it was imported before the program was decoded"""
    for record in models.PATTestRecord.objects.all():
        record.details = {key: value for key, value in record.details.items() if key not in OLD_KEYS}
        record.save()


def run(*args):
    out = StringIO()
    call_command("refresh_pat_results", *args, stdout=out)
    return out.getvalue()


def result(day=3, **kwargs):
    kwargs.setdefault("definition", b.program_definition(b.def_continuity(), b.def_insulation(), b.def_polarity()))
    return b.test_result(tested_at=datetime.datetime(2025, 11, day, 10, 0, 0), **kwargs)


def test_stale_records_are_brought_up_to_date(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result()), "march.sss")
    make_stale()
    record = models.PATTestRecord.objects.get()
    assert "program_steps" not in record.details

    output = run()

    record.refresh_from_db()
    assert len(record.details["program_steps"]) == 3
    assert record.has_limits
    assert "march.sss: 1 updated, 0 added" in output
    assert "1 results changed" in output


def test_refresh_keeps_the_old_version_in_history(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result()), "march.sss")
    make_stale()
    run()
    record = models.PATTestRecord.objects.get()
    versions = Version.objects.get_for_object(record)
    assert versions.count() == 2
    assert Revision.objects.order_by("-pk").first().comment == "Refreshed PAT results from march.sss"
    assert Revision.objects.order_by("-pk").first().user is None


def test_dry_run_changes_nothing(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result()), "march.sss")
    make_stale()
    revisions = Revision.objects.count()

    output = run("--dry-run")

    assert "march.sss: 1 updated, 0 added" in output
    assert "1 results would be changed" in output
    assert "program_steps" not in models.PATTestRecord.objects.get().details
    assert Revision.objects.count() == revisions


def test_nothing_to_refresh_makes_no_revision(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result()), "march.sss")
    revisions = Revision.objects.count()
    assert "0 results changed" in run()
    assert Revision.objects.count() == revisions


def test_records_stay_with_the_upload_they_came_from(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result(1), result(2)), "first.sss")
    upload(admin_client, b.sss_file(result(2), result(3)), "second.sss")
    first, second = models.PATTestBatch.objects.order_by("id")
    shared = models.PATTestRecord.objects.get(tested_at__day=2)
    assert shared.batch == first
    make_stale()

    run()

    shared.refresh_from_db()
    assert shared.batch == first
    assert {r.batch_id for r in models.PATTestRecord.objects.filter(tested_at__day=3)} == {second.pk}
    assert all(r.has_limits for r in models.PATTestRecord.objects.all())


def test_a_refresh_does_not_count_as_a_conflict_afterwards(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result()), "march.sss")
    make_stale()
    run()
    batch = models.PATTestBatch.objects.get()
    assert batch.conflicts == []


def test_a_batch_whose_file_is_missing_is_skipped(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result()), "march.sss")
    models.PATTestBatch.objects.create(original_filename="lost.sss", sha256="1" * 64, file="")
    out, err = StringIO(), StringIO()
    call_command("refresh_pat_results", stdout=out, stderr=err)
    assert "lost.sss: skipped" in err.getvalue()
    assert "march.sss: 0 updated, 0 added" in out.getvalue()


def test_dry_run_counts_overlapping_records_once(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result(1), result(2)), "first.sss")
    upload(admin_client, b.sss_file(result(2), result(3)), "second.sss")
    make_stale()
    output = run("--dry-run")
    assert "first.sss: 2 updated" in output
    assert "second.sss: 1 updated" in output
    assert "3 results would be changed" in output


def test_history_says_a_refresh_re_read_the_file_and_was_made_by_the_system(admin_client, pat_asset):
    upload(admin_client, b.sss_file(result()), "march.sss")
    make_stale()
    run()
    content = admin_client.get(reverse("asset_history", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert "Re-read from the file" in content
    assert "Replaced the earlier" not in content
    assert ">System<" in content.replace(" ", "").replace("\n", "")
