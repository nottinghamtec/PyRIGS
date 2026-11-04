from datetime import date, datetime
from decimal import Decimal

import pytest

from assets import sss
from assets.tests import sss_builder as b


def parse_one(**kwargs):
    return sss.parse_sss(b.sss_file(b.test_result(**kwargs))).results[0]


def test_machine_info_and_end_marker():
    parsed = sss.parse_sss(b.sss_file())
    assert parsed.machine_model == "Apollo 500 Plus"
    assert parsed.machine_serial == "31S-0387"
    assert parsed.results == ()


def test_test_result_header_fields():
    result = parse_one(comments="Change Connector", retest_months=6, visual_retest_months=3)
    assert result.asset_id == "4334"
    assert result.status == sss.PASS
    assert result.passed is True
    assert result.tested_at == datetime(2025, 9, 28, 20, 3, 34)
    assert result.operator == "Isaac DM"
    assert result.site == "TEC PA"
    assert result.location == "Storeroom"
    assert result.program == "IEC Lead"
    assert result.comments == "Change Connector"
    assert result.next_full_test_date == date(2026, 3, 28)
    assert result.next_visual_test_date == date(2025, 12, 28)


def test_failed_result():
    result = parse_one(passed=False, steps=[b.polarity(passed=False)])
    assert result.passed is False
    assert result.steps[0].status == sss.FAIL


def test_physical_results_decode_values_and_units():
    result = parse_one()
    lead, insulation, polarity = result.steps
    assert lead.kind == "IEC lead continuity"
    assert lead.measurements[0].value == Decimal("0.04")
    assert lead.measurements[0].unit == "ohm"
    assert insulation.qualifier == ">"
    assert [(m.name, m.value, m.unit) for m in insulation.measurements] == [
        ("voltage", Decimal("500"), "V"),
        ("resistance", Decimal("19.99"), "Mohm"),
    ]
    assert polarity.measurements == ()


def test_visual_and_comment_results():
    result = parse_one(steps=[b.comment("Change Connector")], visuals=[b.visual("Plug"), b.visual("Flex", False)])
    assert [(v.kind, v.status) for v in result.visual_checks] == [("Plug", sss.PASS), ("Flex", sss.FAIL)]
    assert result.steps[0].text == "Change Connector"


def test_no_retest_interval_means_no_due_date():
    result = parse_one(retest_months=0, visual_retest_months=0)
    assert result.next_full_test_date is None
    assert result.next_visual_test_date is None


def test_marker_byte_inside_header_region_is_skipped():
    result = parse_one(before_marker=b"\x00\xfe\x01\x02")
    assert [s.kind for s in result.steps] == ["IEC lead continuity", "Insulation", "Polarity"]


def test_multiple_results_and_details_are_json_ready():
    parsed = sss.parse_sss(b.sss_file(b.test_result(asset_id="1"), b.test_result(asset_id="2", passed=False)))
    assert [r.asset_id for r in parsed.results] == ["1", "2"]
    details = parsed.results[0].details()
    assert details["steps"][0]["measurements"][0] == {"name": "resistance", "value": "0.04", "unit": "ohm"}


def test_unknown_record_type_is_ignored_with_warning():
    parsed = sss.parse_sss(b.sss_file(b.frame(b"\x77abc")))
    assert parsed.results == ()
    assert parsed.warnings == ("Ignored a record of unknown type 0x77",)


@pytest.mark.parametrize("months,expected", [(1, date(2025, 2, 28)), (12, date(2026, 1, 31)), (13, date(2026, 2, 28))])
def test_add_months_clamps_to_month_end(months, expected):
    assert sss.add_months(date(2025, 1, 31), months) == expected


def corrupt(data, index):
    return data[:index] + bytes([data[index] ^ 0xFF]) + data[index + 1 :]


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not an sss file at all",
        b.machine_info(),
        b.sss_file(end=False),
        b.sss_file()[:-3],
        b.sss_file() + b"\x00",
        b.sss_file(machine=b"\x55\x00\x00\x00\x00\x01\x00"),
        b.sss_file(machine=b.frame(b"")),
        b.end_marker(),
    ],
)
def test_malformed_files_are_rejected(data):
    with pytest.raises(sss.SSSParseError):
        sss.parse_sss(data)


def test_checksum_mismatch_is_rejected():
    data = b.sss_file(b.test_result())
    with pytest.raises(sss.SSSParseError, match="Checksum"):
        sss.parse_sss(corrupt(data, 100))


def invalid_date_record():
    record = bytearray(b.test_result())
    month_offset = sss.FRAME_HEADER.size + 1 + 1 + 16 + 64 + 16 + 16 + 4
    record[month_offset] = 13
    return b.frame(bytes(record[sss.FRAME_HEADER.size : -1]), terminated=True)


def test_invalid_date_is_rejected():
    with pytest.raises(sss.SSSParseError, match="invalid date"):
        sss.parse_sss(b.sss_file(invalid_date_record()))


def test_unrecognised_test_type_is_rejected():
    with pytest.raises(sss.SSSParseError, match="Could not read the test results"):
        parse_one(steps=[bytes([0x42, 0x01, 0x02])])


def test_truncated_result_is_rejected():
    with pytest.raises(sss.SSSParseError, match="Could not read the test results"):
        parse_one(steps=[b.lead_continuity()[:-1]])
