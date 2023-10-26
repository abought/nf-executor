"""
Django settings for nf_executor project.

Generated by 'django-admin startproject' using Django 4.2.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path

import environ

env = environ.Env()

ROOT_DIR = Path(__file__).parents[2]

READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR / '.env'))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# General Django settings
DEBUG = env.bool('DJANGO_DEBUG', False)

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True
LANGUAGE_CODE = 'en-us'

SITE_ID = 1


# Database connections
# ------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ROOT_DIR / "db.sqlite3",
    }  # env.db('DATABASE_URL', ''),
}
DATABASES['default']['ATOMIC_REQUESTS'] = True

# URLs
ROOT_URLCONF = 'config.urls'

ALLOWED_HOSTS = []

# Application definition
DJANGO_APPS = [
    'django.contrib.auth',  # TODO: required by some packages though we don't directly use it in app code; revisit
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]


THIRD_PARTY_APPS = [
    'rest_framework',
    'django_filters',
]

LOCAL_APPS = [
    'nf_executor.api.apps.ApiConfig'
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

STATIC_URL = 'static/'
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    }
]


REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
        "drf_orjson_renderer.parsers.ORJSONParser",
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ),
    'DEFAULT_VERSION': 'v1',
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
}

NF_EXECUTOR = {
    # TODO: Provide production settings to override this. For full production system, consider allowing
    #  storage target to be configured separately for each workflow
    # HOW to run and store results
    'compute': 'nf_executor.nextflow.runners.compute.SubprocessRunner',
    'storage': 'nf_executor.nextflow.runners.storage.LocalStorage',
    # WHERE to run and store results
    'queue': None,  # In production, ARN of a batch queue for NF processes (can be different from queue used for tasks)
    'workdir': '/tmp/nf_executor/work',   # Intermediate files during a run
    'logs_dir': '/tmp/nf_executor/logs',  # Where logs etc. are written. Can be s3 bucket.
}

WSGI_APPLICATION = 'config.wsgi.application'


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = 'DENY'
# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sentry. Specify two buckets: one for python errors (backend) and one for JS (frontend)
# FIXME: update sentry config for 2023 SDKs
# ------------------------------------------------------------------------------
SENTRY_DSN = env('SENTRY_DSN', default=None)
SENTRY_DSN_FRONTEND = env('SENTRY_DSN_FRONTEND', default=None)
