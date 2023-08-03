"""
Serializers for workflow executor API

Note that there is no write serializer for tasks, because

"""

from rest_framework import serializers as drf_serializers

from . import models as api_models


class WorkflowSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = api_models.Workflow
        fields = ('name', 'description', 'version', 'definition_path')


class JobSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = api_models.Job
        # Signoff: Executor ID is used only for internal functions and not reported to consumers of the API
        fields = (
            'run_id', 'name', 'workflow', 'owner',
            'status', 'success',
            'expire_on', 'start_on', 'duration',
            'succeed_count', 'retries_count',
        )


class TaskSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = api_models.Task
        fields = ('job', 'name', 'status', 'submitted_on', 'started_on', 'completed_on')
