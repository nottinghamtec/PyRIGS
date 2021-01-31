"""
Django settings for PyRIGS project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import datetime
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import secrets

import raven
from envparse import env

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

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

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # Redirect all http requests to https

INTERNAL_IPS = ['127.0.0.1']

ADMINS = [('Tom Price', 'tomtom5152@gmail.com'), ('IT Manager', 'it@nottinghamtec.co.uk'),
          ('Arona Jones', 'arona.jones@nottinghamtec.co.uk')]
if DEBUG:
    ADMINS.append(('Testing Superuser', 'superuser@example.com'))

# Application definition
INSTALLED_APPS = (
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

    'debug_toolbar',
    'registration',
    'reversion',
    'captcha',
    'widget_tweaks',
    'raven.contrib.django.raven_compat',
)

MIDDLEWARE = (
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'PyRIGS.urls'

WSGI_APPLICATION = 'PyRIGS.wsgi.application'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
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

RAVEN_CONFIG = {
    'dsn': env('RAVEN_DSN', default=""),
}

# User system
AUTH_USER_MODEL = 'RIGS.Profile'

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/user/login/'
LOGOUT_URL = '/user/logout/'

ACCOUNT_ACTIVATION_DAYS = 7

# reCAPTCHA settings
RECAPTCHA_PUBLIC_KEY = env('RECAPTCHA_PUBLIC_KEY', default="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")  # If not set, use development key
RECAPTCHA_PRIVATE_KEY = env('RECAPTCHA_PUBLIC_KEY', default="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")  # If not set, use development key
NOCAPTCHA = True

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']

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

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Need to allow seconds as datetime-local input type spits out a time that has seconds
DATETIME_INPUT_FORMATS = ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S')

# Static files (CSS, JavaScript, Images)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
STATIC_DIRS = (
    os.path.join(BASE_DIR, 'static/')
)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'pipeline/built_assets/'),
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
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
