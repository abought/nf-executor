"""
Serializers for workflow executor API

Note that there is no write serializer for tasks, because

"""
from rest_framework import serializers as drf_serializers

from . import models as api_models


class WorkflowSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = api_models.Workflow
        fields = ('id', 'name', 'description', 'version', 'definition_path')


class JobSerializer(drf_serializers.ModelSerializer):
    status = drf_serializers.CharField(source='get_status_display', read_only=True)

    def validate(self, data):
        # Workaround: Two column unique constraints are not handled properly by DRF
        # This method can be removed upon fix for this issue:
        # https://github.com/encode/django-rest-framework/issues/7173
        if 'run_id' not in data or 'workflow' not in data:
            raise drf_serializers.ValidationError({
                'error': 'Serializer did not receive required fields'
            })

        if api_models.Job.objects.filter(run_id=data['run_id'], workflow=data['workflow']).exists():
            raise drf_serializers.ValidationError({
                'error': 'run_id must be unique per workflow'
            })
        return data

    class Meta:
        model = api_models.Job
        # Signoff: Executor ID & logs_dir are used only for internal functions and not reported to consumers of the API
        fields = (
            'id', 'run_id', 'workflow', 'params', 'owner',
            'status', 'expire_on', 'started_on', 'completed_on', 'duration',
            'succeed_count', 'retries_count',
        )
        read_only_fields = (
            'id', 'status', 'expire_on', 'started_on', 'completed_on', 'duration', 'succeed_count', 'retries_count'
        )


class JobDetailSerializer(JobSerializer):
    """Detail view includes additional information which is more expensive to calculate"""
    class Meta(JobSerializer.Meta):
        fields = JobSerializer.Meta.fields + ('progress',)


class TaskSerializer(drf_serializers.ModelSerializer):
    """
    Typically used as read only serializer; tasks are populated via monitor callbacks unique to workflow engine
    """
    status = drf_serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        # All fields are marked read only
        model = api_models.Task
        fields = ('job', 'name', 'status', 'submitted_on', 'started_on', 'completed_on')
        read_only_fields = ('job', 'name', 'status', 'submitted_on', 'started_on', 'completed_on')
