import datetime

import pytest
from django.urls import reverse
from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains

from PyRIGS.tests.base import assert_oembed, login

from assets import models

from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_supplier_create(admin_client):
    url = reverse('supplier_create')
    response = admin_client.post(url)
    assertFormError(response, 'form', 'name', 'This field is required.')


def test_supplier_edit(admin_client):
    supplier = models.Supplier.objects.create(name="Gadgetron Corporation")
    url = reverse('supplier_update', kwargs={'pk': supplier.pk})
    response = admin_client.post(url, {'name': ""})
    assertFormError(response, 'form', 'name', 'This field is required.')


def test_404(admin_client):
    urls = {'asset_detail', 'asset_update', 'asset_duplicate', 'supplier_detail', 'supplier_update'}
    for url_name in urls:
        request_url = reverse(url_name, kwargs={'pk': "0000"})
        response = admin_client.get(request_url, follow=True)
        assert response.status_code == 404


def test_embed_login_redirect(client, django_user_model, test_asset):
    request_url = reverse('asset_embed', kwargs={'pk': test_asset.asset_id})
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


def test_x_frame_headers(client, django_user_model, test_asset):
    asset_url = reverse('asset_embed', kwargs={'pk': test_asset.asset_id})
    login_url = reverse('login_embed')

    login(client, django_user_model)

    response = client.get(asset_url, follow=True)
    with pytest.raises(KeyError):
        response.headers["X-Frame-Options"]

    response = client.get(login_url, follow=True)
    with pytest.raises(KeyError):
        response.headers["X-Frame-Options"]


def test_oembed(client, test_asset):
    client.logout()
    asset_url = reverse('asset_detail', kwargs={'pk': test_asset.asset_id})
    asset_embed_url = reverse('asset_embed', kwargs={'pk': test_asset.asset_id})
    oembed_url = reverse('asset_oembed', kwargs={'pk': test_asset.asset_id})

    alt_oembed_url = reverse('asset_oembed', kwargs={'pk': 999})
    alt_asset_embed_url = reverse('asset_embed', kwargs={'pk': 999})

    assert_oembed(alt_asset_embed_url, alt_oembed_url, client, asset_embed_url, asset_url, oembed_url)


def test_asset_create(admin_client):
    response = admin_client.post(reverse('asset_create'), {'date_sold': '2000-01-01', 'date_acquired': '2020-01-01', 'purchase_price': '-30', 'replacement_cost': '-30'})
    assertFormError(response, 'form', 'asset_id', 'This field is required.')
    assert_asset_form_errors(response)


def test_cable_create(admin_client):
    response = admin_client.post(reverse('asset_create'), {'asset_id': 'X$%A', 'is_cable': True})
    assertFormError(response, 'form', 'asset_id', 'An Asset ID can only consist of letters and numbers, with a final number')
    assertFormError(response, 'form', 'cable_type', 'A cable must have a type')
    assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
    assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')


def test_asset_edit(admin_client, test_asset):
    url = reverse('asset_update', kwargs={'pk': test_asset.asset_id})
    response = admin_client.post(url, {'date_sold': '2000-12-01', 'date_acquired': '2020-12-01', 'purchase_price': '-50', 'replacement_cost': '-50', 'description': "", 'status': "", 'category': ""})
    assert_asset_form_errors(response)


def test_cable_edit(admin_client, test_cable):
    url = reverse('asset_update', kwargs={'pk': test_cable.asset_id})
    response = admin_client.post(url, {'is_cable': True, 'length': -3, 'csa': -3})

    # TODO Can't figure out how to select the 'none' option...
    # assertFormError(response, 'form', 'cable_type', 'A cable must have a type')
    assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
    assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')


def test_asset_duplicate(admin_client, test_cable):
    url = reverse('asset_duplicate', kwargs={'pk': test_cable.asset_id})
    response = admin_client.post(url, {'is_cable': True, 'length': 0, 'csa': 0})

    assertFormError(response, 'form', 'length', 'The length of a cable must be more than 0')
    assertFormError(response, 'form', 'csa', 'The CSA of a cable must be more than 0')


def assert_asset_form_errors(response):
    assertFormError(response, 'form', 'description', 'This field is required.')
    assertFormError(response, 'form', 'status', 'This field is required.')
    assertFormError(response, 'form', 'category', 'This field is required.')
    assertFormError(response, 'form', 'date_sold', 'Cannot sell an item before it is acquired')
    assertFormError(response, 'form', 'purchase_price', 'A price cannot be negative')
    assertFormError(response, 'form', 'replacement_cost', 'A price cannot be negative')
