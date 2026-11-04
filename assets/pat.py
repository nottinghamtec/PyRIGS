from dataclasses import dataclass, field

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

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
    batch.file.save(filename, ContentFile(content), save=False)
    batch.save()
    for record in plan.new:
        record.batch = batch
    models.PATTestRecord.objects.bulk_create(plan.new)
    return summarise(plan, batch)


@transaction.atomic
def reprocess(batch, accept=None):
    """
    Run the stored file against RIGS again, picking up assets created since the upload.
    If accept is the key of one of the batch's conflicts, that result replaces the one already recorded.
    """
    with batch.file.open("rb") as stored:
        parsed = parse_sss(stored.read())
    plan = classify(parsed, replace_keys={accept} if accept else set())

    for record in plan.new:
        record.batch = batch
    models.PATTestRecord.objects.bulk_create(plan.new)
    for current, fields in plan.replacements:
        for name, value in fields.items():
            setattr(current, name, value)
        current.batch = batch
        current.save()

    batch.unmatched_asset_ids = sorted(set(plan.unmatched))
    batch.conflicts = plan.conflicts
    batch.save(update_fields=["unmatched_asset_ids", "conflicts"])
    return summarise(plan, batch)
