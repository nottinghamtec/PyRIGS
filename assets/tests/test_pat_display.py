import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from assets import models
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db

WHEN = datetime.datetime(2025, 11, 3, 10, 0, 0)


def import_record(client, **kwargs):
    client.post(reverse("pat_upload"), {"file": SimpleUploadedFile("r.sss", b.sss_file(b.test_result(**kwargs)))})
    return models.PATTestRecord.objects.get()


def rows_of(client, **kwargs):
    return [row for row in import_record(client, **kwargs).display_steps()]


def test_readings_are_lined_up_with_their_program_limits(admin_client, pat_asset):
    rows = rows_of(
        admin_client,
        definition=b.program_definition(b.def_continuity(limit=(100, 3)), b.def_insulation(limit=(1000, 3))),
        steps=[b.lead_continuity(4, 2), b.insulation(500, 1999, 2)],
    )
    assert [(r["kind"], r["reading"], r["limit"], r["status"]) for r in rows] == [
        ("IEC lead continuity", "0.04 Ω", "≤ 0.100 Ω", "PASS"),
        ("Insulation", "> 19.99 MΩ", "≥ 1.000 MΩ", "PASS"),
    ]
    assert rows[1]["setup"] == "500 V"


def test_repeated_tests_are_numbered_and_each_gets_the_limit(admin_client, pat_asset):
    rows = rows_of(
        admin_client,
        definition=b.program_definition(b.def_continuity(limit=(100, 3), ways=4)),
        steps=[b.lead_continuity(7, 2)] * 4,
    )
    assert [r["repeat"] for r in rows] == ["1 of 4", "2 of 4", "3 of 4", "4 of 4"]
    assert {r["limit"] for r in rows} == {"≤ 0.100 Ω"}


def test_prompts_split_the_test_into_numbered_sections(admin_client, pat_asset):
    rows = rows_of(
        admin_client,
        definition=b.program_definition(b.def_polarity(), b.def_prompt(), b.def_polarity()),
        steps=[b.polarity(), b.comment("Change Connector"), b.polarity()],
    )
    assert [(r.get("section"), r.get("prompt"), r.get("repeat")) for r in rows] == [
        ("Section 1 of 2", None, None),
        ("", "", ""),
        (None, "Change Connector", None),
        ("Section 2 of 2", None, None),
        ("", "", ""),
    ]


def test_a_prompt_the_operator_failed_is_marked_failed(admin_client, pat_asset):
    rows = rows_of(
        admin_client, passed=False, steps=[b.polarity(), b.comment("Change Connector", passed=False), b.polarity()]
    )
    assert [r["status"] for r in rows if r.get("prompt")] == ["FAIL"]


def test_without_prompts_there_are_no_sections(admin_client, pat_asset):
    rows = rows_of(admin_client, steps=[b.polarity(), b.polarity()])
    assert not any(r.get("section") for r in rows)
    assert [r["repeat"] for r in rows] == ["1 of 2", "2 of 2"]


def test_the_program_is_summarised_with_repeated_cycles_shown_once(admin_client, pat_asset):
    cycle = [b.def_polarity(), b.def_insulation(), b.def_continuity(), b.def_prompt()]
    record = import_record(
        admin_client, definition=b.program_definition(*(cycle * 5), *cycle[:3]), steps=[b.polarity()]
    )
    program = record.display_program()
    assert program["sections"] == 6
    assert [item["text"] for item in program["items"]] == [
        "Polarity",
        "Insulation at 500.0 V, ≥ 1.000 MΩ",
        "IEC lead continuity, ≤ 0.100 Ω",
        "Prompt: Change Connector",
    ]


def test_a_program_without_repeats_is_listed_in_full(admin_client, pat_asset):
    record = import_record(
        admin_client,
        definition=b.program_definition(b.def_continuity(ways=4), b.def_insulation(), b.def_polarity()),
        steps=[b.polarity()],
    )
    program = record.display_program()
    assert program["sections"] == 1
    assert [item["text"] for item in program["items"]] == [
        "IEC lead continuity ×4, ≤ 0.100 Ω",
        "Insulation at 500.0 V, ≥ 1.000 MΩ",
        "Polarity",
    ]


def test_a_skipped_step_does_not_shift_the_limits(admin_client, pat_asset):
    rows = rows_of(
        admin_client,
        definition=b.program_definition(b.def_continuity(limit=(100, 3)), b.def_insulation(limit=(2000, 3))),
        steps=[b.insulation(500, 1999, 2)],
    )
    assert [(r["kind"], r["limit"]) for r in rows] == [("Insulation", "≥ 2.000 MΩ")]


def test_steps_the_program_does_not_define_just_have_no_limit(admin_client, pat_asset):
    rows = rows_of(admin_client, definition=b.program_definition(), steps=[b.lead_continuity(4, 2)])
    assert rows[0]["limit"] == ""
    assert rows[0]["reading"] == "0.04 Ω"


def test_rcd_limits_are_in_milliseconds(admin_client, pat_asset):
    record = import_record(
        admin_client, definition=b.program_definition(b.def_rcd(limit=(2000, 1))), steps=[b.polarity()]
    )
    assert record.describe_limit(record.details["program_steps"][0]) == "≤ 200.0 ms"


def test_visual_checks_are_listed_with_their_status(admin_client, pat_asset):
    record = import_record(admin_client, visuals=[b.visual("Plug"), b.visual("Flex", passed=False)])
    assert [(c["kind"], c["status"]) for c in record.display_visual_checks()] == [("Plug", "PASS"), ("Flex", "FAIL")]


def test_expanded_view_shows_limits_and_a_note_about_them(admin_client, pat_asset):
    import_record(
        admin_client,
        definition=b.program_definition(b.def_insulation(limit=(1000, 3))),
        steps=[b.insulation(500, 1999, 2)],
    )
    content = admin_client.get(reverse("asset_detail", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert "≥ 1.000 MΩ" in content
    assert "base limits" in content


def test_failing_rows_are_highlighted(admin_client, pat_asset):
    import_record(admin_client, passed=False, steps=[b.polarity(False)])
    content = admin_client.get(reverse("asset_detail", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert '<tr class="table-danger">' in content


def test_results_expand_in_a_separate_full_width_row(admin_client, pat_asset):
    record = import_record(admin_client)
    content = admin_client.get(reverse("asset_detail", kwargs={"pk": pat_asset.asset_id})).content.decode()
    assert f'data-bs-target="#pat-{record.pk}"' in content
    assert '<td colspan="7" class="p-0 border-0">' in content
    assert "table-layout: fixed" in content


def test_other_models_history_is_unchanged(admin_client):
    supplier = models.Supplier.objects.create(name="Gadgetron")
    content = admin_client.get(reverse("supplier_history", kwargs={"pk": supplier.pk})).content.decode()
    assert "table-striped" in content
    assert "pat-table" not in content


def test_a_test_that_stopped_at_a_failure_says_how_many_were_expected(admin_client, pat_asset):
    record = import_record(
        admin_client,
        passed=False,
        definition=b.program_definition(b.def_continuity(limit=(100, 3), ways=4), b.def_polarity()),
        steps=[b.lead_continuity(8, 2), b.lead_continuity(9, 2), b.lead_continuity(1656, 2, passed=False)],
    )
    assert [row["repeat"] for row in record.display_steps()] == ["1 of 4", "2 of 4", "3 of 4"]
    assert record.failure_reasons == ["IEC lead continuity failed (resistance 16.56 ohm) [3 of 4]"]
