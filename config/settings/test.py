from .base import env

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY", default="GgT7r-3]*?]=xDpA|KM4(YB;n;$>B;E!;HT,ZkCq+[-RNK.~}tp6q(2O%|&|bVL")

TEST_RUNNER = "django.test.runner.DiscoverRunner"
