# -- Active: 1728471122893@@127.0.0.1@5432@stock
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login
from django.db.models import Q
from .forms import SignUpForm
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy , reverse
from .utils import mystock
import pandas as pd
from bokeh.plotting import figure, output_file, save
from bokeh.embed import components, server_document
from pykrx import stock as pystock

from .utils.dbupdater import DBUpdater
from apscheduler.schedulers.background import BackgroundScheduler
sched : BackgroundScheduler = BackgroundScheduler()


# pd.options.plotting.backend = "bokeh" ## 버전문제인듯. 작동안함. 


######################## scheduler start! ################################
# year(int/str) -> 실행할 연도 4자리
# month(int/str) -> 실행할 월 1-12
# day(int/str) -> 실행할 일 1-31
# week(int/str) -> 실행할 주차 수 1-53
# day_of_week(int/str) -> 실행할 요일 0-6 | mon,tue,wed,thu,fri,sat,sun
# hour(int/str) -> 실행할 시간 0-23
# minute(int/str) -> 실행할 분 0-59
# second(int/str) -> 실행할 초 0-59
# timezone(timezoneInfo|str) -> 사용할 timezone


# @sched.scheduled_job('cron',  hour=22, minute=8)
# def scheduler_ticker():
#     DBUpdater.update_ticker()

@sched.scheduled_job('cron', day_of_week="1-5", hour=7, minute=30)
def scheduler_ticker():
    DBUpdater.update_ticker()
    
@sched.scheduled_job('cron', day_of_week="1-6", hour=15, minute=55) # 토요일 전체 데이터 새로 받기.
def scheduler_ohlcv():
    DBUpdater.update_ohlcv()
    
@sched.scheduled_job('cron', day_of_week="1-5", hour=16, minute=5)
def dcheduler_basic_info():
    DBUpdater.update_basic_info()

@sched.scheduled_job('cron', day_of_week="1-5", hour=18, minute=5)
def dcheduler_update_investor():
    DBUpdater.update_investor()

@sched.scheduled_job('cron',  day_of_week="1-6", hour="8-18", minute="*/45")
def dcheduler_update_issue():
    DBUpdater.update_issue()

@sched.scheduled_job('cron', day_of_week="1-6", hour="8-23", minute="*/30")
def dcheduler_update_stockplus_news():
    DBUpdater.update_stockplus_news()
    
@sched.scheduled_job('cron', day_of_week=6,  hour=22, minute=0)  # 일요일 22시 
def dcheduler_update_theme_upjong():
    DBUpdater.update_theme_upjong()

if not settings.DEBUG:
    sched.start()
##########################sceduler end!  ##################################


class CustomLoginView(auth_views.LoginView):
    template_name='dashboard/registration/login.html'

    def get_success_url(self):
        # return reverse_lazy('dashboard:stock') ## url name
        return reverse('dashboard:dashboard') ## url name

customLoginView = CustomLoginView.as_view()

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard:login')
    else:
        form = SignUpForm()
    return render(request, 'dashboard/registration/signup.html', {'form': form})



from .forms import StockFilterForm

from ex_form.models import MyStock


# df = pystock.get_market_ohlcv("20220720", "20220810", "005930")
 
# 3:23 부터 보기. https://www.youtube.com/watch?v=JRGktwaaYUA

   

def dashboard(request):
    
    
    data = [{ "code":'005930',
            "name":'삼성전자',
            "reasons":'new_bra 3w sun',
            },
            { "code":'000660',
            "name":'sk하이닉스',
            "reasons":'new_bra 3',
            },
            { "code":'310210',
            "name":'보로노이',
            "reasons":'3w',
            },
            ]
    df = pd.DataFrame(data)

    
    condition = request.GET.getlist('condition')
    if condition:
        # df filtering
        pass
    
    context ={}
    context['items'] = df.to_dict('records')
    
    return render(request, 'dashboard/dashboard.html',context=context)

def item_detail(request, item_code):
    context = {
        'item_code': item_code
    }
    return render(request, 'dashboard/detail.html',context=context )
