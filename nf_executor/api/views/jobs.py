import os

from django.utils.text import get_valid_filename
from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from nf_executor.api import models, serializers
from nf_executor.api.enums import JobStatus
from nf_executor.nextflow.runners import get_runner
from nf_executor.nextflow.util import get_callback_url


class LockedWorkflowException(APIException):
    status_code = 423
    default_detail = "This workflow is not accepting new job submissions"
    default_code = 'queue_locked'


class JobListView(generics.ListCreateAPIView):
    """
    See running jobs (get) or create a new one (post)
    """
    queryset = models.Job.objects.all()
    serializer_class = serializers.JobSerializer

    ordering = ('-created',)
    filterset_fields = ('workflow', 'owner', 'status')

    def perform_create(self, serializer: serializers.JobSerializer):
        """
        Explicitly submit the job to an executor backend when the model is created.

        This is a slightly synchronous view. May want to move to a celery background worker in the future.
        """
        data = serializer.validated_data
        if not data["workflow"].is_active:
            # By design, we only lock queue for NEW submissions.
            #   Existing jobs can be run to completion and receive task events.
            raise LockedWorkflowException

        # Assign persistent logging directory. A job ID is unique *per workflow*
        safe_path = os.path.join(
            str(data["workflow"].pk),
            get_valid_filename(data["run_id"])
        )
        data['logs_dir'] = safe_path

        # First save: record work requested by user. The executor will save again once work has been scheduled.
        job = serializer.save()

        runner = get_runner(job)
        callback_url = get_callback_url(self.request, job)
        runner.run(job.params, callback_url)


class JobDetailView(generics.RetrieveDestroyAPIView):
    """
    Once a job is created, it can be viewed (to check status), updated (to force reconciliation of status), or deleted
        (to schedule cancellation)

    If you suspect that downtime has caused job tracking to fail, force detailed check using the query param
        `?force_check=True`. This is a SYNCHRONOUS OPERATION that may involve checking resource APIs,
        and we ask that end users minimize use of this feature.

    (have no fear: reconciliation will be done automatically on a scheduled background process.)
    """
    queryset = models.Job.objects.all()
    serializer_class = serializers.JobDetailSerializer

    def get_object(self):
        """
        Slight hack. GET is generally idempotent, but we allow this because it's making the DB more accurate
        """
        job = super().get_object()
        if self.request.method == 'GET' and self.request.query_params.get('force_check'):
            runner = get_runner(job)
            runner.reconcile_job_status(save=True)
        return job

    def delete(self, request, *args, **kwargs):
        """Keep the model, but allow the runner engine to stop job and mark it canceled"""
        job = self.get_object()
        if not JobStatus.is_active(job):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        runner = get_runner(job)
        runner.cancel()
        return Response(status=status.HTTP_204_NO_CONTENT)
