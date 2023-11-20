from datetime import timedelta
import uuid

from django.test import TestCase
from django.utils import timezone

from rest_framework.exceptions import AuthenticationFailed

from abc_impute.nextflow.auth import gen_password
from abc_impute.api.tests.factories import JobFactory
from abc_impute.nextflow.views import check_auth_for_job_event


class TestCallbackAuth(TestCase):
    def test_callback_auth_succeeds(self):
        real_pwd = uuid.uuid4().bytes
        callback_token = gen_password(real_pwd)

        job = JobFactory(is_submitted=True, callback_token=callback_token)

        try:
            check_auth_for_job_event(job, real_pwd)
        except Exception as e:
            print(e)
            self.fail('Valid auth should not raise an exception')

    def test_callback_auth_wrong_password(self):
        real_pwd = uuid.uuid4().bytes
        callback_token = gen_password(real_pwd)

        job = JobFactory(is_submitted=True, callback_token=callback_token)

        with self.assertRaises(AuthenticationFailed, msg='Wrong password should raise error'):
            check_auth_for_job_event(job, 'wrongpassword')

    def test_callback_auth_expired(self):
        real_pwd = uuid.uuid4().bytes
        callback_token = gen_password(real_pwd)

        past = timezone.now() - timedelta(hours=2)
        job = JobFactory(is_completed=True, callback_token=callback_token, completed_on=past)

        with self.assertRaises(AuthenticationFailed, msg='Expired password should raise error'):
            check_auth_for_job_event(job, real_pwd)

    def test_callback_auth_missing(self):
        real_pwd = uuid.uuid4().bytes
        callback_token = gen_password(real_pwd)

        past = timezone.now() - timedelta(hours=2)
        job = JobFactory(is_completed=True, callback_token=callback_token, completed_on=past)

        with self.assertRaises(AuthenticationFailed, msg='Missing password should raise error'):
            check_auth_for_job_event(job, None)

    def test_callback_auth_uses_expire_date_if_not_complete(self):
        real_pwd = uuid.uuid4().bytes
        callback_token = gen_password(real_pwd)

        # Differentiator: completed on gets a grace period, expire is a hard stop, so this should fail
        past = timezone.now() - timedelta(minutes=30)
        job = JobFactory(is_unknown=True, callback_token=callback_token, expire_on=past)

        with self.assertRaises(AuthenticationFailed, msg='Expired job should reject events'):
            check_auth_for_job_event(job, None)
