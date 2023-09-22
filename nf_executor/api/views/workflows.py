from rest_framework import generics, views

from nf_executor.api import models, serializers


class WorkflowListView(generics.ListCreateAPIView):
    """List all known workflows"""
    queryset = models.Workflow.objects.all()
    serializer_class = serializers.WorkflowSerializer

    ordering = ('name', '-version')


class WorkflowDetailView(generics.RetrieveUpdateAPIView):
    """
    Can lock a workflow for new job submissions via PATCH request `{is_active: false}`

    There is no mass lock/unlock option, because a real system might contain deprecated or hidden workflows that we
        don't want to reactivate by accident in a bulk mode

    In the future we may implement a totally separate queue lock but this is enough for a prototype
        (oftentimes queue lock might be controlled elsewhere, like in the webapp UI that consumes this service)
    """
    serializer_class = serializers.WorkflowSerializer
    queryset = models.Workflow.objects.all()
