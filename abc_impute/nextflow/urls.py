from django.conf import settings
from django.urls import path

from . import views


app_name = 'api'
urlpatterns = [
    path('jobs/<pk>/callback/', views.NextflowCallback.as_view(), name='callback'),
]

if settings.DEBUG:
    urlpatterns.append(
        path('json_capture_debug/', views.json_capture, name='json_capture_debug'),
    )
