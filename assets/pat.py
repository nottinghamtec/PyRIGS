from dataclasses import dataclass, field

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from reversion import revisions as reversion

from assets import models
from assets.sss import parse_sss

RESULT_LABELS = {True: "Pass", False: "Fail", None: "Unknown"}


@dataclass
class Plan:
    new: list = field(default_factory=list)
    replacements: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    unmatched: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)


@dataclass
class ImportSummary:
    batch: models.PATTestBatch | None
    imported: list = field(default_factory=list)
    replaced: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    unmatched: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)


def normalise_asset_id(raw):
    return raw.strip().upper()


def conflict_key(asset, tested_at):
    return f"{asset.asset_id}|{tested_at.isoformat()}"


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
        (record.asset_id, record.tested_at): record
        for record in models.PATTestRecord.objects.filter(asset__in=assets.values())
    }

    plan = Plan()
    seen = set()
    for result in parsed.results:
        asset = assets.get(normalise_asset_id(result.asset_id))
        if asset is None:
            plan.unmatched.append(result.asset_id)
            continue
        tested_at = timezone.make_aware(result.tested_at)
        key = (asset.pk, tested_at)
        if key in seen:
            plan.duplicates.append(asset.asset_id)
            continue
        seen.add(key)

        fields = record_fields(result)
        current = existing.get(key)
        if current is None:
            plan.new.append(models.PATTestRecord(asset=asset, tested_at=tested_at, **fields))
        elif current.passed == fields["passed"] and current.details == fields["details"]:
            plan.duplicates.append(asset.asset_id)
        elif conflict_key(asset, tested_at) in replace_keys:
            plan.replacements.append((current, fields))
        else:
            plan.conflicts.append(
                {
                    "key": conflict_key(asset, tested_at),
                    "asset_id": asset.asset_id,
                    "tested_at": f"{timezone.localtime(tested_at):%d/%m/%Y %H:%M}",
                    "existing": RESULT_LABELS[current.passed],
                    "new": RESULT_LABELS[fields["passed"]],
                    "differs": "result" if current.passed != fields["passed"] else "readings",
                }
            )
    return plan


def summarise(plan, batch):
    return ImportSummary(
        batch=batch,
        imported=[record.asset.asset_id for record in plan.new],
        replaced=[current.asset.asset_id for current, _ in plan.replacements],
        duplicates=plan.duplicates,
        unmatched=plan.unmatched,
        conflicts=plan.conflicts,
    )


def add_records_to_revision(records):
    for record in records:
        reversion.add_to_revision(record)


@transaction.atomic
def import_sss(parsed, content, filename, sha256, user):
    """Import a parsed file. If it has nothing new and no conflicts, nothing is stored and summary.batch is None."""
    plan = classify(parsed)
    if not plan.new and not plan.conflicts:
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
    Nothing is written, and no revision made, unless something changed.
    """
    plan = plan_reprocess(batch, accept, refresh)

    unmatched = sorted(set(plan.unmatched))
    if not (
        plan.new or plan.replacements or unmatched != batch.unmatched_asset_ids or plan.conflicts != batch.conflicts
    ):
        return summarise(plan, batch)

    with reversion.create_revision():
        if user is not None:
            reversion.set_user(user)
        if refresh:
            reversion.set_comment(f"Refreshed PAT results from {batch.original_filename}")
        elif plan.replacements:
            assets = ", ".join(current.asset.asset_id for current, _ in plan.replacements)
            reversion.set_comment(f"Replaced PAT results for {assets} with the version in {batch.original_filename}")
        else:
            reversion.set_comment(f"Re-matched PAT results in {batch.original_filename}")
        for record in plan.new:
            record.batch = batch
        models.PATTestRecord.objects.bulk_create(plan.new)
        add_records_to_revision(plan.new)
        for current, fields in plan.replacements:
            for name, value in fields.items():
                setattr(current, name, value)
            if not refresh:
                current.batch = batch
            current.save()
        batch.unmatched_asset_ids = unmatched
        batch.conflicts = plan.conflicts
        batch.save(update_fields=["unmatched_asset_ids", "conflicts"])
    return summarise(plan, batch)
