import datetime

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains

from assets import models, urls

pytestmark = pytest.mark.django_db  # TODO


def login(client, django_user_model):
    pwd = 'testuser'
    usr = "TestUser"
    django_user_model.objects.create_user(username=usr, email="TestUser@test.com", password=pwd, is_superuser=True, is_active=True, is_staff=True)
    assert client.login(username=usr, password=pwd)


def create_test_asset():
    working = models.AssetStatus.objects.create(name="Working", should_show=True)
    lighting = models.AssetCategory.objects.create(name="Lighting")
    asset = models.Asset.objects.create(asset_id="1991", description="Spaceflower", status=working, category=lighting, date_acquired=datetime.date(1991, 12, 26))
    return asset


def create_test_cable():
    category = models.AssetCategory.objects.create(name="Sound")
    status = models.AssetStatus.objects.create(name="Broken", should_show=True)
    connector = models.Connector.objects.create(description="16A IEC", current_rating=16, voltage_rating=240, num_pins=3)
    cable_type = models.CableType.objects.create(circuits=11, cores=3, plug=connector, socket=connector)
    return models.Asset.objects.create(asset_id="666", description="125A -> Jack", comments="The cable from Hell...", status=status, category=category, date_acquired=datetime.date(2006, 6, 6), is_cable=True, cable_type=cable_type, length=10, csa="1.5")


def test_supplier_create(client, django_user_model):
    login(client, django_user_model)
    url = reverse('supplier_create')
    response = client.post(url)
    assertFormError(response, 'form', 'name', 'This field is required.')


def test_supplier_edit(client, django_user_model):
    login(client, django_user_model)
    supplier = models.Supplier.objects.create(name="Gadgetron Corporation")
    url = reverse('supplier_update', kwargs={'pk': supplier.pk})
    response = client.post(url, {'name': ""})
    assertFormError(response, 'form', 'name', 'This field is required.')


def test_404(client, django_user_model):
    login(client, django_user_model)
    urls = {'asset_detail', 'asset_update', 'asset_duplicate', 'supplier_detail', 'supplier_update'}
    for url_name in urls:
        request_url = reverse(url_name, kwargs={'pk': "0000"})
        response = client.get(request_url, follow=True)
        assert response.status_code == 404


def test_embed_login_redirect(client, django_user_model):
    request_url = reverse('asset_embed', kwargs={'pk': create_test_asset().asset_id})
    expected_url = "{0}?next={1}".format(reverse('login_embed'), request_url)

    # Request the page and check it redirects
    response = client.get(request_url, follow=True)
    assertRedirects(response, expected_url, status_code=302, target_status_code=200)

    # Now login
    login(client, django_user_model)

    # And check that it no longer redirects
    response = client.get(request_url, follow=True)
    assert len(response.redirect_chain) == 0


def test_login_cookie_warning(client, django_user_model):
    login_url = reverse('login_embed')
    response = client.post(login_url, follow=True)
    assert "Cookies do not seem to be enabled" in str(response.content)


def test_x_frame_headers(client, django_user_model):
    asset_url = reverse('asset_embed', kwargs={'pk': create_test_asset().asset_id})
    login_url = reverse('login_embed')

    login(client, django_user_model)

    response = client.get(asset_url, follow=True)
    with pytest.raises(KeyError):
        response._headers["X-Frame-Options"]

    response = client.get(login_url, follow=True)
    with pytest.raises(KeyError):
        response._headers["X-Frame-Options"]


def test_oembed(client):
    asset = create_test_asset()
    asset_url = reverse('asset_detail', kwargs={'pk': asset.asset_id})
    asset_embed_url = reverse('asset_embed', kwargs={'pk': asset.asset_id})
    oembed_url = reverse('asset_oembed', kwargs={'pk': asset.asset_id})

    alt_oembed_url = reverse('asset_oembed', kwargs={'pk': 999})
    alt_asset_embed_url = reverse('asset_embed', kwargs={'pk': 999})

    # Test the meta tag is in place
    response = client.get(asset_url, follow=True, HTTP_HOST='example.com')
    assert '<link rel="alternate" type="application/json+oembed"' in str(response.content)
    assertContains(response, oembed_url)

    # Test that the JSON exists
    response = client.get(oembed_url, follow=True, HTTP_HOST='example.com')
    assert response.status_code == 200
    assertContains(response, asset_embed_url)

    # Should also work for non-existant
    response = client.get(alt_oembed_url, follow=True, HTTP_HOST='example.com')
    assert response.status_code == 200
    assertContains(response, alt_asset_embed_url)


@override_settings(DEBUG=True)
def test_generate_sample_data(client):
    # Run the management command and check there are no exceptions
    call_command('generateSampleAssetsData')

    # Check there are lots
    assert models.Asset.objects.all().count() > 50
    assert models.Supplier.objects.all().count() > 50


@override_settings(DEBUG=True)
def test_delete_sample_data(client):
    call_command('deleteSampleData')

    assert models.Asset.objects.all().count() == 0
    assert models.Supplier.objects.all().count() == 0


