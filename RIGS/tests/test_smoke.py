"""Broad GET smoke tests: render every main page once so view/template/form code paths are exercised."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from RIGS import models
from assets import models as asset_models

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(admin_user, basic_event, ra, checklist, power_test, venue):
    person = models.Person.objects.create(name="Pat Person", email="pat@example.com")
    org = models.Organisation.objects.create(name="Org Ltd")
    basic_event.person = person
    basic_event.organisation = org
    basic_event.venue = venue
    basic_event.mic = admin_user
    basic_event.status = models.Event.CONFIRMED
    basic_event.end_date = basic_event.start_date + datetime.timedelta(days=1)
    basic_event.save()
    models.EventItem.objects.create(event=basic_event, name="Item", cost=10, quantity=2, order=1)
    invoice = models.Invoice.objects.create(event=basic_event)
    payment = models.Payment.objects.create(invoice=invoice, date=timezone.now(), amount=5, method=models.Payment.CASH)

    status = asset_models.AssetStatus.objects.create(name="OK", should_show=True)
    category = asset_models.AssetCategory.objects.create(name="Cat")
    asset = asset_models.Asset.objects.create(
        asset_id="X1",
        description="Thing",
        status=status,
        category=category,
        date_acquired=datetime.date(2020, 1, 1),
        replacement_cost=10,
    )
    supplier = asset_models.Supplier.objects.create(name="Sup")
    connector = asset_models.Connector.objects.create(
        description="IEC", current_rating=16, voltage_rating=240, num_pins=3
    )
    cable_type = asset_models.CableType.objects.create(circuits=1, cores=3, plug=connector, socket=connector)
    return dict(
        event=basic_event,
        person=person,
        org=org,
        venue=venue,
        invoice=invoice,
        payment=payment,
        ra=ra,
        ec=checklist,
        pt=power_test,
        asset=asset,
        supplier=supplier,
        cable_type=cable_type,
        user=admin_user,
    )


# (url name, kwargs as {kwarg: world key attribute})
PAGES = [
    ("rigboard", {}),
    ("web_calendar", {}),
    ("event_archive", {}),
    ("hs_list", {}),
    ("person_list", {}),
    ("person_create", {}),
    ("person_detail", {"pk": "person"}),
    ("person_update", {"pk": "person"}),
    ("organisation_list", {}),
    ("organisation_create", {}),
    ("organisation_detail", {"pk": "org"}),
    ("organisation_update", {"pk": "org"}),
    ("venue_list", {}),
    ("venue_create", {}),
    ("venue_detail", {"pk": "venue"}),
    ("venue_update", {"pk": "venue"}),
    ("event_detail", {"pk": "event"}),
    ("event_create", {}),
    ("event_embed", {"pk": "event"}),
    ("event_print", {"pk": "event"}),
    ("event_update", {"pk": "event"}),
    ("event_duplicate", {"pk": "event"}),
    ("event_ra", {"pk": "event"}),
    ("ra_detail", {"pk": "ra"}),
    ("ra_edit", {"pk": "ra"}),
    ("ra_print", {"pk": "ra"}),
    ("event_ec", {"pk": "event"}),
    ("ec_detail", {"pk": "ec"}),
    ("ec_edit", {"pk": "ec"}),
    ("event_pt", {"pk": "event"}),
    ("pt_detail", {"pk": "pt"}),
    ("pt_edit", {"pk": "pt"}),
    ("event_checkin", {"pk": "event"}),
    ("event_checkout", {}),
    ("event_checkin_override", {"pk": "event"}),
    ("event_authorise_request", {"pk": "event"}),
    ("event_authorise_preview", {"pk": "event"}),
    ("invoice_dashboard", {}),
    ("invoice_list", {}),
    ("invoice_archive", {}),
    ("invoice_waiting", {}),
    ("invoice_event", {"pk": "event"}),
    ("invoice_detail", {"pk": "invoice"}),
    ("invoice_print", {"pk": "invoice"}),
    ("invoice_void", {"pk": "invoice"}),
    ("invoice_delete", {"pk": "invoice"}),
    ("payment_delete", {"pk": "payment"}),
    ("activity_feed", {}),
    ("event_history", {"pk": "event"}),
    ("asset_index", {}),
    ("asset_list", {}),
    ("asset_detail", {"pk": "asset"}),
    ("asset_create", {}),
    ("asset_update", {"pk": "asset"}),
    ("asset_duplicate", {"pk": "asset"}),
    ("generate_label", {"pk": "asset"}),
    ("cable_list", {}),
    ("cable_type_list", {}),
    ("cable_type_create", {}),
    ("cable_type_update", {"pk": "cable_type"}),
    ("cable_type_detail", {"pk": "cable_type"}),
    ("asset_embed", {"pk": "asset"}),
    ("asset_audit_list", {}),
    ("asset_audit", {"pk": "asset"}),
    ("supplier_list", {}),
    ("supplier_detail", {"pk": "supplier"}),
    ("supplier_create", {}),
    ("supplier_update", {"pk": "supplier"}),
    ("profile_detail", {}),
    ("profile_update_self", {}),
    ("search_help", {}),
    ("item_list", {}),
    ("trainee_list", {}),
    ("level_list", {}),
]


@pytest.mark.parametrize("name,kw", PAGES, ids=[p[0] for p in PAGES])
def test_page_renders(admin_client, world, name, kw):
    world["assetlist"] = "X1"
    kwargs = {k: (world[v].pk if hasattr(world[v], "pk") else world[v]) for k, v in kw.items()}
    if name in ("asset_detail", "asset_update", "asset_duplicate", "generate_label", "asset_embed", "asset_audit"):
        kwargs["pk"] = "X1"
    response = admin_client.get(reverse(name, kwargs=kwargs), follow=True)
    assert response.status_code == 200


def test_ical(client, world):
    user = world["user"]
    user.api_key = "abc123"
    user.save()
    response = client.get(reverse("ics_calendar", kwargs={"api_pk": user.pk, "api_key": "abc123"}))
    assert response.status_code == 200
    assert b"VEVENT" in response.content


def test_invoice_payment_flow(admin_client, world):
    inv = world["invoice"]
    response = admin_client.post(
        reverse("payment_create"),
        {"invoice": inv.pk, "date": "2020-01-01", "amount": "3.00", "method": models.Payment.CASH},
    )
    assert response.status_code in (200, 302)
    assert admin_client.post(reverse("payment_delete", kwargs={"pk": world["payment"].pk})).status_code in (200, 302)


def test_event_create_and_update_post(admin_client, world):
    event = world["event"]
    data = {
        "name": "Posted",
        "start_date": "2030-01-01",
        "status": models.Event.BOOKED,
        "items-TOTAL_FORMS": 0,
        "items-INITIAL_FORMS": 0,
        "items-MIN_NUM_FORMS": 0,
        "items-MAX_NUM_FORMS": 1000,
    }
    assert admin_client.post(reverse("event_create"), data).status_code in (200, 302)
    assert admin_client.post(reverse("event_update", kwargs={"pk": event.pk}), data).status_code in (200, 302)


def test_api_secure(admin_client, world):
    assert admin_client.get(reverse("api_secure", kwargs={"model": "person"}), {"term": "Pat"}).status_code == 200
    assert (
        admin_client.get(reverse("api_secure", kwargs={"model": "venue", "pk": world["venue"].pk})).status_code == 200
    )


def test_authorisation_request_and_authorise(admin_client, client, world):
    from django.core import signing

    event = world["event"]
    response = admin_client.post(reverse("event_authorise_request", kwargs={"pk": event.pk}), {"email": "a@b.com"})
    assert response.status_code in (200, 302)
    hmac = signing.dumps({"pk": event.pk, "email": "a@b.com", "sent_by": world["user"].pk})
    url = reverse("event_authorise", kwargs={"pk": event.pk, "hmac": hmac})
    assert client.get(url).status_code == 200
    assert client.get(reverse("event_authorise_form_preview", kwargs={"pk": event.pk, "hmac": hmac})).status_code == 200


def test_event_thread_redirect(admin_client, world):
    assert admin_client.get(reverse("event_thread", kwargs={"pk": world["event"].pk})).status_code in (200, 302)


@pytest.mark.parametrize(
    "url",
    [
        "/rigboard/calendar/month/",
        "/rigboard/calendar/week/2020-01-01/",
        "/rigboard/calendar/day/2020-01-01/",
        "/event/archive/?start=2030-01-01&end=2020-01-01",
        "/event/archive/?q=TE&status=1",
        "/event/hs/?q=TE",
        "/rigboard/activity/",
        "/search/?q=Pat",
    ],
)
def test_filtered_pages(admin_client, world, url):
    assert admin_client.get(url, follow=True).status_code == 200
