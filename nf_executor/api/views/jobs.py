import os

from django.conf import settings
from django.urls import reverse
from django.utils.text import get_valid_filename
from rest_framework import generics

from nf_executor.api import models, serializers
from nf_executor.nextflow.runners import get_storage
from nf_executor.nextflow.runners.compute import SubprocessExecutor


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

        We could also do this via other means, such as a post-save signal, but we only want this to happen for one view.

        TODO: Make the execution mode configurable per workflow
        """
        data = serializer.validated_data
        safe_path = get_valid_filename(f'{data["workflow"].pk}_{data["run_id"]}')
        storage = get_storage(safe_path)  # Persistent storage for things like logs

        # Local tmp folder assumed to always be a filesystem
        tmp_path = os.path.join(settings.NF_EXECUTOR['workdir'], safe_path)
        executor = SubprocessExecutor(storage, workdir=tmp_path)

        # Assign working directory. A job ID is unique *per workflow*
        data['logs_dir'] = storage.get_home()

        # First save: record work requested by user. The executor will save again once work has been scheduled.
        job = serializer.save()

        # TODO: Make this configurable per workflow in the future, so runners can be replaced in local vs prod
        callback_uri = self.request.build_absolute_uri(
            reverse('nextflow:callback', kwargs={'pk': job.pk})
        )
        executor.run(job, job.params, callback_uri)
