import calendar
import struct
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"
UNKNOWN = "UNKNOWN"

RECORD_START = 0x55
RECORD_MACHINE_INFO = 0x55
RECORD_TEST_RESULT = 0x01
RECORD_END = 0xAA
TERMINATOR = 0xFF
TERMINATED_CHECKSUM_OFFSET = 0xFE
RESULTS_MARKER = 0xFE
VISUAL_RESULT = 0xFD

FRAME_HEADER = struct.Struct("<BHHH")
MACHINE_INFO = struct.Struct("<20s20s")
# flags, asset id, 48 unused bytes, test GUID, site, location, h/m/s/d/m/y, operator, comments, unused byte,
# retest months, program, visual retest months, 15 bytes that are the same in every normal test
TEST_HEADER = struct.Struct("<B16s48x16s16s16sBBBBBH16s128s1xB30sB15x")
VISUAL_RESULT_BODY = struct.Struct("<16s16sHB")

FLAG_PASS = 0x01
FLAG_FAIL = 0x02
FLAG_POLARITY_FAIL = 0x04  # polarity results are also flagged this way, sometimes without FLAG_FAIL
FLAG_LESS_THAN = 0x10
FLAG_GREATER_THAN = 0x20

POLARITY_TEST = 0x91

# type byte -> (kind, [(field name, unit or None for string)...]); every body ends with one flag byte
PHYSICAL_TESTS = {
    0x11: ("Earth resistance", [("resistance", "ohm")]),
    0x16: ("IEC lead continuity", [("resistance", "ohm")]),
    0x18: ("Point to point", [("resistance", "ohm")]),
    0x20: ("Insulation", [("voltage", "V"), ("resistance", "Mohm")]),
    0x83: ("Substitute leakage", [("current", "mA")]),
    POLARITY_TEST: ("Polarity", []),
    0x92: ("Mains voltage", [("voltage", "V")]),
    0x96: ("Touch / leakage current", [("load current", "mA"), None, ("leakage current", "mA")]),
    0x9A: ("RCD", [("test current", "mA"), ("angle", "deg"), ("trip time", "ms")]),
}
STRING_COMMENT = 0xFC
STRING_COMMENT_LENGTH = 86
FLOAT_SIZE = 2

# The program a test was run with is stored in front of its results: a length, a flag for the standard visual
# checks, then one entry per step, each a type byte followed by this many bytes of settings.
PROGRAM_STEP_SIZES = {
    0x11: 4,
    0x16: 4,
    0x20: 6,
    0x83: 4,
    0x53: 4,
    POLARITY_TEST: 0,
    0x9A: 6,
    STRING_COMMENT: 55,
    VISUAL_RESULT: 32,
}
PROGRAM_TEXT_LENGTH = 54


class SSSParseError(ValueError):
    pass


@dataclass(frozen=True)
class Measurement:
    name: str
    value: Decimal
    unit: str


@dataclass(frozen=True)
class TestStep:
    kind: str
    status: str
    qualifier: str = ""
    measurements: tuple = ()
    text: str = ""
    flags: int = 0

    def as_dict(self):
        return {
            "kind": self.kind,
            "status": self.status,
            "qualifier": self.qualifier,
            "flags": self.flags,
            "measurements": [{"name": m.name, "value": str(m.value), "unit": m.unit} for m in self.measurements],
            "text": self.text,
        }


