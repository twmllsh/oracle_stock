from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth import login
from django.db.models import Q, Max, Min
from django.views.generic import ListView
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy , reverse
from .utils import mystock
import numpy as np
import pandas as pd
from pykrx import stock as pystock
import plotly.offline as pyo
import plotly.io as pio
from django.shortcuts import get_object_or_404
import plotly.offline as opy
from .task import Task # 스케쥴 등록

######################  restapi#######################################

from rest_framework import viewsets
from .models import Ticker
from .serializers import *

class TickerViewSet(viewsets.ModelViewSet):
    queryset = Ticker.objects.all()
    serializer_class = TickerSerializer

    def get_queryset(self):
        queryset = Ticker.objects.all()
        ticker = self.request.query_params.get('ticker', None)
        if ticker is not None:
            queryset = queryset.filter(code=ticker)
        return queryset
    
class InfoViewSet(viewsets.ModelViewSet):
    queryset = Info.objects.all()
    serializer_class = InfoSerializer

    def get_queryset(self):
        queryset = Info.objects.all()
        ticker = self.request.query_params.get('ticker', None)
        if ticker is not None:
            queryset = queryset.filter(ticker=ticker)
        return queryset
    
class OhlcvViewSet(viewsets.ModelViewSet):
    queryset = Ohlcv.objects.all()
    serializer_class = OhlcvSerializer

    def get_queryset(self):
        queryset = Ohlcv.objects.all()
        ticker = self.request.query_params.get('ticker', None)
        if ticker is not None:
            queryset = queryset.filter(ticker=ticker)
        else:
            last_date = Ohlcv.objects.aggregate(Max('Date'))['Date__max']
            queryset = queryset.filter(Date=last_date)
        return queryset
    
class FinstatsViewSet(viewsets.ModelViewSet):
    queryset = Finstats.objects.all()
    serializer_class = FinstatsSerializer

    def get_queryset(self):
        queryset = Finstats.objects.all()
        ticker = self.request.query_params.get('ticker', None)
        if ticker is not None:
            queryset = queryset.filter(ticker=ticker)
        else:
            queryset = queryset.filter(ticker='005930')
        return queryset

class InvestorTradingViewSet(viewsets.ModelViewSet):
    queryset = InvestorTrading.objects.all()
    serializer_class = InvestorTradingSerializer

    def get_queryset(self):
        queryset = InvestorTrading.objects.all()
        last_date = InvestorTrading.objects.aggregate(Max('날짜'))['날짜__max']
        pre_month = last_date - pd.Timedelta(days=30)
        ticker = self.request.query_params.get('ticker', None)
        start = self.request.query_params.get('start', None)
        if ticker is not None:
            if start is not None:
                queryset = queryset.filter(ticker=ticker, 날짜__gte=pd.to_datetime(start))
            else:
                queryset = queryset.filter(ticker=ticker, 날짜__gte=pre_month)
        else:
            queryset = queryset.filter(날짜=last_date)
        return queryset

class BrokerTradingViewSet(viewsets.ModelViewSet):
    queryset = BrokerTrading.objects.all()
    serializer_class = BrokerTradingSerializer

    def get_queryset(self):
        queryset = BrokerTrading.objects.all()
        last_date = BrokerTrading.objects.aggregate(Max('date'))['date__max']
        pre_month = last_date - pd.Timedelta(days=30)
        ticker = self.request.query_params.get('ticker', None)
        start = self.request.query_params.get('start', None)
        if ticker is not None:
            if start is not None:
                queryset = queryset.filter(ticker=ticker, date__gte=pd.to_datetime(start))
            else:
                queryset = queryset.filter(ticker=ticker, date__gte=pre_month)
        else:
            queryset = queryset.filter(date=last_date)
        return queryset

######################  rest api  #########################


from .forms import StockFilterForm
from django.views import View
# df = pystock.get_market_ohlcv("20220720", "20220810", "005930")
 
# 3:23 부터 보기. https://www.youtube.com/watch?v=JRGktwaaYUA


from dashboard.utils.mystock import Stock
from .models import *
from .forms import *
from django.views.generic.edit import FormMixin
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from .forms import StockFilterForm


# def dashboard_list(request):
#     items = Ticker.objects.all()[:5]
#     context ={}
#     context['items'] = items
#     return render(request, 'dashboard/index.html',context=context)

