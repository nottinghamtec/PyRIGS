import pytest
from django.core.management import call_command
from django.template.defaultfilters import striptags
from django.urls import URLPattern, URLResolver
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from pytest_django.asserts import assertRedirects, assertContains, assertNotContains
from pytest_django.asserts import assertTemplateUsed, assertInHTML

from PyRIGS import urls
from RIGS.models import Event, Profile
from assets.models import Asset
from training.tests.test_unit import get_response
from django.db import connection
from django.template.defaultfilters import striptags
from django.urls.exceptions import NoReverseMatch

from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings


def find_urls_recursive(patterns):
    urls_to_check = []
    for url in patterns:
        if isinstance(url, URLResolver):
            urls_to_check += find_urls_recursive(url.url_patterns)
        elif isinstance(url, URLPattern):
            # Skip some things that actually don't need auth (mainly OEmbed JSONs that are essentially just a redirect)
            if url.name is not None and url.name != "closemodal" and "json" not in str(url):
                urls_to_check.append(url)
    return urls_to_check


def get_request_url(url):
    pattern = str(url.pattern)
    try:
        kwargz = {}
        if ":pk>" in pattern:
            kwargz['pk'] = 1
        if ":model>" in pattern:
            kwargz['model'] = "event"
        return reverse(url.name, kwargs=kwargz)
    except NoReverseMatch:
        print("Couldn't test url " + pattern)


@pytest.mark.parametrize("command", ['generateSampleAssetsData', 'generateSampleRIGSData', 'generateSampleUserData',
                                     'deleteSampleData', 'generateSampleTrainingData', 'generate_sample_training_users'])
def test_production_exception(command):
    from django.core.management.base import CommandError
    with pytest.raises(CommandError, match=".*production"):
        call_command(command)


class TestSampleDataGenerator(TestCase):
    @override_settings(DEBUG=True)
    def test_sample_data(self):
        call_command('generateSampleData')
        assert Asset.objects.all().count() > 50
        assert Event.objects.all().count() > 100
        call_command('deleteSampleData')
        assert not Asset.objects.all().exists()
        assert not Event.objects.all().exists()


@override_settings(DEBUG=True)
@pytest.mark.skip(reason="broken")
def test_unauthenticated(client):  # Nothing should be available to the unauthenticated
    call_command('generateSampleData')
    for url in find_urls_recursive(urls.urlpatterns):
        request_url = get_request_url(url)
        if request_url and 'user' not in request_url:  # User module is full of edge cases
            response = client.get(request_url, follow=True, HTTP_HOST='example.com')
            assertContains(response, 'Login')
            if 'application/json+oembed' in response.content.decode():
                assertTemplateUsed(response, 'login_redirect.html')
            else:
                if "embed" in str(url):
                    expected_url = f"{reverse('login_embed')}?next={request_url}"
                else:
                    expected_url = f"{reverse('login')}?next={request_url}"
                assertRedirects(response, expected_url)
    call_command('deleteSampleData')


@override_settings(DEBUG=True)
@pytest.mark.skip(reason="broken")
def test_basic_access(client):
    call_command('generateSampleData')
    assert client.login(username="basic", password="basic")

    url = reverse('asset_list')
    response = client.get(url)
    # Check edit and duplicate buttons NOT shown in list
    assertNotContains(response, 'Edit')
    assertNotContains(response,
                      'Duplicate')  # If this line is randomly failing, check the debug toolbar HTML hasn't crept in

    url = reverse('asset_detail', kwargs={'pk': Asset.objects.first().asset_id})
    response = client.get(url)
    assertNotContains(response, 'Purchase Details')
    assertNotContains(response, 'View Revision History')

    urlz = {'asset_history', 'asset_update', 'asset_duplicate'}
    for url_name in urlz:
        request_url = reverse(url_name, kwargs={'pk': Asset.objects.first().asset_id})
        response = client.get(request_url, follow=True)
        assert response.status_code == 403

    request_url = reverse('supplier_create')
    response = client.get(request_url, follow=True)
    assert response.status_code == 403

    request_url = reverse('supplier_update', kwargs={'pk': 1})
    response = client.get(request_url, follow=True)
    assert response.status_code == 403
    client.logout()
    call_command('deleteSampleData')


@override_settings(DEBUG=True)
@pytest.mark.skip(reason="broken")
def test_keyholder_access(client):
    call_command('generateSampleData')
    assert client.login(username="keyholder", password="keyholder")

    url = reverse('asset_list')
    response = client.get(url)
    # Check edit and duplicate buttons shown in list
    assertContains(response, 'Edit')
    assertContains(response, 'Duplicate')

    url = reverse('asset_detail', kwargs={'pk': Asset.objects.first().asset_id})
    response = client.get(url)
    assertContains(response, 'Purchase Details')
    assertContains(response, 'View Revision History')
    client.logout()
    call_command('deleteSampleData')


def test_search(admin_client, admin_user):
    url = reverse('search')
    response = admin_client.get(url, {'q': "Definetelynothingfoundifwesearchthis"})
    assertContains(response, "No results found")
    response = admin_client.get(url, {'q': admin_user.first_name})
    assertContains(response, admin_user.first_name)