def test_production_exception(client):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match=".*production"):
        call_command('generateSampleAssetsData')
        call_command('deleteSampleData')


def test_asset_create(client, django_user_model):
    login(client, django_user_model)
    response = client.post(reverse('asset_create'), {'date_sold': '2000-01-01', 'date_acquired': '2020-01-01', 'purchase_price': '-30', 'salvage_value': '-30'})
    assertFormError(response, 'form', 'asset_id', 'This field is required.')
    assertFormError(response, 'form', 'description', 'This field is required.')
    assertFormError(response, 'form', 'status', 'This field is required.')
    assertFormError(response, 'form', 'category', 'This field is required.')

    assertFormError(response, 'form', 'date_sold', 'Cannot sell an item before it is acquired')
    assertFormError(response, 'form', 'purchase_price', 'A price cannot be negative')
    assertFormError(response, 'form', 'salvage_value', 'A price cannot be negative')


def test_cable_create(client, django_user_model):
    login(client, django_user_model)
    response = client.post(reverse('asset_create'), {'asset_id': 'X$%A', 'is_cable': True})
    assertFormError(response, 'form', 'asset_id', 'An Asset ID can only consist of letters and numbers, with a final number')

    assertFormError(response, 'form', 'cable_type', 'A cable must have a type')
    assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
    assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')

# Given that validation is done at model level it *shouldn't* need retesting...gonna do it anyway!


def test_asset_edit(client, django_user_model):
    login(client, django_user_model)
    url = reverse('asset_update', kwargs={'pk': create_test_asset().asset_id})
    response = client.post(url, {'date_sold': '2000-12-01', 'date_acquired': '2020-12-01', 'purchase_price': '-50', 'salvage_value': '-50', 'description': "", 'status': "", 'category': ""})
    # assertFormError(response, 'form', 'asset_id', 'This field is required.')
    assertFormError(response, 'form', 'description', 'This field is required.')
    assertFormError(response, 'form', 'status', 'This field is required.')
    assertFormError(response, 'form', 'category', 'This field is required.')
    assertFormError(response, 'form', 'date_sold', 'Cannot sell an item before it is acquired')
    assertFormError(response, 'form', 'purchase_price', 'A price cannot be negative')
    assertFormError(response, 'form', 'salvage_value', 'A price cannot be negative')


def test_cable_edit(client, django_user_model):
    login(client, django_user_model)
    url = reverse('asset_update', kwargs={'pk': create_test_cable().asset_id})
    # TODO Why do I have to send is_cable=True here?
    response = client.post(url, {'is_cable': True, 'length': -3, 'csa': -3})

    # TODO Can't figure out how to select the 'none' option...
    # assertFormError(response, 'form', 'cable_type', 'A cable must have a type')
    assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
    assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')


def test_asset_duplicate(client, django_user_model):
    login(client, django_user_model)
    url = reverse('asset_duplicate', kwargs={'pk': create_test_cable().asset_id})
    response = client.post(url, {'is_cable': True, 'length': 0, 'csa': 0})

    assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
    assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')


@override_settings(DEBUG=True)
def create_asset_one():
    # Shortcut to create the levels - bonus side effect of testing the command (hopefully) matches production
    call_command('generateSampleData')
    # Create an asset with ID 1 to make things easier in loops (we can always use pk=1)
    category = models.AssetCategory.objects.create(name="Number One")
    status = models.AssetStatus.objects.create(name="Probably Fine", should_show=True)
    return models.Asset.objects.create(asset_id="1", description="Half Price Fish", status=status, category=category, date_acquired=datetime.date(2020, 2, 1))


def test_basic_access(client):
    create_asset_one()
    client.login(username="basic", password="basic")

    url = reverse('asset_list')
    response = client.get(url)
    # Check edit and duplicate buttons NOT shown in list
    assertNotContains(response, 'Edit')
    assertNotContains(response, 'Duplicate')

    url = reverse('asset_detail', kwargs={'pk': "9000"})
    response = client.get(url)
    assertNotContains(response, 'Purchase Details')
    assertNotContains(response, 'View Revision History')

    urls = {'asset_history', 'asset_update', 'asset_duplicate'}
    for url_name in urls:
        request_url = reverse(url_name, kwargs={'pk': "9000"})
        response = client.get(request_url, follow=True)
        assert response.status_code == 403

    request_url = reverse('supplier_create')
    response = client.get(request_url, follow=True)
    assert response.status_code == 403

    request_url = reverse('supplier_update', kwargs={'pk': "1"})
    response = client.get(request_url, follow=True)
    assert response.status_code == 403


def test_keyholder_access(client):
    create_asset_one()
    client.login(username="keyholder", password="keyholder")

    url = reverse('asset_list')
    response = client.get(url)
    # Check edit and duplicate buttons shown in list
    assertContains(response, 'Edit')
    assertContains(response, 'Duplicate')

    url = reverse('asset_detail', kwargs={'pk': "9000"})
    response = client.get(url)
    assertContains(response, 'Purchase Details')
    assertContains(response, 'View Revision History')
