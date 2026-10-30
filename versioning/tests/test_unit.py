from datetime import date

from django.urls import reverse
from reversion import revisions as reversion
from pytest_django.asserts import assertContains

from RIGS import models
from assets import models as amodels


def create_events(admin_user):
    models.VatRate.objects.create(start_at="2014-03-05", rate=0.20, comment="test1")

    events = {}

    with reversion.create_revision():
        reversion.set_user(admin_user)
        events[1] = models.Event.objects.create(name="TE E1", start_date=date.today())

    with reversion.create_revision():
        reversion.set_user(admin_user)
        events[2] = models.Event.objects.create(name="TE E2", start_date="2014-03-05")

    with reversion.create_revision():
        reversion.set_user(admin_user)
        events[1].description = "A test description"
        events[1].save()

    return events


def create_assets(admin_user):
    working = amodels.AssetStatus.objects.create(name="Working", should_show=True)
    broken = amodels.AssetStatus.objects.create(name="Broken", should_show=False)
    lighting = amodels.AssetCategory.objects.create(name="Lighting")

    assets = {}

    with reversion.create_revision():
        reversion.set_user(admin_user)
        assets[1] = amodels.Asset.objects.create(
            asset_id="1991", description="Spaceflower", status=broken, category=lighting, date_acquired=date.today()
        )

    with reversion.create_revision():
        reversion.set_user(admin_user)
        assets[2] = amodels.Asset.objects.create(
            asset_id="0001", description="Virgil", status=working, category=lighting, date_acquired=date.today()
        )

    with reversion.create_revision():
        reversion.set_user(admin_user)
        assets[1].status = working
        assets[1].save()

    return assets


def test_history_loads_successfully(admin_client, admin_user):
    events = create_events(admin_user)
    request_url = reverse("event_history", kwargs={"pk": events[1].pk})
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200
    assets = create_assets(admin_user)
    request_url = reverse("asset_history", kwargs={"pk": assets[1].asset_id})
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200


def test_activity_feed_loads_successfully(admin_client):
    request_url = reverse("activity_feed")
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200


def test_activity_table_loads_successfully(admin_client):
    request_url = reverse("activity_table")
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200

    request_url = reverse("assets_activity_table")
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200


# Some edge cases that have caused server errors in the past
def test_deleted_event(admin_client, admin_user):
    events = create_events(admin_user)
    request_url = reverse("activity_feed")

    events[2].delete()

    response = admin_client.get(request_url, follow=True)
    assertContains(response, "TE E2")
    assert response.status_code == 200


def test_deleted_relation(admin_client, admin_user):
    events = create_events(admin_user)
    request_url = reverse("activity_feed")

    with reversion.create_revision():
        person = models.Person.objects.create(name="Test Person")
    with reversion.create_revision():
        events[1].person = person
        events[1].save()

    # Check response contains person
    response = admin_client.get(request_url, follow=True)
    assertContains(response, "Test Person")
    assert response.status_code == 200
    # Delete person
    person.delete()
    # Check response still contains person
    response = admin_client.get(request_url, follow=True)
    assertContains(response, "Test Person")
    assert response.status_code == 200


def test_activity_feed_version_is_stored_without_a_timeout():
    from unittest import mock
    from django.core.cache import cache
    from versioning.versioning import bump_activity_feed_version, activity_feed_version

    with mock.patch.object(cache, "set", wraps=cache.set) as spy:
        bump_activity_feed_version()
    # cache.incr() would store it again with the default 5 minute timeout, after which the feed reverted to a stale one
    assert spy.call_args.args[2] is None

    first = activity_feed_version()
    bump_activity_feed_version()
    assert activity_feed_version() != first


def test_activity_feed_version_after_losing_the_key_is_new():
    from django.core.cache import cache
    from versioning.versioning import bump_activity_feed_version, activity_feed_version

    bump_activity_feed_version()
    first = activity_feed_version()
    cache.clear()
    assert activity_feed_version() not in ("", 0, None, first)


def test_activity_feed_collapses_bulk_invoices(admin_client):
    models.VatRate.objects.create(start_at="2014-03-05", rate=0.20, comment="test1")
    with reversion.create_revision():
        events = [models.Event.objects.create(name=f"Bulk E{i}", start_date="2014-03-05") for i in range(5)]
    with reversion.create_revision():
        for event in events:
            models.Invoice.objects.create(event=event)

    response = admin_client.get(reverse("activity_feed"), follow=True)
    assertContains(response, "Created 5 invoices")
    assert response.content.decode().count("<details") == 1


def test_activity_feed_does_not_collapse_other_models(admin_client):
    with reversion.create_revision():
        for i in range(6):
            models.Person.objects.create(name=f"Bulk Person {i}")

    response = admin_client.get(reverse("activity_feed"), follow=True)
    assertContains(response, "Bulk Person 5")
    assert "<details" not in response.content.decode()
