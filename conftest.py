from django.conf import settings
import django


def pytest_configure():
    settings.PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    django.setup()
