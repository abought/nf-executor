"""
Views used for nextflow reporting callbacks
"""
import logging

from django.http import HttpRequest
from django.views.generic.detail import SingleObjectMixin

from rest_framework.views import APIView
from rest_framework.response import Response

from nf_executor.api.models import Job
from nf_executor.nextflow.parsers.from_http import  parse_event


logger = logging.getLogger(__name__)


class NextflowCallback(SingleObjectMixin, APIView):
    """
    Receives events from nextflow HTTP callbacks, and parse them into database task/job records
      Payload structure and event names: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http
    """
    http_method_names = ('post',)
    queryset = Job.objects.all()

    def post(self, request: HttpRequest, pk):
        try:
            # As a safeguard, job IDs are included in callback URLs.
            job = self.get_object()
        except Job.DoesNotExist as e:
            logger.critical(f'Received nextflow job status for a job that does not exist: {pk}')
            raise e

        record = parse_event(job, request.body)
        record.save()

        # NF doesn't look at the response: it doesn't even log if the callback is unreachable!
        return Response({
            'success': True,
            'record_id': record.pk,
            'job': job.pk
        })
