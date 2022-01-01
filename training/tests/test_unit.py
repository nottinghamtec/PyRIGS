import pytest

from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains

pytestmark = pytest.mark.django_db


def test_(admin_client):
    url = reverse('add_qualification')
    response = admin_client.post(url)
    assertFormError(response, 'form', 'name', 'This field is required.')
