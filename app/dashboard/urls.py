from django.urls import path, re_path, include
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views
from django.views.decorators.clickjacking import xframe_options_exempt


from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'ticker', TickerViewSet)  # 'yourmodel' URL에 ViewSet 연결  /api/ticker
router.register(r'info', InfoViewSet)  # 'yourmodel' URL에 ViewSet 연결  /api/ticker
router.register(r'ohlcv', OhlcvViewSet)  # 'yourmodel' URL에 ViewSet 연결  /api/ticker
router.register(r'finstats', FinstatsViewSet)  # 'yourmodel' URL에 ViewSet 연결  /api/ticker
router.register(r'investor', InvestorTradingViewSet)  # 'yourmodel' URL에 ViewSet 연결  /api/ticker
router.register(r'broker', BrokerTradingViewSet)  # 'yourmodel' URL에 ViewSet 연결  /api/ticker


app_name = "dashboard"

# /kor/ 
urlpatterns = [
    # path("", xframe_options_exempt(views.ItemListView.as_view), name='item_list'),
    path("", views.ItemListView.as_view(), name='index'),
    # path("", views.StockFilterListView.as_view(), name='index'),
    # path("sean/", views.list_form, name='list_form'),
    # path("api/<str:item_code>/", views.stock_api, name='stock_api'),
    path('api/', include(router.urls)),  # API URL에 포함  restframework
    # path("chart/<str:item_code>/", views.item_detail, name='chart'),
    path("chart/<str:item_code>/", views.stock_detail_view, name='chart'),
    
] 
