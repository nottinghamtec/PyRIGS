import base64
import datetime
import json

import pytest
from django.urls import reverse

from RIGS import models, prefill


def encode(data, urlsafe=True, pad=True):
    raw = json.dumps(data).encode()
    value = (base64.urlsafe_b64encode(raw) if urlsafe else base64.b64encode(raw)).decode()
    return value if pad else value.rstrip("=")


@pytest.fixture
def records(db):
    return {
        "venue": models.Venue.objects.create(name="The Barn - SB"),
        "organisation": models.Organisation.objects.create(name="Allotment Society"),
        "person": models.Person.objects.create(name="Tom Hale", email="tom@example.org"),
    }


def payload(records):
    return {
        "name": "Allotment Society Halloween Party",
        "start_date": "2026-10-30",
        "end_date": "2026-10-31",
        "start_time": "20:00",
        "end_time": "01:00",
        "venue_id": records["venue"].pk,
        "venue_name": "the barn at Sutton Bonington",
        "organisation_id": records["organisation"].pk,
        "person_id": records["person"].pk,
        "person_name": "Tom Hale",
        "contact_email": "tom@example.org",
        "contact_phone": "07700 900456",
        "notes": "About 150 people.",
        "source_url": "https://forum.nottinghamtec.co.uk/t/x/1",
    }


@pytest.mark.parametrize("urlsafe,pad", [(True, True), (True, False), (False, True), (False, False)])
def test_decode_accepts_standard_and_urlsafe_base64(urlsafe, pad):
    data = {"name": "Café night ~~??>>", "start_date": "2026-01-02"}
    assert prefill.decode(encode(data, urlsafe, pad)) == {
        "name": "Café night ~~??>>",
        "start_date": datetime.date(2026, 1, 2),
    }


@pytest.mark.parametrize(
    "value", [None, "", "not base64!!", encode([1, 2]), "A" * 20000, base64.b64encode(b"{").decode()]
)
def test_decode_rejects_bad_input(value):
    assert prefill.decode(value) == {}


def test_decode_drops_unknown_and_badly_typed_fields():
    data = {
        "name": 5,
        "start_date": "31/10/2026",
        "start_time": "25:99",
        "venue_id": "7",
        "person_id": True,
        "evil": "x",
        "notes": "ok",
    }
    assert prefill.decode(encode(data)) == {"notes": "ok"}


def test_event_initial_links_existing_records_and_notes(records):
    initial = prefill.event_initial(encode(payload(records)))
    assert initial["name"] == "Allotment Society Halloween Party"
    assert initial["start_time"] == datetime.time(20, 0)
    assert (initial["venue"], initial["organisation"], initial["person"]) == tuple(
        records[k].pk for k in ("venue", "organisation", "person")
    )
    assert "Contact: Tom Hale tom@example.org 07700 900456" in initial["description"]
    assert "Venue:" not in initial["description"]
    assert "Enquiry thread: https://forum.nottinghamtec.co.uk/t/x/1" in initial["description"]


def test_unknown_ids_are_ignored_and_names_go_into_the_text(records):
    data = payload(records) | {"venue_id": 99999, "organisation_id": 99999, "organisation_name": "Mystery Club"}
    initial = prefill.event_initial(encode(data))
    assert "venue" not in initial and "organisation" not in initial
    assert "Client: Mystery Club" in initial["description"]
    assert "Venue: the barn at Sutton Bonington" in initial["description"]


def test_enquiry_has_no_times_or_venue_fields_so_they_go_in_the_notes(records):
    initial = prefill.enquiry_initial(encode(payload(records)))
    assert set(initial) == {"name", "start_date", "end_date", "person", "organisation", "notes"}
    assert "Times: 20:00 to 01:00" in initial["notes"]
    assert "Venue: the barn at Sutton Bonington" in initial["notes"]


def test_event_create_form_is_prefilled(admin_client, records):
    response = admin_client.get(reverse("event_create"), {"prefill": encode(payload(records))})
    assert response.status_code == 200
    form = response.context["form"]
    assert form["name"].value() == "Allotment Society Halloween Party"
    assert form["venue"].value() == records["venue"].pk
    assert response.context["venue"] == records["venue"]
    assert "pre-filled" in response.content.decode()


def test_event_create_with_garbage_prefill_still_renders(admin_client):
    response = admin_client.get(reverse("event_create"), {"prefill": "garbage"})
    assert response.status_code == 200
    assert response.context["form"]["name"].value() in (None, "")
    assert "could not be read" in response.content.decode()


def test_enquiry_modal_is_prefilled(admin_client, records):
    response = admin_client.get(reverse("enquiry_create"), {"prefill": encode(payload(records))})
    form = response.context["form"]
    assert form["name"].value() == "Allotment Society Halloween Party"
    assert form["person"].value() == records["person"].pk
    assert "Times: 20:00 to 01:00" in form["notes"].value()


def test_kanban_opens_the_enquiry_modal_when_prefilled(admin_client, records):
    value = encode(payload(records))
    response = admin_client.get(reverse("event_kanban"), {"prefill": value})
    assert response.status_code == 200
    assert response.context["prefill_modal_url"].startswith(reverse("enquiry_create") + "?prefill=")
    assert 'id="kanban-prefill-url"' in response.content.decode()
    assert "prefill_modal_url" not in admin_client.get(reverse("event_kanban"), {"prefill": "garbage"}).context


def test_kanban_does_not_open_a_modal_without_permission(client, django_user_model, records):
    user = django_user_model.objects.create_user("viewer", password="x", is_approved=True)
    client.force_login(user)
    response = client.get(reverse("event_kanban"), {"prefill": encode(payload(records))})
    assert "prefill_modal_url" not in (response.context or {})
