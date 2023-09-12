"""
Simplistic authentication for callback endpoints such as Nextflow "weblog via http".
  (which does not support headers, cookies, etc)

This module relies on relatively weak encryption algorithms because we check a password-analogue token on every request
    and expect to process many events, continuously

The primary use of this is to prevent against nonces being leaked via the DB. There are other compensating controls,
  such as auth being ignored once a job is marked complete for more than 1 day.
"""
import datetime

import bcrypt
from django.utils import timezone


def gen_password(base: bytes):
    return bcrypt.hashpw(base, bcrypt.gensalt())


def check_password(provided, actual, expire_time: 'datetime.datetime' = None) -> bool:
    """This module checks both the content of a password, and whether it should still be trusted"""
    if expire_time and expire_time < timezone.now():
        return False

    if isinstance(provided, str):
        provided = bytes.fromhex(provided)

    return bcrypt.checkpw(provided, actual)

