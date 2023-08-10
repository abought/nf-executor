# TODO Write this!!
'jobs/<pk>/nextflow_callback'
from django.urls import path

import nf_executor.api.views.workflows

import nf_executor.api.views.jobs

import nf_executor.api.views.tasks
from . import views


app_name = 'api'
urlpatterns = [
    path('jobs/<pk>/callback/', views.NextflowCallback.as_view(), name='callback'),
]
