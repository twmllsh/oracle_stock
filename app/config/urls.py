
from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from dashboard import views
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/kor/', permanent=True)),
    path('admin/', admin.site.urls),
    path('kor/', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    # path('core/', include('core.urls')),
    # path('usa/', include('usa.urls')),
]

# if settings.DEBUG:
if apps.is_installed("debug_toolbar"):
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]