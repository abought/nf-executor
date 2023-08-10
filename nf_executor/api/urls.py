from django.urls import path

from nf_executor.api.views import (
    jobs,
    tasks,
    workflows,
)

app_name = 'api'
urlpatterns = [
    path('workflows/', workflows.WorkflowListView.as_view(), name='workflows-list'),

    path('jobs/', jobs.JobListView.as_view(), name='jobs-list'),

    path('tasks/', tasks.TaskListView.as_view(), name='tasks-list'),
]
