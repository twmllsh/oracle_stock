from django.urls import path, re_path
from django.urls import reverse_lazy
from . import views

app_name = "dashboard_usa"

urlpatterns = [
    path("", views.dashboard_usa, name='usa'),
    path("item/<str:item_code>/", views.item_detail, name='detail'),
   
        
]
