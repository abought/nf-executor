from rest_framework import generics
from rest_framework.exceptions import NotFound

from nf_executor.api import models, serializers


class TaskListView(generics.ListAPIView):
    """
    List of tasks associated with one particular job. Read only view; at present only NF reports to API
      and payload is nonstandard
    """
    serializer_class = serializers.TaskSerializer

    ordering = ('-submitted_on',)
    filterset_fields = ('status',)

    def get_queryset(self):
        job_id = self.kwargs['job_id']
        if not models.Job.objects.exists(pk=job_id):
            raise NotFound('Specified job ID does not exist')

        return models.Task.objects.filter(job=job_id)
