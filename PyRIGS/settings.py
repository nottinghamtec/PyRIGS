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

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY') if os.environ.get('SECRET_KEY') else 'gxhy(a#5mhp289_=6xx$7jh=eh$ymxg^ymc+di*0c*geiu3p_e'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(os.environ.get('DEBUG'))) if os.environ.get('DEBUG') else True

STAGING = bool(int(os.environ.get('STAGING'))) if os.environ.get('STAGING') else False

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['pyrigs.nottinghamtec.co.uk', 'rigs.nottinghamtec.co.uk', 'pyrigs.herokuapp.com']

if STAGING:
    ALLOWED_HOSTS.append('.herokuapp.com')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SECURE_SSL_REDIRECT = True # Redirect all http requests to https

INTERNAL_IPS = ['127.0.0.1']

ADMINS = (
    ('Tom Price', 'tomtom5152@gmail.com')
)


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
    'captcha',
    'widget_tweaks',
    'raven.contrib.django.raven_compat',
    'social.apps.django_app.default',
)

MIDDLEWARE_CLASSES = (
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'RIGS.discourse.discourse.DiscourseAuth',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',  # Load remote details
    'social.pipeline.social_auth.social_uid',  # Load remote ID
    'social.pipeline.social_auth.auth_allowed',  # Check not blacklisted
    'social.pipeline.social_auth.social_user',  # If already associated, login
    'RIGS.discourse.pipeline.new_connection',  # Choose a user account, much UI
    'social.pipeline.social_auth.associate_user',  # Associate the social auth with the user
    'social.pipeline.user.user_details',  # Save any details that changed
)

DISCOURSE_HOST=os.environ.get('DISCOURSE_HOST') if os.environ.get('DISCOURSE_HOST') else 'http://localhost:4000'
DISCOURSE_SSO_SECRET=os.environ.get('DISCOURSE_SSO_SECRET') if os.environ.get('DISCOURSE_SSO_SECRET') else 'ABCDEFGHIJKLMNOP'

REGISTRATION_OPEN = False  # Disable built-in django registration - must register using forum

ROOT_URLCONF = 'PyRIGS.urls'

WSGI_APPLICATION = 'PyRIGS.wsgi.application'


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

import raven

RAVEN_CONFIG = {
    'dsn': os.environ.get('RAVEN_DSN'),
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    # 'release': raven.fetch_git_sha(os.path.dirname(os.path.dirname(__file__))),
}

# User system
AUTH_USER_MODEL = 'RIGS.Profile'

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/user/login'
LOGOUT_URL = '/user/logout'

ACCOUNT_ACTIVATION_DAYS = 7

# reCAPTCHA settings
RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY', None)
RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY', None)
NOCAPTCHA = True

# Email
EMAILER_TEST = False
if not DEBUG or EMAILER_TEST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT'))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    EMAIL_USE_TLS = bool(int(os.environ.get('EMAIL_USE_TLS', 0)))
    EMAIL_USE_SSL = bool(int(os.environ.get('EMAIL_USE_SSL', 0)))
    DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_FROM')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Europe/London'

FORMAT_MODULE_PATH = 'PyRIGS.formats'

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
    'social.apps.django_app.context_processors.backends',
    'social.apps.django_app.context_processors.login_redirect',
)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
STATIC_DIRS = (
    os.path.join(BASE_DIR, 'static/')
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR,  'templates'),
)

USE_GRAVATAR=True

TERMS_OF_HIRE_URL = "http://www.nottinghamtec.co.uk/terms.pdf"
