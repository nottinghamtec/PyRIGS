from datetime import date

from django.urls import reverse
from reversion import revisions as reversion
from pytest_django.asserts import assertContains

from RIGS import models
from assets import models as amodels


def create_events(admin_user):
    models.VatRate.objects.create(start_at='2014-03-05', rate=0.20, comment='test1')

    events = {}

    with reversion.create_revision():
        reversion.set_user(admin_user)
        events[1] = models.Event.objects.create(name="TE E1", start_date=date.today())

    with reversion.create_revision():
        reversion.set_user(admin_user)
        events[2] = models.Event.objects.create(name="TE E2", start_date='2014-03-05')

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
        assets[1] = amodels.Asset.objects.create(asset_id="1991", description="Spaceflower", status=broken,
                                                 category=lighting, date_acquired=date.today())

    with reversion.create_revision():
        reversion.set_user(admin_user)
        assets[2] = amodels.Asset.objects.create(asset_id="0001", description="Virgil", status=working,
                                                 category=lighting, date_acquired=date.today())

    with reversion.create_revision():
        reversion.set_user(admin_user)
        assets[1].status = working
        assets[1].save()

    return assets


def test_history_loads_successfully(admin_client, admin_user):
    events = create_events(admin_user)
    request_url = reverse('event_history', kwargs={'pk': events[1].pk})
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200
    assets = create_assets(admin_user)
    request_url = reverse('asset_history', kwargs={'pk': assets[1].asset_id})
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200


def test_activity_feed_loads_successfully(admin_client):
    request_url = reverse('activity_feed')
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200


def test_activity_table_loads_successfully(admin_client):
    request_url = reverse('activity_table')
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200

    request_url = reverse('assets_activity_table')
    response = admin_client.get(request_url, follow=True)
    assert response.status_code == 200


# Some edge cases that have caused server errors in the past
def test_deleted_event(admin_client, admin_user):
    events = create_events(admin_user)
    request_url = reverse('activity_feed')

    events[2].delete()

    response = admin_client.get(request_url, follow=True)
    assertContains(response, "TE E2")
    assert response.status_code == 200


def test_deleted_relation(admin_client, admin_user):
    events = create_events(admin_user)
    request_url = reverse('activity_feed')

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
