import base64
import binascii
import datetime
import json

from RIGS import models

MAX_ENCODED_LENGTH = 16000
TEXT_LIMITS = {
    "name": 255,
    "notes": 2000,
    "venue_name": 255,
    "organisation_name": 255,
    "person_name": 255,
    "contact_email": 254,
    "contact_phone": 40,
    "source_url": 500,
}


def decode(value):
    """Turn the ?prefill= parameter (base64 encoded JSON, URL-safe or standard, padding optional) into a clean dict"""
    if not value or len(value) > MAX_ENCODED_LENGTH:
        return {}
    value = value.strip().replace("+", "-").replace("/", "_")
    try:
        data = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8"))
    except binascii.Error, ValueError, UnicodeDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return _clean(data)


def _clean(data):
    clean = {}
    for key, limit in TEXT_LIMITS.items():
        if isinstance(data.get(key), str) and data[key].strip():
            clean[key] = data[key].strip()[:limit]
    for key in ("start_date", "end_date"):
        try:
            clean[key] = datetime.date.fromisoformat(data[key])
        except KeyError, TypeError, ValueError:
            pass
    for key in ("start_time", "end_time"):
        try:
            clean[key] = datetime.time.fromisoformat(data[key])
        except KeyError, TypeError, ValueError:
            pass
    for key in ("venue_id", "organisation_id", "person_id"):
        if isinstance(data.get(key), int) and not isinstance(data[key], bool):
            clean[key] = data[key]
    return clean


def _existing(model, pk):
    return pk if pk is not None and model.objects.filter(pk=pk).exists() else None


def _text(data, matched, include_times=False):
    lines = []
    if data.get("notes"):
        lines.append(data["notes"])
    contact = " ".join(p for p in (data.get("person_name"), data.get("contact_email"), data.get("contact_phone")) if p)
    if contact:
        lines.append(f"Contact: {contact}")
    if data.get("organisation_name") and "organisation" not in matched:
        lines.append(f"Client: {data['organisation_name']}")
    if data.get("venue_name") and "venue" not in matched:
        lines.append(f"Venue: {data['venue_name']}")
    if include_times and (data.get("start_time") or data.get("end_time")):
        start = data["start_time"].strftime("%H:%M") if data.get("start_time") else "?"
        end = data["end_time"].strftime("%H:%M") if data.get("end_time") else "?"
        lines.append(f"Times: {start} to {end}")
    if data.get("source_url"):
        lines.append(f"Enquiry thread: {data['source_url']}")
    return "\n".join(lines)


def _links(data):
    found = {
        "person": _existing(models.Person, data.get("person_id")),
        "organisation": _existing(models.Organisation, data.get("organisation_id")),
        "venue": _existing(models.Venue, data.get("venue_id")),
    }
    return {k: v for k, v in found.items() if v is not None}


def event_initial(value):
    data = decode(value)
    if not data:
        return {}
    links = _links(data)
    initial = {k: data[k] for k in ("name", "start_date", "end_date", "start_time", "end_time") if k in data}
    initial.update(links)
    text = _text(data, links)
    if text:
        initial["notes"] = text
    return initial


def enquiry_initial(value):
    data = decode(value)
    if not data:
        return {}
    links = _links(data)
    initial = {k: data[k] for k in ("name", "start_date", "end_date") if k in data}
    initial.update({k: v for k, v in links.items() if k in ("person", "organisation")})
    text = _text(data, {k for k in links if k != "venue"}, include_times=True)
    if text:
        initial["notes"] = text
    return initial
