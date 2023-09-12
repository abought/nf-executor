"""
Views used for nextflow reporting callbacks
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.views.generic.detail import SingleObjectMixin

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from nf_executor.nextflow.auth import check_password
from nf_executor.api.models import Job
from nf_executor.nextflow.parsers.from_http import parse_event


logger = logging.getLogger(__name__)


def check_auth_for_job_event(job, nonce):
    """
    Basic authentication check for URL query param based callbacks

    NEVER USE URL BASED AUTH IN EXTERNAL ENDPOINTS, because then the "real" password value gets captured in logs etc
        (we don't store in DB, but there are other ways to store something)

    This mechanism is designed for Nextflow's internal HTTP callbacks, which don't support custom headers or payloads.
    """
    if not nonce:
        raise AuthenticationFailed('No nonce provided')

    # Once a job is done, stop accepting new events (with a tiny grace period for out of order event delivery)
    if job.completed_on:
        end = job.completed_on + timedelta(hours=1)
    else:
        end = job.expire_on

    try:
        res = check_password(nonce, job.callback_token, expire_time=end)
    except:
        logger.debug('Unknown failure in password check')
        res = False

    if res is False:
        raise AuthenticationFailed('Invalid or expired nonce on callback')


class NextflowCallback(SingleObjectMixin, APIView):
    """
    Receives events from nextflow HTTP callbacks, and parse them into database task/job records
      Payload structure and event names: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http
    """
    http_method_names = ('post',)
    queryset = Job.objects.all()

    def post(self, request: Request, pk):
        try:
            # As a safeguard, job IDs are included in callback URLs. We use this to associate tasks with the right job.
            job = self.get_object()
        except Job.DoesNotExist as e:
            logger.critical(f'Received nextflow job status for a job that does not exist: {pk}')
            raise e

        check_auth_for_job_event(job, request.query_params.get('nonce'))

        record = parse_event(job, request.body)
        record.save()

        # NF doesn't look at the response: it doesn't even log if the callback is unreachable!
        return Response({
            'success': True,
            'record_id': record.pk,
            'job': job.pk
        })


if settings.DEBUG:
    import json
    from django.views.decorators.csrf import csrf_exempt

    items = []  # Store items from the whole workflow until end

    @csrf_exempt
    def json_capture(request):
        """
        A simple endpoint for debugging/verification purposes.
         Captures raw HTTP payloads from a single nextflow process run manually outside the app.

        *Everything about this code is a hack*, but it's useful for characterizing NF behavior
        """
        global items

        if request.method == 'POST':
            payload = json.loads(request.body)
            event = payload['event']
            run_id = payload['runId']

            items.append(payload)

            if event == 'completed':
                with open(f'captured_{run_id}.json', 'w') as f:
                    json.dump(items, f)

                items = []

        return HttpResponse({
            'accepted': True
        })
