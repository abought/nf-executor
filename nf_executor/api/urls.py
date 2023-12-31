from django.urls import path

from nf_executor.api.views import (
    jobs,
    heartbeats,
    tasks,
    workflows,
)

app_name = 'api'
urlpatterns = [
    path('workflows/', workflows.WorkflowListView.as_view(), name='workflows-list'),
    path('workflows/<pk>/', workflows.WorkflowListView.as_view(), name='workflows-detail'),

    # NOTE: I considered nesting under workflows/, but may want to query "all jobs for a user regardless of workflow".
    path('jobs/', jobs.JobListView.as_view(), name='jobs-list'),
    path('jobs/<pk>/', jobs.JobDetailView.as_view(), name='jobs-detail'),

    path('jobs/<job_id>/tasks/', tasks.TaskListView.as_view(), name='tasks-list'),
    path('jobs/<job_id>/heartbeats/', heartbeats.HeartbeatListView.as_view(), name='heartbeats-list'),


    # path('tasks/', , name='tasks-list'),
]
