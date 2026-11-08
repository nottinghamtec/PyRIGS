import pytest
from django.core.management import call_command
from django.urls import URLPattern, URLResolver
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from pytest_django.asserts import assertRedirects, assertContains, assertNotContains
from pytest_django.asserts import assertTemplateUsed

from PyRIGS import urls
from RIGS.models import Event
from assets.models import Asset

from django.test import TestCase
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
            kwargz["pk"] = 1
        if ":model>" in pattern:
            kwargz["model"] = "event"
        return reverse(url.name, kwargs=kwargz)
    except NoReverseMatch:
        print("Couldn't test url " + pattern)


@pytest.mark.parametrize(
    "command",
    [
        "generateSampleAssetsData",
        "generateSampleRIGSData",
        "generateSampleUserData",
        "deleteSampleData",
        "generateSampleTrainingData",
        "generate_sample_training_users",
    ],
)
def test_production_exception(command):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match=".*production"):
        call_command(command)


class TestSampleDataGenerator(TestCase):
    @override_settings(DEBUG=True)
    def test_sample_data(self):
        call_command("generateSampleData")
        assert Asset.objects.all().count() > 50
        assert Event.objects.all().count() > 100
        call_command("deleteSampleData")
        assert not Asset.objects.all().exists()
        assert not Event.objects.all().exists()


@override_settings(DEBUG=True)
@pytest.mark.skip(reason="broken")
def test_unauthenticated(client):  # Nothing should be available to the unauthenticated
    call_command("generateSampleData")
    for url in find_urls_recursive(urls.urlpatterns):
        request_url = get_request_url(url)
        if request_url and "user" not in request_url:  # User module is full of edge cases
            response = client.get(request_url, follow=True, HTTP_HOST="example.com")
            assertContains(response, "Login")
            if "application/json+oembed" in response.content.decode():
                assertTemplateUsed(response, "login_redirect.html")
            else:
                if "embed" in str(url):
                    expected_url = f"{reverse('login_embed')}?next={request_url}"
                else:
                    expected_url = f"{reverse('login')}?next={request_url}"
                assertRedirects(response, expected_url)
    call_command("deleteSampleData")


@override_settings(DEBUG=True)
@pytest.mark.skip(reason="broken")
def test_basic_access(client):
    call_command("generateSampleData")
    assert client.login(username="basic", password="basic")

    url = reverse("asset_list")
    response = client.get(url)
    # Check edit and duplicate buttons NOT shown in list
    assertNotContains(response, "Edit")
    assertNotContains(
        response, "Duplicate"
    )  # If this line is randomly failing, check the debug toolbar HTML hasn't crept in

    url = reverse("asset_detail", kwargs={"pk": Asset.objects.first().asset_id})
    response = client.get(url)
    assertNotContains(response, "Purchase Details")
    assertNotContains(response, "View Revision History")

    urlz = {"asset_history", "asset_update", "asset_duplicate"}
    for url_name in urlz:
        request_url = reverse(url_name, kwargs={"pk": Asset.objects.first().asset_id})
        response = client.get(request_url, follow=True)
        assert response.status_code == 403

    request_url = reverse("supplier_create")
    response = client.get(request_url, follow=True)
    assert response.status_code == 403

    request_url = reverse("supplier_update", kwargs={"pk": 1})
    response = client.get(request_url, follow=True)
    assert response.status_code == 403
    client.logout()
    call_command("deleteSampleData")


@override_settings(DEBUG=True)
@pytest.mark.skip(reason="broken")
def test_keyholder_access(client):
    call_command("generateSampleData")
    assert client.login(username="keyholder", password="keyholder")

    url = reverse("asset_list")
    response = client.get(url)
    # Check edit and duplicate buttons shown in list
    assertContains(response, "Edit")
    assertContains(response, "Duplicate")

    url = reverse("asset_detail", kwargs={"pk": Asset.objects.first().asset_id})
    response = client.get(url)
    assertContains(response, "Purchase Details")
    assertContains(response, "View Revision History")
    client.logout()
    call_command("deleteSampleData")


def test_search(admin_client, admin_user):
    url = reverse("search")
    response = admin_client.get(url, {"q": "Definetelynothingfoundifwesearchthis"})
    assertContains(response, "No results found")
    response = admin_client.get(url, {"q": admin_user.first_name})
    assertContains(response, admin_user.first_name)


@pytest.mark.django_db
@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
def test_duplicate_form_submission_is_deduplicated(admin_client):
    from django.core.cache import cache
    from RIGS.models import Person

    cache.clear()
    data = {
        "name": "Dupe Tester",
        "email": "",
        "phone": "",
        "address": "",
        "notes": "",
        "csrfmiddlewaretoken": "nonce-a",
    }
    first = admin_client.post(reverse("person_create"), data)
    second = admin_client.post(reverse("person_create"), data)
    assert first.status_code == 302
    assert second.status_code == 302
    assert second.url == first.url
    assert Person.objects.filter(name="Dupe Tester").count() == 1

    # A different render of the form is a different submission
    data["csrfmiddlewaretoken"] = "nonce-b"
    admin_client.post(reverse("person_create"), data)
    assert Person.objects.filter(name="Dupe Tester").count() == 2