@dataclass(frozen=True)
class TestResult:
    asset_id: str
    status: str
    site: str
    location: str
    tested_at: datetime
    operator: str
    comments: str
    program: str
    retest_months: int
    visual_retest_months: int
    visual_checks: tuple = ()
    steps: tuple = ()
    flags: int = 0
    guid: str = ""
    standard_visual_checks: bool = True
    program_steps: tuple = ()
    raw: dict = field(default_factory=dict)

    @property
    def passed(self):
        if self.status == PASS:
            return True
        if self.status == FAIL:
            return False
        return None

    @property
    def next_full_test_date(self):
        return add_months(self.tested_at.date(), self.retest_months) if self.retest_months else None

    @property
    def next_visual_test_date(self):
        return add_months(self.tested_at.date(), self.visual_retest_months) if self.visual_retest_months else None

    def details(self):
        return {
            "site": self.site,
            "location": self.location,
            "program": self.program,
            "guid": self.guid,
            "flags": self.flags,
            "retest_months": self.retest_months,
            "visual_retest_months": self.visual_retest_months,
            "standard_visual_checks": self.standard_visual_checks,
            "program_steps": list(self.program_steps),
            "raw": self.raw,
            "visual_checks": [step.as_dict() for step in self.visual_checks],
            "steps": [step.as_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class SSSFile:
    machine_model: str
    machine_serial: str
    results: tuple = ()
    warnings: tuple = field(default=())


def add_months(start, months):
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def decode_text(raw):
    return raw.split(b"\x00", 1)[0].decode("cp1252", errors="replace").strip()


def decode_float(raw):
    """Two bits of decimal exponent, fourteen of significand."""
    return Decimal(raw & 0x3FFF).scaleb(-(raw >> 14))


def decode_flags(byte, fail_mask=FLAG_FAIL):
    if byte & fail_mask:
        status = FAIL
    elif byte & FLAG_PASS:
        status = PASS
    elif byte == 0:
        status = INFO
    else:
        status = UNKNOWN
    if byte & FLAG_LESS_THAN:
        qualifier = "<"
    elif byte & FLAG_GREATER_THAN:
        qualifier = ">"
    else:
        qualifier = ""
    return status, qualifier


def iter_records(data):
    pos = 0
    while True:
        if len(data) - pos < FRAME_HEADER.size:
            raise SSSParseError("File ends before the end-of-file marker")
        start, length, checksum, reserved = FRAME_HEADER.unpack_from(data, pos)
        if start != RECORD_START or reserved != 0:
            raise SSSParseError(f"Not a valid record header at byte {pos}")
        content_start = pos + FRAME_HEADER.size
        content_end = content_start + length
        content = data[content_start:content_end]
        if len(content) != length:
            raise SSSParseError(f"Record at byte {pos} is truncated")
        total = sum(content)
        if total & 0xFFFF == checksum:
            pos = content_end
        elif (
            data[content_end : content_end + 1] == bytes([TERMINATOR])
            and (total + TERMINATED_CHECKSUM_OFFSET) & 0xFFFF == checksum
        ):
            pos = content_end + 1
        else:
            raise SSSParseError(f"Checksum mismatch in record at byte {pos}")
        if not content:
            raise SSSParseError(f"Record at byte {pos} is empty")
        if content[:1] == bytes([RECORD_END]):
            if pos != len(data):
                raise SSSParseError("Unexpected data after the end-of-file marker")
            return
        yield content


def parse_machine_info(body):
    if len(body) < MACHINE_INFO.size:
        raise SSSParseError("Machine info record is too short")
    model, serial = MACHINE_INFO.unpack_from(body)
    return decode_text(model), decode_text(serial)


def parse_results(body, pos):
    """Parse the visual and physical results from pos to the end of body, or return None if they don't fit."""
    visual_checks = []
    steps = []
    while pos < len(body):
        kind = body[pos]
        pos += 1
        if kind == VISUAL_RESULT:
            if pos + VISUAL_RESULT_BODY.size > len(body):
                return None
            name, unit, raw, flags = VISUAL_RESULT_BODY.unpack_from(body, pos)
            pos += VISUAL_RESULT_BODY.size
            status, qualifier = decode_flags(flags)
            value = decode_float(raw)
            unit = decode_text(unit)
            measurements = (Measurement("value", value, unit),) if unit else ()
            visual_checks.append(TestStep(decode_text(name), status, qualifier, measurements, flags=flags))
        elif kind == STRING_COMMENT:
            if pos + STRING_COMMENT_LENGTH + 1 > len(body):
                return None
            text = decode_text(body[pos : pos + STRING_COMMENT_LENGTH])
            flags = body[pos + STRING_COMMENT_LENGTH]
            status, qualifier = decode_flags(flags)
            pos += STRING_COMMENT_LENGTH + 1
            steps.append(TestStep("Comment", status, qualifier, text=text, flags=flags))
        elif kind in PHYSICAL_TESTS:
            name, layout = PHYSICAL_TESTS[kind]
            size = len(layout) * FLOAT_SIZE + 1
            if pos + size > len(body):
                return None
            measurements = []
            for offset, spec in enumerate(layout):
                if spec is not None:
                    (raw,) = struct.unpack_from("<H", body, pos + offset * FLOAT_SIZE)
                    measurements.append(Measurement(spec[0], decode_float(raw), spec[1]))
            fail_mask = FLAG_FAIL | FLAG_POLARITY_FAIL if kind == POLARITY_TEST else FLAG_FAIL
            flags = body[pos + size - 1]
            status, qualifier = decode_flags(flags, fail_mask)
            pos += size
            steps.append(TestStep(name, status, qualifier, tuple(measurements), flags=flags))
        else:
            return None
    return tuple(visual_checks), tuple(steps)


def program_float(raw):
    return str(decode_float(struct.unpack("<H", raw)[0]))


def parse_program(definition):
    """
    Decode the program a test was run with. Returns (standard_visual_checks, steps), or None if it has an entry we
    don't understand. Limits are the program's base limits: the tester can allow more for longer leads.
    """
    if len(definition) < 2:
        return None
    body = definition[2:]
    pos = 1 if body[:1] == b"\x01" else 0
    standard_visual_checks = pos == 1
    steps = []
    while pos < len(body):
        kind = body[pos]
        size = PROGRAM_STEP_SIZES.get(kind)
        if size is None or pos + 1 + size > len(body):
            return None
        settings = body[pos + 1 : pos + 1 + size]
        pos += 1 + size
        if kind == 0x11:
            steps.append(
                {"kind": "Earth resistance", "limit": program_float(settings[1:3]), "limit_type": "max", "unit": "ohm"}
            )
        elif kind == 0x16:
            steps.append(
                {
                    "kind": "IEC lead continuity",
                    "limit": program_float(settings[1:3]),
                    "limit_type": "max",
                    "unit": "ohm",
                    "repeats": settings[3] + 1,
                }
            )
        elif kind == 0x20:
            steps.append(
                {
                    "kind": "Insulation",
                    "voltage": program_float(settings[0:2]),
                    "limit": program_float(settings[3:5]),
                    "limit_type": "min",
                    "unit": "Mohm",
                }
            )
        elif kind == 0x9A:
            steps.append(
                {
                    "kind": "RCD",
                    "test_current": program_float(settings[0:2]),
                    "angle": program_float(settings[2:4]),
                    "limit": program_float(settings[4:6]),
                    "limit_type": "max",
                    "unit": "ms",
                }
            )
        elif kind == POLARITY_TEST:
            steps.append({"kind": "Polarity"})
        elif kind == STRING_COMMENT:
            steps.append({"kind": "Comment", "text": decode_text(settings[:PROGRAM_TEXT_LENGTH])})
        elif kind == VISUAL_RESULT:
            steps.append({"kind": "Visual check", "text": decode_text(settings[:16])})
        elif kind == 0x83:
            steps.append({"kind": "Substitute leakage"})
        else:
            steps.append({"kind": f"Test 0x{kind:02x}"})
    return standard_visual_checks, tuple(steps)


def locate_results(body):
    """Find the marker that ends the program definition and parse the results after it."""
    start = TEST_HEADER.size
    candidates = []
    if len(body) >= start + 2:
        # The definition starts with a length that counts everything after it, up to and including the marker
        (length,) = struct.unpack_from("<H", body, start)
        candidates.append(start + length + 1)
    marker = body.find(bytes([RESULTS_MARKER]), start)
    while marker != -1:
        candidates.append(marker)
        marker = body.find(bytes([RESULTS_MARKER]), marker + 1)
    for marker in candidates:
        if marker < len(body) and body[marker] == RESULTS_MARKER:
            parsed = parse_results(body, marker + 1)
            if parsed is not None:
                return marker, parsed
    return None, None


def parse_test_result(body):
    if len(body) < TEST_HEADER.size:
        raise SSSParseError("Test record is too short")
    (
        flags,
        asset_id,
        guid,
        site,
        location,
        hour,
        minute,
        second,
        day,
        month,
        year,
        operator,
        comments,
        retest_months,
        program,
        visual_retest_months,
    ) = TEST_HEADER.unpack_from(body)
    asset_id = decode_text(asset_id)
    try:
        tested_at = datetime(year, month, day, hour, minute, second)
    except ValueError:
        raise SSSParseError(f"Test record for '{asset_id}' has an invalid date") from None

    marker, parsed = locate_results(body)
    if parsed is None:
        raise SSSParseError(f"Could not read the test results for '{asset_id}'")
    definition = body[TEST_HEADER.size : marker]
    program_steps = parse_program(definition)

    status, _ = decode_flags(flags)
    return TestResult(
        asset_id=asset_id,
        status=status,
        site=decode_text(site),
        location=decode_text(location),
        tested_at=tested_at,
        operator=decode_text(operator),
        comments=decode_text(comments),
        program=decode_text(program),
        retest_months=retest_months,
        visual_retest_months=visual_retest_months,
        visual_checks=parsed[0],
        steps=parsed[1],
        flags=flags,
        guid=str(uuid.UUID(bytes_le=guid)) if any(guid) else "",
        standard_visual_checks=program_steps[0] if program_steps else True,
        program_steps=program_steps[1] if program_steps else (),
        raw={} if program_steps else {"program_definition": definition.hex()},
    )


def parse_sss(data):
    """Parse the contents of a Seaward .sss file. Raises SSSParseError if it isn't a file we understand."""
    machine = None
    results = []
    warnings = []
    for content in iter_records(bytes(data)):
        record_type, body = content[0], content[1:]
        if record_type == RECORD_MACHINE_INFO:
            machine = parse_machine_info(body)
        elif record_type == RECORD_TEST_RESULT:
            results.append(parse_test_result(body))
        else:
            warnings.append(f"Ignored a record of unknown type 0x{record_type:02x}")
    if machine is None:
        raise SSSParseError("File has no machine info record")
    return SSSFile(machine[0], machine[1], tuple(results), tuple(warnings))
