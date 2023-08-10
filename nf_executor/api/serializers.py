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
        # Signoff: Executor ID & workdir are used only for internal functions and not reported to consumers of the API
        fields = (
            'run_id', 'workflow', 'params', 'owner',
            'status', 'expire_on', 'started_on', 'completed_on', 'duration',
            'succeed_count', 'retries_count',
        )
        read_only_fields = (
            'status', 'expire_on', 'started_on', 'completed_on', 'duration', 'succeed_count', 'retries_count'
        )


class TaskSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = api_models.Task
        fields = ('job', 'name', 'status', 'submitted_on', 'started_on', 'completed_on')
