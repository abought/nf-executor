import uuid

from django.urls import reverse
from django.utils.http import urlencode

from nf_executor.api.auth import gen_password
from nf_executor.api.models import Job


def get_callback_url(request, job: Job):
    # We don't store the actual nonce "password" in the DB, so it is only known when the callback URL is first generated
    nonce = uuid.uuid4().bytes
    job.callback_token = gen_password(nonce)
    job.save()

    base_url = request.build_absolute_uri(
        reverse('nextflow:callback', kwargs={'pk': job.pk})
    )

    token = urlencode({'nonce': nonce.hex()})
    return f'{base_url}?{token}'
