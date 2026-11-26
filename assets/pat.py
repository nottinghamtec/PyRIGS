from dataclasses import dataclass, field

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.http import content_disposition_header
from reversion import revisions as reversion

from assets import models
from assets.sss import parse_sss
from versioning.versioning import record_deletions

RESULT_LABELS = {True: "Pass", False: "Fail", None: "Unknown"}


@dataclass
class Plan:
    new: list = field(default_factory=list)
    replacements: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    unmatched: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    new_unmatched: list = field(default_factory=list)


@dataclass
class ImportSummary:
    batch: models.PATTestBatch | None
    imported: list = field(default_factory=list)
    replaced: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    unmatched: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    kept: list = field(default_factory=list)


def normalise_asset_id(raw):
    return raw.strip().upper()


def conflict_key(asset_id, tested_at):
    return f"{asset_id}|{tested_at.isoformat()}"


def record_fields(result):
    return {
        "passed": result.passed,
        "operator": result.operator,
        "comments": result.comments,
        "next_full_test_date": result.next_full_test_date,
        "next_visual_test_date": result.next_visual_test_date,
        "details": result.details(),
    }


def classify(parsed, replace_keys=()):
    """Work out what to do with each result in the file without writing anything."""
    asset_ids = {normalise_asset_id(result.asset_id) for result in parsed.results}
    assets = {asset.asset_id: asset for asset in models.Asset.objects.filter(asset_id__in=asset_ids)}
    existing = {
        (record.asset.asset_id, record.tested_at): record
        for record in models.PATTestRecord.objects.filter(asset__in=assets.values()).select_related("asset")
    }
    existing_unmatched = {
        (result.asset_id, result.tested_at): result
        for result in models.PATUnmatchedResult.objects.filter(asset_id__in=asset_ids - assets.keys())
    }

    plan = Plan()
    seen = set()
    for result in parsed.results:
        asset_id = normalise_asset_id(result.asset_id)
        asset = assets.get(asset_id)
        if asset is None:
            plan.unmatched.append(result.asset_id)
            if not asset_id:
                continue
        tested_at = timezone.make_aware(result.tested_at)
        key = (asset_id, tested_at)
        if key in seen:
            if asset is not None:
                plan.duplicates.append(asset_id)
            continue
        seen.add(key)

        fields = record_fields(result)
        current = existing.get(key) if asset is not None else existing_unmatched.get(key)
        if current is None:
            if asset is not None:
                plan.new.append(models.PATTestRecord(asset=asset, tested_at=tested_at, **fields))
            else:
                plan.new_unmatched.append(models.PATUnmatchedResult(asset_id=asset_id, tested_at=tested_at, **fields))
        elif current.passed == fields["passed"] and current.details == fields["details"]:
            if asset is not None:
                plan.duplicates.append(asset_id)
        elif conflict_key(asset_id, tested_at) in replace_keys:
            plan.replacements.append((current, fields))
        else:
            conflict = {
                "key": conflict_key(asset_id, tested_at),
                "asset_id": asset_id,
                "tested_at": f"{timezone.localtime(tested_at):%d/%m/%Y %H:%M}",
                "existing": RESULT_LABELS[current.passed],
                "new": RESULT_LABELS[fields["passed"]],
                "differs": "result" if current.passed != fields["passed"] else "readings",
            }
            if asset is None:
                conflict["unmatched"] = True
            plan.conflicts.append(conflict)
    return plan


def result_asset_id(result):
    return result.asset.asset_id if isinstance(result, models.PATTestRecord) else result.asset_id


def keep_unmatched(batch, results):
    for result in results:
        result.batch = batch
    models.PATUnmatchedResult.objects.bulk_create(results)


def discard_unmatched(records):
    if not records:
        return
    matches = Q()
    for record in records:
        matches |= Q(asset_id=record.asset.asset_id, tested_at=record.tested_at)
    models.PATUnmatchedResult.objects.filter(matches).delete()


def summarise(plan, batch):
    return ImportSummary(
        batch=batch,
        imported=[record.asset.asset_id for record in plan.new],
        replaced=[result_asset_id(current) for current, _ in plan.replacements],
        duplicates=plan.duplicates,
        unmatched=plan.unmatched,
        conflicts=plan.conflicts,
        kept=[result.asset_id for result in plan.new_unmatched],
    )


def add_records_to_revision(records):
    for record in records:
        reversion.add_to_revision(record)


@transaction.atomic
def import_sss(parsed, content, filename, sha256, user):
    """Import a parsed file. If it has nothing new and no conflicts, nothing is stored and summary.batch is None."""
    plan = classify(parsed)
    if not (plan.new or plan.new_unmatched or plan.conflicts):
        return summarise(plan, None)

    batch = models.PATTestBatch(
        original_filename=filename[:255],
        sha256=sha256,
        machine_model=parsed.machine_model,
        machine_serial=parsed.machine_serial,
        uploaded_by=user,
        unmatched_asset_ids=sorted(set(plan.unmatched)),
        conflicts=plan.conflicts,
    )
    with reversion.create_revision():
        reversion.set_user(user)
        reversion.set_comment(f"Uploaded PAT results {batch.original_filename}")
        batch.file.save(filename, ContentFile(content), save=False)
        batch.save()
        for record in plan.new:
            record.batch = batch
        models.PATTestRecord.objects.bulk_create(plan.new)
        add_records_to_revision(plan.new)
    keep_unmatched(batch, plan.new_unmatched)
    discard_unmatched(plan.new)
    return summarise(plan, batch)


