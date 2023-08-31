import os

from django.conf import settings
from django.urls import reverse
from django.utils.text import get_valid_filename
from rest_framework import generics

from nf_executor.api import models, serializers
from nf_executor.nextflow.runners import get_runner


class JobListView(generics.ListCreateAPIView):
    """
    See running jobs (get) or create a new one (post)
    """
    queryset = models.Job.objects.all()
    serializer_class = serializers.JobSerializer

    ordering = ('-created',)
    search_fields = ('workflow_id', 'owner')

    def perform_create(self, serializer: serializers.JobSerializer):
        """
        Explicitly submit the job to an executor backend when the model is created.

        This is a slightly synchronous view. May want to move to a celery background worker in the future.
        """
        data = serializer.validated_data
        # Assign persistent logging directory. A job ID is unique *per workflow*
        safe_path = os.path.join(
            str(data["workflow"].pk),
            get_valid_filename(data["run_id"])
        )
        data['logs_dir'] = safe_path

        # First save: record work requested by user. The executor will save again once work has been scheduled.
        job = serializer.save()

        runner = get_runner(job)
        callback_uri = self.request.build_absolute_uri(
            reverse('nextflow:callback', kwargs={'pk': job.pk})
        )
        runner.run(job.params, callback_uri)