@pytest.mark.django_db
@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
def test_duplicate_submission_while_in_flight_does_not_block(admin_client):
    from django.core.cache import cache
    from RIGS.models import Person
    from PyRIGS.middleware import DuplicateSubmissionMiddleware, IN_FLIGHT

    cache.clear()
    cache.set(DuplicateSubmissionMiddleware.cache_key("nonce-c"), IN_FLIGHT, 60)
    data = {
        "name": "Inflight Tester",
        "email": "",
        "phone": "",
        "address": "",
        "notes": "",
        "csrfmiddlewaretoken": "nonce-c",
    }
    response = admin_client.post(reverse("person_create"), data)
    assert response.status_code == 409
    assert not Person.objects.filter(name="Inflight Tester").exists()


@pytest.mark.parametrize(
    "version, shown",
    [("HTTP/3.0", True), ("HTTP/2.0", False), ("HTTP/1.1", False), (None, False)],
)
def test_footer_shows_h3_only_for_http3(admin_client, version, shown):
    extra = {"HTTP_X_HTTP_VERSION": version} if version else {}
    response = admin_client.get(reverse("index"), **extra)
    assert ("Connected over HTTP/3" in response.content.decode()) is shown


@pytest.fixture
def access_entries():
    import json
    import logging

    class Collect(logging.Handler):
        def __init__(self):
            super().__init__()
            self.entries = []

        def emit(self, record):
            self.entries.append(json.loads(record.getMessage()))

    handler = Collect()
    logger = logging.getLogger("pyrigs.access")
    logger.addHandler(handler)
    yield handler.entries
    logger.removeHandler(handler)


def test_daily_file_handler_rolls_each_day_and_keeps_thirty(tmp_path):
    import datetime
    import logging

    from PyRIGS.logging import DailyFileHandler

    def record_on(day):
        stamp = datetime.datetime.combine(day, datetime.time(12), datetime.timezone.utc).timestamp()
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "line %s", (day,), None)
        record.created = stamp
        return record

    today = datetime.date(2026, 11, 8)
    for age in (45, 30, 29, 28):
        (tmp_path / f"access.{today - datetime.timedelta(days=age)}.log").write_text("old\n")
    (tmp_path / "unrelated.log").write_text("keep\n")

    handler = DailyFileHandler(tmp_path, backup_count=30)
    handler.emit(record_on(today))
    handler.emit(record_on(today))
    handler.emit(record_on(today + datetime.timedelta(days=1)))
    handler.close()

    assert (tmp_path / "access.2026-11-08.log").read_text().splitlines() == ["line 2026-11-08"] * 2
    assert (tmp_path / "access.2026-11-09.log").exists()
    names = {p.name for p in tmp_path.iterdir()}
    assert "unrelated.log" in names
    # The last file written is for the 9th, so thirty days means 2026-10-11 onwards: 28 days before the 8th is kept
    assert f"access.{today - datetime.timedelta(days=28)}.log" in names
    assert f"access.{today - datetime.timedelta(days=29)}.log" not in names
    assert f"access.{today - datetime.timedelta(days=30)}.log" not in names
    assert f"access.{today - datetime.timedelta(days=45)}.log" not in names


@pytest.mark.django_db
def test_access_log_records_user_and_skips_static(admin_client, admin_user, access_entries, settings):
    settings.ACCESS_LOG_FIELDS = ["ip", "user_id", "username", "method", "path", "status", "query"]
    admin_client.get(reverse("index") + "?x=1", HTTP_X_REAL_IP="203.0.113.7")
    admin_client.get("/static/does-not-exist.css")
    entries = access_entries
    assert len(entries) == 1
    assert entries[0] == {
        "ip": "203.0.113.7",
        "user_id": admin_user.pk,
        "username": admin_user.get_username(),
        "method": "GET",
        "path": reverse("index"),
        "status": entries[0]["status"],
        "query": "x=1",
    }


@pytest.mark.django_db
def test_access_log_anonymous_user_is_null(client, access_entries):
    client.get(reverse("index"))
    entry = access_entries[0]
    assert entry["user_id"] is None
    assert entry["username"] is None


@pytest.mark.django_db
def test_access_log_records_api_key_user(client, admin_user, access_entries, settings):
    settings.ACCESS_LOG_FIELDS = ["user_id", "username", "view", "status"]
    admin_user.api_key = "k3y"
    admin_user.save()
    client.get(reverse("ics_calendar", kwargs={"api_pk": admin_user.pk, "api_key": "k3y"}))
    client.get(
        reverse("lookup", kwargs={"kind": "venues"}),
        {"q": "barn"},
        headers={"Authorization": f"Bearer {admin_user.pk}:k3y"},
    )
    client.get(reverse("ics_calendar", kwargs={"api_pk": admin_user.pk, "api_key": "wrong"}))
    assert [(e["user_id"], e["view"], e["status"]) for e in access_entries] == [
        (admin_user.pk, "ics_calendar", 200),
        (admin_user.pk, "lookup", 200),
        (None, "ics_calendar", 403),
    ]
