import struct
import uuid
from datetime import datetime

from assets import sss


def encode_float(value, exponent=0):
    return struct.pack("<H", (exponent << 14) | value)


def text(value, length):
    return value.encode("cp1252").ljust(length, b"\x00")


def frame(content, terminated=False):
    checksum = sum(content) + (sss.TERMINATED_CHECKSUM_OFFSET if terminated else 0)
    header = struct.pack("<BHHH", sss.RECORD_START, len(content), checksum & 0xFFFF, 0)
    return header + content + (bytes([sss.TERMINATOR]) if terminated else b"")


def machine_info(model="Apollo 500 Plus", serial="31S-0387"):
    return frame(bytes([sss.RECORD_MACHINE_INFO]) + text(model, 20) + text(serial, 20))


def polarity(passed=True, flags=None):
    if flags is None:
        flags = sss.FLAG_PASS if passed else sss.FLAG_FAIL
    return bytes([0x91, flags])


def program_definition(*entries, standard_visual_checks=True):
    payload = (b"\x01" if standard_visual_checks else b"") + b"".join(entries)
    # the length counts everything after itself, up to and including the results marker
    return struct.pack("<H", len(payload) + 1) + payload


def def_earth(limit=(100, 3), mode=5):
    return bytes([0x11, mode]) + encode_float(*limit) + b"\x00"


def def_continuity(limit=(100, 3), mode=5, ways=1):
    return bytes([0x16, mode]) + encode_float(*limit) + bytes([ways - 1])


def def_insulation(voltage=(5000, 1), limit=(1000, 3), mode=2):
    return bytes([0x20]) + encode_float(*voltage) + bytes([mode]) + encode_float(*limit) + b"\x00"


def def_rcd(current=(3000, 2), angle=(0, 3), limit=(2000, 1)):
    return bytes([0x9A]) + encode_float(*current) + encode_float(*angle) + encode_float(*limit)


def def_polarity():
    return bytes([0x91])


def def_prompt(value="Change Connector"):
    return bytes([sss.STRING_COMMENT]) + text(value, 54) + b"\x00"


def lead_continuity(value=4, exponent=2, passed=True):
    return bytes([0x16]) + encode_float(value, exponent) + bytes([sss.FLAG_PASS if passed else sss.FLAG_FAIL])


def insulation(voltage=500, mohm=1999, exponent=2, greater_than=True, passed=True, less_than=False):
    flags = sss.FLAG_PASS if passed else sss.FLAG_FAIL
    if greater_than and not less_than:
        flags |= sss.FLAG_GREATER_THAN
    if less_than:
        flags |= sss.FLAG_LESS_THAN
    return bytes([0x20]) + encode_float(voltage, 0) + encode_float(mohm, exponent) + bytes([flags])


def comment(value, passed=True):
    flags = sss.FLAG_PASS if passed else sss.FLAG_FAIL
    return bytes([sss.STRING_COMMENT]) + text(value, sss.STRING_COMMENT_LENGTH) + bytes([flags])


def visual(name="Plug", passed=True):
    flags = sss.FLAG_PASS if passed else sss.FLAG_FAIL
    return bytes([sss.VISUAL_RESULT]) + text(name, 16) + text("", 16) + encode_float(0) + bytes([flags])


def test_result(
    asset_id="4334",
    passed=True,
    tested_at=datetime(2025, 9, 28, 20, 3, 34),
    operator="Isaac DM",
    comments="",
    retest_months=12,
    visual_retest_months=12,
    program="IEC Lead",
    steps=None,
    visuals=None,
    before_marker=b"",
    guid=None,
    definition=None,
):
    guid = guid or uuid.uuid5(uuid.NAMESPACE_OID, f"{asset_id}{tested_at.isoformat()}")
    header = sss.TEST_HEADER.pack(
        sss.FLAG_PASS if passed else sss.FLAG_FAIL,
        text(asset_id, 16),
        guid.bytes_le,
        text("TEC PA", 16),
        text("Storeroom", 16),
        tested_at.hour,
        tested_at.minute,
        tested_at.second,
        tested_at.day,
        tested_at.month,
        tested_at.year,
        text(operator, 16),
        text(comments, 128),
        retest_months,
        text(program, 30),
        visual_retest_months,
    )
    steps = steps if steps is not None else [lead_continuity(), insulation(), polarity()]
    visuals = visuals if visuals is not None else [visual("Plug"), visual("Flex")]
    definition = program_definition() if definition is None else definition
    content = bytes([sss.RECORD_TEST_RESULT]) + header + definition + before_marker + bytes([sss.RESULTS_MARKER])
    content += b"".join(visuals) + b"".join(steps)
    return frame(content, terminated=True)


def end_marker():
    return frame(bytes([sss.RECORD_END, 0xFF]))


def sss_file(*records, machine=None, end=True):
    return (machine or machine_info()) + b"".join(records) + (end_marker() if end else b"")
