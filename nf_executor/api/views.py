from rest_framework import generics

from . import models, serializers


class WorkflowListView(generics.ListAPIView):
    """List all known workflows"""
    queryset = models.Workflow.objects.all()
    serializer_class = serializers.WorkflowSerializer

    ordering = ('name', '-version')



class JobListView(generics.ListAPIView):
    queryset = models.Job.objects.all()
    serializer_class = serializers.JobSerializer

    ordering = ('-created',)
    search_fields = ('workflow_id', 'owner')


class TaskListView(generics.ListAPIView):
    queryset = models.Task.objects.all()
    serializer_class = serializers.TaskSerializer

    ordering = ('-submitted_on',)
    search_fields = ('job_id',)

