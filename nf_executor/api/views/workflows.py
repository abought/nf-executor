from rest_framework import generics

from nf_executor.api import models, serializers


class WorkflowListView(generics.ListCreateAPIView):
    """List all known workflows"""
    queryset = models.Workflow.objects.all()
    serializer_class = serializers.WorkflowSerializer

    ordering = ('name', '-version')
