import pytest
from django.core.management import call_command
from django.template.defaultfilters import striptags
from django.urls import URLPattern, URLResolver
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from pytest_django.asserts import assertRedirects, assertContains, assertNotContains
from pytest_django.asserts import assertTemplateUsed, assertInHTML

from PyRIGS import urls
from RIGS.models import Event
from assets.models import Asset


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


@pytest.fixture(scope='module', autouse=True)
def sample_data(django_db_blocker):
    with django_db_blocker.unblock():
        from django.conf import settings
        settings.DEBUG = True
        call_command('generateSampleData')
        assert Asset.objects.all().count() > 50
        assert Event.objects.all().count() > 100
        settings.DEBUG = False
        yield
        call_command('flush', '--noinput')
        call_command('migrate')


def test_unauthenticated(client):  # Nothing should be available to the unauthenticated
    for url in find_urls_recursive(urls.urlpatterns):
        request_url = get_request_url(url)
        if request_url and 'user' not in request_url:  # User module is full of edge cases
            response = client.get(request_url, follow=True, HTTP_HOST='example.com')
            assertContains(response, 'Login')
            if 'application/json+oembed' in response.content.decode():
                assertTemplateUsed(response, 'login_redirect.html')
            else:
                if "embed" in str(url):
                    expected_url = "{0}?next={1}".format(reverse('login_embed'), request_url)
                else:
                    expected_url = "{0}?next={1}".format(reverse('login'), request_url)
                assertRedirects(response, expected_url)


def test_page_titles(admin_client):
    for url in filter((lambda u: "embed" not in u.name), find_urls_recursive(urls.urlpatterns)):
        request_url = get_request_url(url)
        response = admin_client.get(request_url)
        if hasattr(response, "context_data") and "page_title" in response.context_data:
            expected_title = striptags(response.context_data["page_title"])
            # try:
            assertInHTML('<title>{} | Rig Information Gathering System'.format(expected_title),
                         response.content.decode())
            print("{} | {}".format(request_url, expected_title))  # If test fails, tell me where!
            # except:
            #    print(response.content.decode(), file=open('output.html', 'w'))


def test_basic_access(client):
    client.logout()
    assert client.login(username="basic", password="basic")

    url = reverse('asset_list')
    response = client.get(url)
    # Check edit and duplicate buttons NOT shown in list
    assertNotContains(response, 'Edit')
    assertNotContains(response,
                      'Duplicate')  # If this line is randomly failing, check the debug toolbar HTML hasn't crept in

    url = reverse('asset_detail', kwargs={'pk': 1})
    response = client.get(url)
    assertNotContains(response, 'Purchase Details')
    assertNotContains(response, 'View Revision History')

    urlz = {'asset_history', 'asset_update', 'asset_duplicate'}
    for url_name in urlz:
        request_url = reverse(url_name, kwargs={'pk': 1})
        response = client.get(request_url, follow=True)
        assert response.status_code == 403

    request_url = reverse('supplier_create')
    response = client.get(request_url, follow=True)
    assert response.status_code == 403

    request_url = reverse('supplier_update', kwargs={'pk': 1})
    response = client.get(request_url, follow=True)
    assert response.status_code == 403
    client.logout()


def test_keyholder_access(client):
    client.logout()
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
    client.logout()
