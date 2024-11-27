from .utils.dbupdater import DBUpdater
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

executors = {
    'default': ThreadPoolExecutor(10),  # 최대 10개의 스레드
    'processpool': ProcessPoolExecutor(4)  # 최대 5개의 프로세스
}
sched : BackgroundScheduler = BackgroundScheduler(executors=executors)

print('task start!')
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

# mon, tue, wed, thu, fri, sat, sun
# 쉼표로 구분하여 여러 요일 지정: "mon,wed,fri"
# 예: day_of_week='mon-fri' → 월요일부터 금요일(평일)에만 실행

# @sched.scheduled_job('cron',  hour=22, minute=8)
# def scheduler_ticker():
#     DBUpdater.update_ticker()
class Task():
    @sched.scheduled_job('cron', day_of_week="mon-fri", hour=7, minute=30)
    def scheduler_ticker():
        DBUpdater.update_ticker()
        
        
    @sched.scheduled_job('cron', day_of_week="mon-sat", hour=15, minute=55) # 토요일 전체 데이터 새로 받기.
    def scheduler_ohlcv():
        DBUpdater.update_ohlcv()
    
    
    @sched.scheduled_job('cron', day_of_week="mon-fri", hour=20, minute=0)
    def scheduler_basic_info():
        DBUpdater.anal_all_stock()
    
    @sched.scheduled_job('cron', day_of_week="mon-fri", hour=16, minute=5)
    def scheduler_basic_info():
        DBUpdater.update_basic_info()

    @sched.scheduled_job('cron', day_of_week="mon-fri", hour=18, minute=5)
    def dcheduler_update_investor():
        DBUpdater.update_investor()

    @sched.scheduled_job('cron',  day_of_week="mon-sat", hour="8-18", minute="*/45")
    def dcheduler_update_issue():
        DBUpdater.update_issue()

    @sched.scheduled_job('cron', day_of_week="mon-sat", hour="8-23", minute="*/30")
    def dcheduler_update_stockplus_news():
        DBUpdater.update_stockplus_news()
        
    @sched.scheduled_job('cron', day_of_week=6,  hour=22, minute=0)  # 일요일 22시 
    def dcheduler_update_theme_upjong():
        DBUpdater.update_theme_upjong()

    # if not settings.DEBUG:
    sched.start()
##########################sceduler end!  ##################################
task = Task()
