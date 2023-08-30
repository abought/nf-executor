# TODO Write this!!
from django.conf import settings
from django.urls import path

import nf_executor.api.views.workflows

import nf_executor.api.views.jobs

import nf_executor.api.views.tasks
from . import views


app_name = 'api'
urlpatterns = [
    path('jobs/<pk>/callback/', views.NextflowCallback.as_view(), name='callback'),
]

if settings.DEBUG:
    urlpatterns.append(
        path('json_capture_debug/', views.json_capture, name='json_capture_debug'),
    )