@method_decorator(xframe_options_exempt, name='dispatch')
class ItemListView(LoginRequiredMixin, FormMixin, ListView):
    model = ChartValue
    template_name = 'dashboard/index.html'
    context_object_name = 'chartvalues'
    form_class = StockFilterForm
    # success_url = "/kor/"
    # paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # 보안 헤더 설정
        response['Cross-Origin-Opener-Policy'] = 'unsafe-none'
        response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
        response['X-Frame-Options'] = 'ALLOWALL'
        return response
    
    def get_queryset(self):
        self.form = self.get_form()
        queryset = super().get_queryset()
        
        if self.form.is_valid():
        # range_consen_slider_value
            # range_value = self.form.cleaned_data.get('range_value')
            # is_active = self.form.cleaned_data.get('is_active')
            consen = self.form.cleaned_data.get('consen')
            consen_slider_value = self.form.cleaned_data.get('consen_slider')
            turnarround =  self.form.cleaned_data.get('turnarround')
            
            new_bra = self.form.cleaned_data.get('new_bra')
            w3 = self.form.cleaned_data.get('w3')
            
            sun = self.form.cleaned_data.get('sun')
            sun_gcv = self.form.cleaned_data.get('sun_gcv')
            sun_slider = self.form.cleaned_data.get('sun_slider')
            
            coke = self.form.cleaned_data.get('coke')
            coke_gcv = self.form.cleaned_data.get('coke_gcv')
            coke_slider = self.form.cleaned_data.get('coke_slider')
            
            realtime = self.form.cleaned_data.get('realtime')
            
            
            if new_bra:
                queryset = queryset.filter(Q(chart_d_new_phase=True))
            if w3:
                queryset = queryset.filter(Q(reasons__contains="w3"))
                
            if consen and turnarround:
                queryset = queryset.filter(Q(growth_y1__gte=consen_slider_value) | Q(growth_y1=-1000))
            elif consen:    
                queryset = queryset.filter(Q(growth_y1__gte=consen_slider_value))
            elif turnarround:
                queryset = queryset.filter(Q(growth_y1__gte=-1000))
            else:
                pass
            
            if sun:
                queryset = queryset.filter(
                    Q(reasons__contains="sun") &
                    Q(chart_d_sun_width__lte=sun_slider) &
                    Q(chart_d_sun_width__gte=0) 
                    )
            
            if sun_gcv:
                queryset = queryset.filter(
                    Q(reasons__contains="sun_gcv") ,
                    Q(chart_d_sun_width__lte=sun_slider) &
                    Q(chart_d_sun_width__gte=0) 
                    )
                
                
            if coke:
                queryset = queryset.filter(
                    Q(reasons__contains="coke") ,
                    Q(chart_d_bb240_width__lte=coke_slider) &
                    Q(chart_d_bb240_width__gte=0)
                    )
            if coke_gcv:
                queryset = queryset.filter(
                    Q(reasons__contains="coke_gcv") ,
                    Q(chart_d_bb240_width__lte=coke_slider) &
                    Q(chart_d_bb240_width__gte=0)
                    )

            if realtime:
                ## 실제 실행해서 db에 있는 애들 검색해서 가져와서 '
                from dashboard.utils.dbupdater import DBUpdater
                result = DBUpdater.choice_stock(2,12)
                qs = Recommend.objects.filter(valid=True).values_list('code',flat=True)
                queryset = ChartValue.objects.filter(ticker_id__in=qs)
                
        return queryset

    def get_form_kwargs(self):
        # GET 파라미터를 폼 초기화에 사용
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'data': self.request.GET
        })
        return kwargs

    def get_context_data(self, **kwargs):
        # 기본 컨텍스트 데이터에 폼 추가
        context = super().get_context_data(**kwargs)
        context['form'] = self.form
        return context

    def post(self, request, *args, **kwargs):
        # POST 요청을 GET 요청으로 리다이렉트
        return self.get(request, *args, **kwargs)




def stock_detail_view(request, item_code):
    chartvalue = get_object_or_404(ChartValue, ticker_id=item_code)
    stock = Stock(item_code)
    fig = stock.plot1()
    plot_div = opy.plot(fig, output_type='div', include_plotlyjs=False)
    
    context = {
        'chartvalue': chartvalue,
        'plot_div': plot_div,
    }
    
    response = render(request, 'dashboard/_stock_detail.html', context)

    # 헤더 추가
    response['Cross-Origin-Opener-Policy'] = 'unsafe-none'
    response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
    response['X-Frame-Options'] = 'ALLOWALL'

    return response

def sample_view(request, item_code):
    context = {
        "item_code" : item_code
    }
    
    response = render(request, 'dashboard/sample.html', context)

    # 헤더 추가
    response['Cross-Origin-Opener-Policy'] = 'unsafe-none'
    response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
    response['X-Frame-Options'] = 'ALLOWALL'
    
    return response



    
# def item_detail(request, item_code):
#     stock = Stock(item_code)
#     fig = stock.plot1()
#     graph_html = pio.to_html(fig, full_html=False)
#     # graph_html = pyo.plot(fig, include_plotlyjs=False, output_type='div')
#     return render(request, 'dashboard/detail_graph.html', {'graph_html': graph_html})
    
