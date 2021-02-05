from PyRIGS import urls
from django.core.management import call_command
import pytest
from django.urls import URLPattern, URLResolver, reverse
from django.urls.exceptions import NoReverseMatch
from django.test.utils import override_settings
from pytest_django.asserts import assertContains, assertRedirects, assertTemplateUsed, assertInHTML
from django.template.defaultfilters import striptags
from assets import models


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


@pytest.fixture(scope='module')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from django.conf import settings
        settings.DEBUG = True
        call_command('generateSampleData')  # We need stuff setup so we don't get 404 errors everywhere
        settings.DEBUG = False


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


@pytest.mark.django_db(transaction=True)
def test_delete_sample_data(settings):
    settings.DEBUG = True
    call_command('deleteSampleData')

    assert models.Asset.objects.all().count() == 0
    assert models.Supplier.objects.all().count() == 0
