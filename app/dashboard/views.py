from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth import login
from django.db.models import Q, Max, Min
from django.views.generic import ListView
from .forms import SignUpForm
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy , reverse
from .utils import mystock
import numpy as np
import pandas as pd
from bokeh.plotting import figure, output_file, save
from bokeh.embed import components, server_document
from pykrx import stock as pystock
import plotly.offline as pyo
import plotly.io as pio
from django.shortcuts import  get_object_or_404
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
# def dashboard_list(request):
#     items = Ticker.objects.all()[:5]
#     context ={}
#     context['items'] = items
#     return render(request, 'dashboard/index.html',context=context)


def home_view(request):
    # blog 앱의 특정 로직 (예: 최근 블로그 글 목록)
    return render(request, 'dashboard/home.html')




@method_decorator(xframe_options_exempt, name='dispatch')
class ItemListView(FormMixin, ListView):
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
            consen = self.request.GET.get('consen') == 'on'
            consen_slider_value = self.request.GET.get('consen_slider')
            turnarround =  self.request.GET.get('turnarround') == 'on'
            
            new_bra = self.request.GET.get('new_bra') == 'on'
            w3 = self.request.GET.get('w3') == 'on'
            
            sun = self.request.GET.get('sun') == 'on'
            sun_gcv = self.request.GET.get('sun_gcv') == 'on'
            sun_slider = self.request.GET.get('sun_slider')
            
            coke = self.request.GET.get('coke') == 'on'
            coke_gcv = self.request.GET.get('coke_gcv') == 'on'
            coke_slider = self.request.GET.get('coke_slider')
            
            realtime = self.request.GET.get('realtime') == 'on'
            
            # chart_d_new_phase=True
            # reasons__contains="sun"
            # filters = []
            ## 턴어라운드.. -1000? ? 
            
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
                    Q(reasons__contains="sun") ,
                    Q(chart_d_sun_width__lte=sun_slider)
                    )
            
            if sun_gcv:
                queryset = queryset.filter(
                    Q(reasons__contains="sun_gcv") ,
                    Q(chart_d_sun_width__lte=sun_slider)
                    )
                
                
            if coke:
                queryset = queryset.filter(
                    Q(reasons__contains="coke") ,
                    Q(chart_d_bb240_width__lte=coke_slider)
                    )
            if coke_gcv:
                queryset = queryset.filter(
                    Q(reasons__contains="coke_gcv") ,
                    Q(chart_d_bb240_width__lte=coke_slider)
                    )

            if realtime:
                pass
        
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



@method_decorator(xframe_options_exempt, name='dispatch')
class ApiView(View):
    def get(self, request, *args, **kwargs):
        item_code = request.GET.get('item_code')  # 쿼리 파라미터에서 'item_code' 가져오기
        try:
            stock = Stock(item_code)
            fig = stock.plot1()
            graph_html = pio.to_html(fig, full_html=False)
        
        
            data = {
                'status': 'ok',
                'message': '정상처리 되었습니다..',
                'item_code': item_code,
                '유보율': stock.유보율,
                '상장주식수': stock.유보율,
                'graph_html' : graph_html,
                
                }
    
        except:
            data = {
                'status': 'bad',
                'message': 'item_code가 제공되지 않았습니다.',
                'item_code': item_code,
            }
        return JsonResponse(data)

from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from .forms import StockFilterForm


@method_decorator(xframe_options_exempt, name='dispatch')
class StockFilterListView(FormMixin,ListView):
    model = ChartValue
    template_name = 'dashboard/index.html'  # 템플릿 경로 지정
    context_object_name = 'chartvalues'  # 템플릿에서 사용할 컨텍스트 변수명
    form_class = StockFilterForm
    # paginate_by = 20  # 페이지당 보여줄 항목 수 (선택사항)

    def get_queryset(self):
        # 기본 쿼리셋 설정
        queryset = super().get_queryset()
        
        # 폼 초기화
        self.form = StockFilterForm(self.request.GET or None)
        
        # 폼이 유효한 경우 필터링 적용
        if self.form.is_valid():
            # 컨센서스 성장 필터
            if self.form.cleaned_data.get('consen'):
                consen_slider = self.form.cleaned_data.get('consen_slider')
                queryset = queryset.filter(growth_y1__gte=consen_slider)
            
            # 턴어라운드 필터
            if self.form.cleaned_data.get('turnarround'):
                queryset = queryset.filter(growth_y1=-1000)
            
            
            # 새로운 BRA 필터
            if self.form.cleaned_data.get('new_bra'):
                queryset = queryset.filter(chart_d_new_phase=True)
            
            # W3 필터
            if self.form.cleaned_data.get('w3'):
                queryset = queryset.filter(Q(reasons__contains="w3") | Q(reasons__contains="3w"))
            
            # 선 필터
            if self.form.cleaned_data.get('sun'):
                sun_slider = self.form.cleaned_data.get('sun_slider')
                queryset = queryset.filter(chart_d_sun_width__lte=sun_slider)
            
            # 선 GCV 필터
            if self.form.cleaned_data.get('sun_gcv'):
                queryset = queryset.filter(Q(reasons__contains="sun_gcv"))
            
            # 코크 필터
            if self.form.cleaned_data.get('coke'):
                coke_slider = self.form.cleaned_data.get('coke_slider')
                queryset = queryset.filter(chart_d_bb240_width__lte=coke_slider)
            
            # 코크 GCV 필터
            if self.form.cleaned_data.get('coke_gcv'):
                queryset = queryset.filter(Q(reasons__contains="coke_gcv"))
            
            # 실시간 필터
            if self.form.cleaned_data.get('realtime'):
                # 현재 qs 에 네이버 실시간 가져온 코드만 적용. 
                pass
            
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'data': self.request.GET})
        return kwargs

    def get_context_data(self, **kwargs):
        # 기본 컨텍스트 데이터에 폼 추가
        context = super().get_context_data(**kwargs)
        context['form'] = self.form
        return context

def stock_detail_view(request, item_code):
    chartvalue = get_object_or_404(ChartValue, ticker_id=item_code)
    stock = Stock(item_code)
    fig = stock.plot1()
    plot_div = opy.plot(fig, output_type='div', include_plotlyjs=False)
    
    context = {
        'chartvalue': chartvalue,
        'plot_div': plot_div,
    }
    print(context)
    # 그래프 데이터 로직 추가
    return render(request, 'dashboard/_stock_detail.html', context)






    
def item_detail(request, item_code):
    stock = Stock(item_code)
    fig = stock.plot1()
    graph_html = pio.to_html(fig, full_html=False)
    # graph_html = pyo.plot(fig, include_plotlyjs=False, output_type='div')
    return render(request, 'dashboard/detail_graph.html', {'graph_html': graph_html})
    
