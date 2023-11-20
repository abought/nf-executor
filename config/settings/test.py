from .base import *  # noqa
from .base import env

SECRET_KEY = env("DJANGO_SECRET_KEY", default="GgT7r-3]*?]=xDpA|KM4(YB;n;$>B;E!;HT,ZkCq+[-RNK.~}tp6q(2O%|&|bVL")

TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = 'http://media.testserver/'
