from rest_framework import generics

from nf_executor.api import models, serializers


class TaskListView(generics.ListAPIView):
    queryset = models.Task.objects.all()
    serializer_class = serializers.TaskSerializer

    ordering = ('-submitted_on',)
    search_fields = ('job_id',)
