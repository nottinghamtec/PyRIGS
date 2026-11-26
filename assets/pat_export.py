import re

from django.db.models import Q
from django.template.loader import get_template
from django.utils import timezone

from assets import models
from PyRIGS.pdf import render_rml

LATEST = "latest"
ALL = "all"
CUSTOM = "custom"
MODES = (LATEST, ALL, CUSTOM)

SIMPLE = "simple"
DETAILED = "detailed"

MAX_ASSETS = 2000
MAX_DETAILED_RESULTS = 500

XML_INVALID = re.compile(r"[^\t\n\r\x20-퟿-�\U00010000-\U0010ffff]")


class SelectionError(ValueError):
    pass


def registered_results():
    return models.PATTestRecord.objects.counted()


def unmatched_results():
    return models.PATUnmatchedResult.objects.all()


def natural_key(asset_id):
    return [(0, int(part), "") if part.isdigit() else (1, 0, part) for part in re.split(r"(\d+)", asset_id) if part]


def ids_matching(registered_filter, unmatched_filter):
    return set(registered_results().filter(registered_filter).values_list("asset__asset_id", flat=True)) | set(
        unmatched_results().filter(unmatched_filter).values_list("asset_id", flat=True)
    )


def split_id_list(query):
    if not re.search(r"[,\n]", query):
        return []
    return [part.strip().upper() for part in re.split(r"[,\n]", query) if part.strip()]


def search_ids(query="", upload=None, tested_from=None, tested_to=None, source=""):
    filters = Q()
    if upload:
        filters &= Q(batch=upload)
    if tested_from:
        filters &= Q(tested_at__date__gte=tested_from)
    if tested_to:
        filters &= Q(tested_at__date__lte=tested_to)
    ids = ids_matching(filters, filters)

    query = query.strip()
    listed = split_id_list(query)
    if listed:
        ids &= set(listed)
    else:
        for term in query.split():
            where = Q(details__location__icontains=term) | Q(details__site__icontains=term)
            in_rigs = (
                Q(asset__asset_id__icontains=term)
                | Q(asset__description__icontains=term)
                | Q(asset__nickname__icontains=term)
                | Q(asset__serial_number__icontains=term)
            )
            ids &= ids_matching(where | in_rigs, where | Q(asset_id__icontains=term))

    if source:
        known = set(models.Asset.objects.filter(asset_id__in=ids).values_list("asset_id", flat=True))
        ids = ids & known if source == "rigs" else ids - known

    if listed:
        return sorted(ids, key=listed.index)
    wanted = query.upper()
    return sorted(
        ids,
        key=lambda asset_id: (
            asset_id != wanted,
            not (wanted and asset_id.startswith(wanted)),
            natural_key(asset_id),
        ),
    )


def load_results(asset_ids):
    results = {asset_id: [] for asset_id in asset_ids}
    for record in registered_results().filter(asset__asset_id__in=asset_ids).select_related("asset", "batch"):
        results[record.asset.asset_id].append((f"r{record.pk}", record))
    for result in unmatched_results().filter(asset_id__in=asset_ids).select_related("batch"):
        results[result.asset_id].append((f"u{result.pk}", result))
    for tests in results.values():
        tests.sort(key=lambda test: (test[1].tested_at, test[0]), reverse=True)
    return results


def load_assets(asset_ids):
    results = load_results(asset_ids)
    known = {asset.asset_id: asset for asset in models.Asset.objects.filter(asset_id__in=asset_ids)}
    return [
        {"asset_id": asset_id, "asset": known.get(asset_id), "tests": results[asset_id]}
        for asset_id in asset_ids
        if results[asset_id]
    ]


def summarise_test(key, test):
    return {
        "key": key,
        "tested": f"{timezone.localtime(test.tested_at):%d/%m/%Y %H:%M}",
        "passed": test.passed,
        "program": test.program,
        "operator": test.operator,
        "location": describe_location(test),
        "upload": test.batch.original_filename,
    }


def describe_location(test):
    return ", ".join(part for part in (test.details.get("location"), test.details.get("site")) if part)


def summarise_asset(item):
    asset = item["asset"]
    return {
        "id": item["asset_id"],
        "description": asset.description if asset else "",
        "in_rigs": asset is not None,
        "url": asset.get_absolute_url() if asset else "",
        "location": describe_location(item["tests"][0][1]),
        "tests": [summarise_test(key, test) for key, test in item["tests"]],
    }


def validate_selection(selection):
    if not isinstance(selection, list):
        raise SelectionError("The selection couldn't be understood")
    if not selection:
        raise SelectionError("Select at least one asset to export")
    if len(selection) > MAX_ASSETS:
        raise SelectionError(f"Up to {MAX_ASSETS} assets can be exported at once")
    cleaned = {}
    for item in selection:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item.get("mode") not in MODES:
            raise SelectionError("The selection couldn't be understood")
        tests = item.get("tests", [])
        if not isinstance(tests, list) or not all(isinstance(key, str) for key in tests):
            raise SelectionError("The selection couldn't be understood")
        if item["mode"] == CUSTOM and not tests:
            raise SelectionError(f"Choose at least one test for {item['id']}, or remove it")
        cleaned[item["id"]] = {"mode": item["mode"], "tests": set(tests)}
    return cleaned


def resolve_selection(selection):
    asset_ids = sorted(selection, key=natural_key)
    assets = load_assets(asset_ids)
    missing = set(asset_ids) - {item["asset_id"] for item in assets}
    if missing:
        raise SelectionError(f"There are no longer any results for {', '.join(sorted(missing, key=natural_key))}")

    for item in assets:
        choice = selection[item["asset_id"]]
        tests = item["tests"]
        if choice["mode"] == LATEST:
            tests = tests[:1]
        elif choice["mode"] == CUSTOM:
            tests = [test for test in tests if test[0] in choice["tests"]]
            if len(tests) != len(choice["tests"]):
                raise SelectionError(
                    f"Some of the tests chosen for {item['asset_id']} have changed. Reload the page and choose again."
                )
        item["tests"] = [test for _, test in tests]
    return assets


def check_size(assets, detail):
    results = sum(len(item["tests"]) for item in assets)
    if detail == DETAILED and results > MAX_DETAILED_RESULTS:
        raise SelectionError(
            f"A detailed export can hold up to {MAX_DETAILED_RESULTS} test results, and this has {results}. "
            "Export fewer at a time, or use the simple format."
        )


def render_pdf(assets, organisation, user, detail):
    now = timezone.localtime()
    exported_by = user.name or user.get_username()
    filename = f"PAT records - {organisation.name} - {now:%Y-%m-%d}.pdf"
    context = {
        "assets": assets,
        "organisation": organisation,
        "exported_by": exported_by,
        "exported_at": now,
        "detailed": detail == DETAILED,
        "test_count": sum(len(item["tests"]) for item in assets),
        "filename": filename,
        "info_string": f"[PAT records exported by {exported_by} on {now:%d/%m/%Y %H:%M}]",
    }
    rml = get_template("pat_export_print.xml").render(context)
    return filename, render_rml(XML_INVALID.sub("", rml)).read()
