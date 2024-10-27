"""
Django settings for PyRIGS project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import datetime
from pathlib import Path
import secrets

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from envparse import env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='gxhy(a#5mhp289_=6xx$7jh=eh$ymxg^ymc+di*0c*geiu3p_e')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', cast=bool, default=True)
STAGING = env('STAGING', cast=bool, default=False)
CI = env('CI', cast=bool, default=False)

ALLOWED_HOSTS = ['pyrigs.nottinghamtec.co.uk', 'rigs.nottinghamtec.co.uk', 'pyrigs.herokuapp.com']

if STAGING:
    ALLOWED_HOSTS.append('.herokuapp.com')

if DEBUG:
    ALLOWED_HOSTS.append('localhost')
    ALLOWED_HOSTS.append('example.com')
    ALLOWED_HOSTS.append('127.0.0.1')
    ALLOWED_HOSTS.append('.app.github.dev')
    CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # Redirect all http requests to https

INTERNAL_IPS = ['127.0.0.1']

DOMAIN = env('DOMAIN', default='example.com')

ADMINS = [('IT Manager', f'it@{DOMAIN}'), ('Arona Jones', f'arona.jones@{DOMAIN}')]
if DEBUG:
    ADMINS.append(('Testing Superuser', 'superuser@example.com'))

# Application definition
INSTALLED_APPS = (
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'versioning',
    'users',
    'RIGS',
    'assets',
    'training',

    # 'debug_toolbar',
    'registration',
    'reversion',
    'widget_tweaks',
    'hcaptcha',
    'massadmin',
)

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'htmlmin.middleware.HtmlMinifyMiddleware',
    'htmlmin.middleware.MarkRequestMiddleware',
)

ROOT_URLCONF = 'PyRIGS.urls'

WSGI_APPLICATION = 'PyRIGS.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}

if not DEBUG:
    import dj_database_url

    DATABASES['default'] = dj_database_url.config()

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': ('%(asctime)s [%(process)d] [%(levelname)s] ' +
                       'pathname=%(pathname)s lineno=%(lineno)s ' +
                       'funcname=%(funcName)s %(message)s'),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'ERROR',
            # But the emails are plain text by default - HTML is nicer
            'include_html': True,
        },
    },
    'loggers': {
        # Again, default Django configuration to email unhandled exceptions
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # Might as well log any errors anywhere else in Django
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}

# Tests lock up SQLite otherwise
if STAGING or CI:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
        }
    }
elif DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }

# Error/performance monitoring
sentry_sdk.init(
    dsn=env('SENTRY_DSN', default=""),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
)

# User system
AUTH_USER_MODEL = 'RIGS.Profile'

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/user/login/'
LOGOUT_URL = '/user/logout/'

ACCOUNT_ACTIVATION_DAYS = 7

# CAPTCHA settings
HCAPTCHA_SITEKEY = env('HCAPTCHA_SITEKEY', '10000000-ffff-ffff-ffff-000000000001')
HCAPTCHA_SECRET = env('HCAPTCHA_SECRET', '0x0000000000000000000000000000000000000000')

# Email
EMAILER_TEST = False
if not DEBUG or EMAILER_TEST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = env('EMAIL_HOST')
    EMAIL_PORT = env('EMAIL_PORT', cast=int, default=25)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
    EMAIL_USE_TLS = env('EMAIL_USE_TLS', cast=bool, default=False)
    EMAIL_USE_SSL = env('EMAIL_USE_SSL', cast=bool, default=False)
    DEFAULT_FROM_EMAIL = env('EMAIL_FROM')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_COOLDOWN = datetime.timedelta(minutes=15)

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Europe/London'

FORMAT_MODULE_PATH = 'PyRIGS.formats'

USE_L10N = True

USE_TZ = True

USE_THOUSAND_SEPARATOR = False

# Need to allow seconds as datetime-local input type spits out a time that has seconds
DATETIME_INPUT_FORMATS = ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S')

# Static files (CSS, JavaScript, Images)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = str(BASE_DIR / 'static/')
STATICFILES_DIRS = [
    str(BASE_DIR / 'pipeline/built_assets'),
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
            'debug': DEBUG
        },
    },
]

USE_GRAVATAR = True

TERMS_OF_HIRE_URL = "http://www.nottinghamtec.co.uk/terms.pdf"
AUTHORISATION_NOTIFICATION_ADDRESS = 'productions@nottinghamtec.co.uk'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE_ENABLED', True)
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE_ENABLED', True)
SECURE_HSTS_PRELOAD = True
