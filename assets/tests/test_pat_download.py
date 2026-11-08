from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from storages.backends.s3 import S3Storage

from assets import models, pat
from assets.tests import sss_builder as b

pytestmark = pytest.mark.django_db


@pytest.fixture
def uploaded(admin_client, pat_asset):
    """An upload whose file really is in the local test storage"""

    def make(name="march.sss"):
        admin_client.post(reverse("pat_upload"), {"file": SimpleUploadedFile(name, b.sss_file(b.test_result()))})
        return models.PATTestBatch.objects.get(original_filename=name)

    return make


@pytest.fixture
def stored(db):
    """An upload recorded as being in the Space. Nothing is sent: links are signed without contacting it"""

    def make(name="march.sss"):
        return models.PATTestBatch.objects.create(
            original_filename=name, sha256="a" * 64, file="pat/2026/11/0123456789abcdef.sss"
        )

    return make


@pytest.fixture
def spaces(settings, monkeypatch):
    """Files are kept in a DigitalOcean Space. Signing a link makes no request, so no real bucket is needed"""
    settings.STORAGES = {**settings.STORAGES, "default": {"BACKEND": pat.S3_BACKEND}}
    settings.AWS_STORAGE_BUCKET_NAME = "pat-test-results"
    settings.AWS_S3_ENDPOINT_URL = "https://lon1.digitaloceanspaces.com"
    settings.AWS_S3_REGION_NAME = "lon1"
    settings.AWS_S3_SIGNATURE_VERSION = "s3v4"
    settings.AWS_S3_ADDRESSING_STYLE = "auto"
    settings.AWS_ACCESS_KEY_ID = "DO00EXAMPLEKEY"
    settings.AWS_SECRET_ACCESS_KEY = "example-secret"
    settings.AWS_DEFAULT_ACL = None
    settings.AWS_QUERYSTRING_AUTH = True
    monkeypatch.setattr(S3Storage, "exists", lambda self, name: True)
    return settings


def location(response):
    url = urlsplit(response["Location"])
    return url, parse_qs(url.query)


def test_with_spaces_the_download_redirects_to_a_signed_link(admin_client, stored, spaces):
    batch = stored()
    response = admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk}))
    url, query = location(response)

    assert response.status_code == 302
    assert url.scheme == "https"
    # with a custom endpoint the default addressing puts the bucket in the path
    assert url.netloc == "lon1.digitaloceanspaces.com"
    assert url.path == f"/pat-test-results/{batch.file.name}"
    assert query["X-Amz-Expires"] == ["60"]
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-Signature"][0]
    assert "lon1" in query["X-Amz-Credential"][0]


def test_virtual_hosted_addressing_puts_the_bucket_in_the_host_name(admin_client, stored, spaces):
    spaces.AWS_S3_ADDRESSING_STYLE = "virtual"
    batch = stored()
    url, query = location(admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})))
    assert url.netloc == "pat-test-results.lon1.digitaloceanspaces.com"
    assert url.path == f"/{batch.file.name}"
    assert query["X-Amz-Signature"][0]


def test_the_link_downloads_the_file_under_its_original_name(admin_client, stored, spaces):
    batch = stored("march.sss")
    _, query = location(admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})))
    assert query["response-content-disposition"] == ['attachment; filename="march.sss"']
    assert query["response-content-type"] == ["application/octet-stream"]


def test_awkward_file_names_are_encoded(admin_client, stored, spaces):
    batch = stored("tést résults.sss")
    _, query = location(admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})))
    assert query["response-content-disposition"] == ["attachment; filename*=utf-8''t%C3%A9st%20r%C3%A9sults.sss"]


def test_the_redirect_is_not_cached(admin_client, stored, spaces):
    batch = stored()
    response = admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk}))
    assert "no-cache" in response["Cache-Control"] and "no-store" in response["Cache-Control"]


def test_in_development_the_link_names_the_address_a_browser_can_reach(admin_client, stored, spaces):
    spaces.AWS_S3_ENDPOINT_URL = "http://s3:7070"
    spaces.AWS_S3_PUBLIC_ENDPOINT_URL = "http://localhost:7070"
    spaces.AWS_S3_ADDRESSING_STYLE = "path"
    batch = stored()
    url, query = location(admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})))
    assert url.netloc == "localhost:7070"
    assert url.path == f"/pat-test-results/{batch.file.name}"
    assert query["X-Amz-Signature"][0]


def test_without_a_public_address_the_normal_one_is_used(admin_client, stored, spaces):
    spaces.AWS_S3_PUBLIC_ENDPOINT_URL = None
    batch = stored()
    url, _ = location(admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})))
    assert url.netloc == "lon1.digitaloceanspaces.com"


def test_a_file_that_is_no_longer_in_the_store_is_a_404(admin_client, stored, spaces, monkeypatch):
    batch = stored()
    monkeypatch.setattr(S3Storage, "exists", lambda self, name: False)
    assert admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})).status_code == 404


def test_permission_is_checked_before_any_link_is_made(client, django_user_model, stored, spaces, monkeypatch):
    batch = stored()
    monkeypatch.setattr(pat, "signed_download_url", lambda *args, **kwargs: pytest.fail("a link was made"))
    user = django_user_model.objects.create_user(username="someone", password="x")
    user.user_permissions.add(Permission.objects.get(codename="add_pattestbatch"))
    client.force_login(user)
    assert client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})).status_code == 403
    client.logout()
    assert client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})).status_code == 302


def test_a_user_who_may_download_is_redirected(client, django_user_model, stored, spaces):
    batch = stored()
    user = django_user_model.objects.create_user(username="viewer", password="x")
    user.user_permissions.add(Permission.objects.get(codename="view_pattestbatch"))
    client.force_login(user)
    response = client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk}))
    assert response.status_code == 302
    assert "digitaloceanspaces.com" in response["Location"]


def test_without_spaces_the_file_is_still_streamed_through_the_app(admin_client, uploaded):
    batch = uploaded("march.sss")
    assert pat.signed_download_url(batch) is None
    response = admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk}))
    assert response.status_code == 200
    assert 'attachment; filename="march.sss"' in response["Content-Disposition"]
    assert b"".join(response.streaming_content).startswith(b"U")  # the .sss file itself


def test_links_expire_quickly(admin_client, stored, spaces):
    batch = stored()
    _, query = location(admin_client.get(reverse("pat_batch_download", kwargs={"pk": batch.pk})))
    assert int(query["X-Amz-Expires"][0]) <= 60
