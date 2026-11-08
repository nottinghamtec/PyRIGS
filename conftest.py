import importlib
from django.conf import settings
import django
import pytest
from RIGS.models import VatRate
import os

# z3c.rml got ``del importlib.metadata`` in __init__.py
# reinject the original one here to solve ``module 'importlib' has no attribute 'metadata'``
# what a bullsh*t
import importlib.metadata as _importlib_metadata

importlib.metadata = _importlib_metadata


POSTGRES_IMAGE = "postgres:18.6"
_postgres_container = None


def _start_postgres_container():
    global _postgres_container
    try:
        from testcontainers.community.postgres import PostgresContainer

        _postgres_container = PostgresContainer(POSTGRES_IMAGE, username="rigs", password="rigs", dbname="rigs")
        _postgres_container.start()
    except Exception as error:
        pytest.exit(
            f"Could not start a Postgres container for the tests ({error}). "
            "Start Docker, or point DATABASE_ENGINE/DATABASE_HOST/... at an existing Postgres server.",
            returncode=1,
        )

    database = {
        "DATABASE_ENGINE": "postgresql",
        "DATABASE_NAME": "rigs",
        "DATABASE_USERNAME": "rigs",
        "DATABASE_PASSWORD": "rigs",
        "DATABASE_HOST": _postgres_container.get_container_host_ip(),
        "DATABASE_PORT": str(_postgres_container.get_exposed_port(5432)),
    }
    os.environ.update(database)

    from django.db import connections

    settings.DATABASES["default"].update(
        {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": database["DATABASE_NAME"],
            "USER": database["DATABASE_USERNAME"],
            "PASSWORD": database["DATABASE_PASSWORD"],
            "HOST": database["DATABASE_HOST"],
            "PORT": database["DATABASE_PORT"],
        }
    )
    connections.close_all()
    if hasattr(connections._connections, "default"):
        delattr(connections._connections, "default")


def pytest_configure(config):
    if "DATABASE_ENGINE" not in os.environ and not hasattr(config, "workerinput"):
        _start_postgres_container()

    settings.PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
    settings.WHITENOISE_USE_FINDERS = True
    settings.WHITENOISE_AUTOREFRESH = True
    # TODO Why do we need this, with the above options enabled?
    settings.STATICFILES_DIRS += [
        os.path.join(settings.BASE_DIR, "static/"),
    ]
    django.setup()


def pytest_unconfigure(config):
    if _postgres_container is not None:
        _postgres_container.stop()


@pytest.fixture  # Overrides the one from pytest-django
def admin_user(admin_user):
    admin_user.username = "EventTest"
    admin_user.first_name = "Event"
    admin_user.last_name = "Test"
    admin_user.initials = "ETU"
    admin_user.is_approved = True
    admin_user.is_supervisor = True
    admin_user.save()
    return admin_user


@pytest.fixture(autouse=True)  # Also enables DB access for all tests as a useful side effect
def vat_rate(db):
    vat_rate = VatRate.objects.create(start_at="2014-03-05", rate=0.20, comment="test1")
    yield vat_rate
    vat_rate.delete()


@pytest.fixture(autouse=True)
def activity_feed_bumps_immediately(monkeypatch):
    monkeypatch.setattr("versioning.versioning.on_commit", lambda callback: callback())


def _has_transactional_marker(item):
    db_marker = item.get_closest_marker("django_db")
    if db_marker and db_marker.kwargs.get("transaction"):
        return 1
    return 0


def pytest_collection_modifyitems(items):
    items.sort(key=_has_transactional_marker)
