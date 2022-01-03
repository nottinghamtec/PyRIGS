import pytest

from pytest_django.asserts import assertFormError, assertRedirects, assertContains, assertNotContains

pytestmark = pytest.mark.django_db
