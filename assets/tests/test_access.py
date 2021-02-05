import datetime

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.test.utils import override_settings
from django.urls import reverse
from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains

from PyRIGS.tests.base import assert_oembed, login

from assets import models

from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture(scope='module')
@pytest.mark.db(transaction=True)
def django_db_setup(django_db_setup, django_db_blocker):  # We need stuff setup so we don't get 404 errors everywhere
    with django_db_blocker.unblock():
        from django.conf import settings
        settings.DEBUG = True
        call_command('generateSampleUserData')
        call_command('generateSampleAssetsData')
        settings.DEBUG = False


def test_basic_access(client):
    assert client.login(username="basic", password="basic")

    url = reverse('asset_list')
    response = client.get(url)
    # Check edit and duplicate buttons NOT shown in list
    assertNotContains(response, 'Edit')
    assertNotContains(response, 'Duplicate')

    url = reverse('asset_detail', kwargs={'pk': 1})
    response = client.get(url)
    assertNotContains(response, 'Purchase Details')
    assertNotContains(response, 'View Revision History')

    urls = {'asset_history', 'asset_update', 'asset_duplicate'}
    for url_name in urls:
        request_url = reverse(url_name, kwargs={'pk': 1})
        response = client.get(request_url, follow=True)
        assert response.status_code == 403

    request_url = reverse('supplier_create')
    response = client.get(request_url, follow=True)
    assert response.status_code == 403

    request_url = reverse('supplier_update', kwargs={'pk': 1})
    response = client.get(request_url, follow=True)
    assert response.status_code == 403


def test_keyholder_access(client, django_user_model):
    assert client.login(username="keyholder", password="keyholder")

    url = reverse('asset_list')
    response = client.get(url)
    # Check edit and duplicate buttons shown in list
    assertContains(response, 'Edit')
    assertContains(response, 'Duplicate')

    url = reverse('asset_detail', kwargs={'pk': 1})
    response = client.get(url)
    assertContains(response, 'Purchase Details')
    assertContains(response, 'View Revision History')
