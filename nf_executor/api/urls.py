from django.urls import path
from . import views


def test(request):
    from django.http import HttpResponse
    return HttpResponse('api')


app_name = 'api'
urlpatterns = [
    path('', test, name='root'),
    path('workflows/', views.WorkflowListView.as_view(), name='workflows-list'),
    path('jobs/', views.JobListView.as_view(), name='jobs-list'),
    path('tasks/', views.TaskListView.as_view(), name='tasks-list'),
]