def read_stored(batch):
    with batch.file.open("rb") as stored:
        return parse_sss(stored.read())


def plan_reprocess(batch, accept=None, refresh=False):
    parsed = read_stored(batch)
    plan = classify(parsed, replace_keys={accept} if accept else set())
    if refresh:
        plan = classify(parsed, replace_keys={conflict["key"] for conflict in plan.conflicts})
    return plan


@transaction.atomic
def reprocess(batch, user, accept=None, refresh=False):
    """
    Run the stored file against RIGS again, picking up assets created since the upload.
    If accept is the key of one of the batch's conflicts, that result replaces the one already recorded.
    With refresh, every recorded result that differs from what the file now decodes to is brought up to date
    (after the parser has improved), and each stays attached to the upload it came from.
    Results for asset IDs still not in RIGS are kept for export if they aren't already.
    No revision is made unless something recorded in RIGS changed.
    """
    plan = plan_reprocess(batch, accept, refresh)
    record_replacements = [(c, f) for c, f in plan.replacements if isinstance(c, models.PATTestRecord)]
    unmatched_replacements = [(c, f) for c, f in plan.replacements if isinstance(c, models.PATUnmatchedResult)]

    unmatched = sorted(set(plan.unmatched))
    if (
        plan.new
        or record_replacements
        or unmatched_replacements
        or unmatched != batch.unmatched_asset_ids
        or plan.conflicts != batch.conflicts
    ):
        with reversion.create_revision():
            if user is not None:
                reversion.set_user(user)
            if refresh:
                reversion.set_comment(f"Refreshed PAT results from {batch.original_filename}")
            elif plan.replacements:
                assets = ", ".join(result_asset_id(current) for current, _ in plan.replacements)
                reversion.set_comment(
                    f"Replaced PAT results for {assets} with the version in {batch.original_filename}"
                )
            else:
                reversion.set_comment(f"Re-matched PAT results in {batch.original_filename}")
            for record in plan.new:
                record.batch = batch
            models.PATTestRecord.objects.bulk_create(plan.new)
            add_records_to_revision(plan.new)
            for current, fields in record_replacements:
                apply_replacement(current, fields, batch, refresh)
            batch.unmatched_asset_ids = unmatched
            batch.conflicts = plan.conflicts
            batch.save(update_fields=["unmatched_asset_ids", "conflicts"])

    keep_unmatched(batch, plan.new_unmatched)
    for current, fields in unmatched_replacements:
        apply_replacement(current, fields, batch, refresh)
    discard_unmatched(plan.new)
    return summarise(plan, batch)


def apply_replacement(current, fields, batch, refresh):
    for name, value in fields.items():
        setattr(current, name, value)
    if not refresh:
        current.batch = batch
    current.save()


@transaction.atomic
def delete_batch(batch, user, reason):
    """
    Delete an upload and the results imported from it, keeping a revision that records who did it and why,
    with a snapshot of the upload and of every result. The stored file is kept.
    """
    records = list(batch.records.select_related("asset"))
    record_deletions(
        [batch, *records], f"PAT results {batch.original_filename} ({len(records)} results): {reason}", user
    )
    batch.skip_deletion_record = True  # that revision is the record of it
    batch.delete()
    return len(records)


@transaction.atomic
def suppress_result(record, user, reason):
    """Stop a result counting towards its asset's status, keeping it listed with who suppressed it and why"""
    with reversion.create_revision():
        reversion.set_user(user)
        reversion.set_comment(f"Suppressed PAT result for {record.asset.asset_id}: {reason}")
        record.suppressed_at = timezone.now()
        record.suppressed_by = user
        record.suppressed_reason = reason
        record.save()


@transaction.atomic
def restore_result(record, user):
    """Make a suppressed result count again"""
    with reversion.create_revision():
        reversion.set_user(user)
        reversion.set_comment(f"Restored PAT result for {record.asset.asset_id}")
        record.suppressed_at = None
        record.suppressed_by = None
        record.suppressed_reason = ""
        record.save()


S3_BACKEND = "storages.backends.s3.S3Storage"
DOWNLOAD_LINK_SECONDS = 60


def signed_download_url(batch, expires=DOWNLOAD_LINK_SECONDS):
    """
    A temporary link that lets a browser download an upload's original file straight from the S3 store, or None
    when files aren't kept there. Signing is done here with no request to the store, so the link has to name an
    address the browser can reach, which in development isn't the one the app uses.
    """
    if settings.STORAGES["default"]["BACKEND"] != S3_BACKEND:
        return None
    from storages.backends.s3 import S3Storage

    endpoint = getattr(settings, "AWS_S3_PUBLIC_ENDPOINT_URL", None) or getattr(settings, "AWS_S3_ENDPOINT_URL", None)
    return S3Storage(endpoint_url=endpoint).url(
        batch.file.name,
        parameters={
            "ResponseContentDisposition": content_disposition_header(True, batch.original_filename),
            "ResponseContentType": "application/octet-stream",
        },
        expire=expires,
    )
