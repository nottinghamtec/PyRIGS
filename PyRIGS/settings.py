"""
Django settings for PyRIGS project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'gxhy(a#5mhp289_=6xx$7jh=eh$ymxg^ymc+di*0c*geiu3p_e'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['*']

INTERNAL_IPS = ['127.0.0.1']


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'RIGS',

    'debug_toolbar',
    'registration',
    'reversion',
    'widget_tweaks',
)

MIDDLEWARE_CLASSES = (
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'PyRIGS.urls'

WSGI_APPLICATION = 'PyRIGS.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    },
    'legacy': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'alfie.codedinternet.com',
        'NAME': 'tec_rigs',
        'USER': 'tec_rigs',
        'PASSWORD': 'xMNb(b+Giu]&',
    }
}

import dj_database_url
DATABASES['default'] = dj_database_url.config()

# User system
AUTH_USER_MODEL = 'RIGS.Profile'

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/user/login'
LOGOUT_URL = '/user/logout'

ACCOUNT_ACTIVATION_DAYS = 7

# Email
EMAILER_TEST = False
if not DEBUG or EMAILER_TEST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'server.techost.co.uk'
    EMAIL_PORT = 465
    EMAIL_HOST_USER = 'tec'
    EMAIL_HOST_PASSWORD = '***REMOVED***'
    DEFAULT_FROM_EMAIL = 'rigs@nottinghamtec.co.uk'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DATETIME_INPUT_FORMATS = ('%Y-%m-%dT%H:%M','%Y-%m-%dT%H:%M:%S')

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
STATIC_DIRS = (
    os.path.join(BASE_DIR, 'static/')
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR,  'templates'),
)

USE_GRAVATAR=True

TERMS_OF_HIRE_URL = "http://dev.nottinghamtec.co.uk/wp-content/uploads/2014/11/terms.pdf"
