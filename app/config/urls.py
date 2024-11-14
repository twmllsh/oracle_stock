
from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from dashboard import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls')),
    path('core/', include('core.urls')),
    path('ex/', include('ex_form.urls')),
]

# if settings.DEBUG:
if apps.is_installed("debug_toolbar"):
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]