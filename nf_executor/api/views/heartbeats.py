from rest_framework import generics
from rest_framework.exceptions import NotFound

from nf_executor.api import models, serializers


class HeartbeatListView(generics.ListCreateAPIView):
    """
    See heartbeat messages (living status reports of custom data during a job):

     List all (get), or create a new one (post)
    """
    serializer_class = serializers.HeartbeatSerializer

    ordering = ('-created',)
    search_fields = ('label',)

    def get_queryset(self):
        job_id = self.kwargs['job_id']
        if not models.Job.objects.filter(pk=job_id).exists():
            raise NotFound('Specified job ID does not exist')

        return models.JobHeartbeat.objects.filter(job=job_id)
