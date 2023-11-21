"""
URL configuration for abc_impute project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path(
        'api/v2/',
        include('abc_impute.api.urls', namespace='apiv2'),
    ),
    path(
        'nextflow/',
        include('abc_impute.nextflow.urls', namespace='nextflow'),
    ),
    path("api/internal/users/", include("abc_impute.users.urls", namespace="users")),
    path("api/internal/accounts/", include("allauth.urls")),

    path("api/v2/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/v2/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
