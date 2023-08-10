import os

from django.urls import reverse
from rest_framework import generics

from nf_executor.api import models, serializers
from nf_executor.nextflow.executors import SubprocessExecutor


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
        instance = serializer.instance
        executor = SubprocessExecutor(instance.workflow)

        # Assign working directory. TODO Should this be done by the executor to abstract away infra?
        wd = f'/tmp/nf_executor/{instance.run_id}'
        os.makedirs(wd)
        instance.workdir = wd

        # First save: record work requested by user. The executor will save again once work has been scheduled.
        job = serializer.save()

        # TODO: Make this configurable per workflow in the future, so executors can be replaced in local vs prod
        callback_uri = self.request.build_absolute_uri(reverse('apiv1:jobs-list'))
        executor.run(job, job.params, callback_uri)
