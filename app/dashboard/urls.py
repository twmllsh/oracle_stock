from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name='dashboard'),
    path("item/<str:item_code>/", views.item_detail, name='detail'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.customLoginView, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
        
]
