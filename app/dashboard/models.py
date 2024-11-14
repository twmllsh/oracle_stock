import pandas as pd
from django.db import models
from model_utils import FieldTracker
from django.db.models import F, Subquery, OuterRef, Q, Sum, Count
from django.db import transaction
from dashboard.utils.mystock import ElseInfo

class Ticker(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=20)
    구분 = models.CharField(max_length=10)
    create_at = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"Ticker[{self.name}({self.code})]"

    class Meta:
        verbose_name='Ticker'
        verbose_name_plural = 'Tickers'
        # db_table = 'stock_dashboard_ticker'
        
class Info(models.Model):
    ticker = models.OneToOneField(Ticker, on_delete=models.CASCADE)
    date = models.DateField(null=True) #
    상장주식수 = models.FloatField(null=True)
    외국인한도주식수 = models.FloatField(null=True)
    외국인보유주식수 = models.FloatField(null=True)
    외국인소진율 = models.FloatField(null=True)
    액면가 = models.FloatField(null=True)
    ROE = models.FloatField(null=True) #
    EPS = models.FloatField(null=True) #
    PER = models.FloatField(null=True) #
    PBR = models.FloatField(null=True) #
    주당배당금 = models.FloatField(null=True)
    배당수익율 = models.FloatField(null=True, blank=True)
    구분 = models.CharField(max_length=7, null=True, blank=True)
    업종 = models.CharField(max_length=20, null=True, blank=True)
    FICS = models.CharField(max_length=20, null=True, blank=True)
    시가총액 = models.FloatField(null=True)
    시가총액순위 = models.PositiveBigIntegerField(null=True)
    외국인보유비중 = models.FloatField(null=True)
    유동주식수 = models.FloatField(null=True)
    유동비율 = models.FloatField(null=True)
    보통발행주식수 = models.FloatField(null=True)
    우선발행주식수 = models.FloatField(null=True)
    PER_12M = models.FloatField(null=True)
    배당수익률 = models.FloatField(null=True)
    동일업종저per_name = models.CharField(max_length=30, blank=True)
    동일업종저per_code = models.CharField(max_length=10)
    
    tracker = FieldTracker(fields=['ROE', 'EPS', '액면가', '상장주식수', '외국인소진율', 'PER_12M', '유동주식수'])

    def __str__(self):
        return f"Info[{self.ticker.name} 업종 : {self.업종} 구분 : {self.구분} 외국인소진율: {self.외국인소진율}]"

    class Meta:
        verbose_name='기본정보'
        verbose_name_plural = '기본정보 목록'
        # db_table = 'stock_dashboard_info'
        
class Ohlcv(models.Model):
    ticker = models.ForeignKey(
        Ticker, on_delete=models.CASCADE
    )  # 여러 개의 Ohlcv가 한 Ticker에 연결
    Date = models.DateField()  # 날짜
    # open = models.DecimalField(max_digits=10, decimal_places=2)  # 시가
    Open = models.FloatField()  # 시가
    High = models.FloatField()   # 고가
    Low = models.FloatField()   # 저가
    Close = models.FloatField()   # 종가
    Volume = models.BigIntegerField()  # 거래량
    Amount = models.BigIntegerField(null=True)  # 거래량
    Change = models.FloatField(null=True)

    class Meta:
        unique_together = (
            "ticker",
            "Date",
        )  # 특정 Ticker의 날짜별 데이터가 중복되지 않도록
        ordering = ['Date']
        verbose_name='OHLCV'
        # db_table = 'stock_dashboard_ohlcv'
        
    def get_data_xx(ticker:Ticker):
        ## 240 개만 데이터 가져오기. 
        field_names = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Change']
        qs = Ohlcv.objects.filter(ticker=ticker)
        qs = qs.values(*field_names)
        df = pd.DataFrame(qs)
        df['Date'] = pd.to_datetime(df['Date'])
        if df.index.name != 'Date' and 'Date' in df.columns:
            df = df.set_index('Date')
        return df
    
    @classmethod
    def get_data(cls, ticker:Ticker):
        """특정 ticker ohlcv 데이터 가져오기"""
        qs = cls.objects.filter(ticker=ticker)
        field_names = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Change']
        qs = qs.values(*field_names)
        df = pd.DataFrame(qs)
        df['Date'] = pd.to_datetime(df['Date'])
        if df.index.name != 'Date' and 'Date' in df.columns:
            df = df.set_index('Date')
        return df
    
    
    def __str__(self):
        return f"Ohlcv [{self.Date} {self.ticker.name} close : {self.Close}]"


class Finstats(models.Model):
    FIN_TYPE = [
        ("연결연도", "연결연도"),
        ("연결분기", "연결분기"),
        ("별도연도", "별도연도"),
        ("별도분기", "별도분기"),
    ]

    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    fintype = models.CharField(max_length=4, choices=FIN_TYPE)
    year = models.IntegerField()  # 연도
    quarter = models.IntegerField()  # 분기 (분기별 데이터가 없을 경우 연도 데이터만)
    매출액 = models.FloatField(null=True, blank=True)
    영업이익 = models.FloatField(null=True, blank=True)
    영업이익발표기준 = models.FloatField(null=True, blank=True)
    당기순이익 = models.FloatField(null=True, blank=True)
    자산총계 = models.FloatField(null=True, blank=True)
    부채총계 = models.FloatField(null=True, blank=True)
    자본총계 = models.FloatField(null=True, blank=True)
    자본금 = models.FloatField(null=True, blank=True)
    부채비율 = models.FloatField(null=True, blank=True)
    유보율 = models.FloatField(null=True, blank=True)
    영업이익률 = models.FloatField(null=True, blank=True)
    순이익률 = models.FloatField(null=True, blank=True)
    ROA = models.FloatField(null=True, blank=True)
    ROE = models.FloatField(null=True, blank=True)
    EPS = models.FloatField(null=True, blank=True)
    BPS = models.FloatField(null=True, blank=True)
    DPS = models.FloatField(null=True, blank=True)
    PER = models.FloatField(null=True, blank=True)
    PBR = models.FloatField(null=True, blank=True)
    발행주식수 = models.FloatField(null=True, blank=True)
    배당수익률 = models.FloatField(null=True, blank=True) 
    지배주주순이익 = models.FloatField(null=True, blank=True)
    비지배주주순이익 = models.FloatField(null=True, blank=True)
    지배주주지분 = models.FloatField(null=True, blank=True)
    비지배주주지분 = models.FloatField(null=True, blank=True)
    지배주주순이익률 = models.FloatField(null=True, blank=True)
    tracker = FieldTracker(fields=['매출액', '영업이익', '당기순이익', '부채비율', '유보율', '발행주식수', 'EPS'])

    # class Meta:
    #     # db_table = 'stock_dashboard_finstats'
    #     pass
    
    
    # 실적주만 가져오기. 
    @classmethod
    def get_good_consen(cls, pct=0.3):
        c_year, f_yaer = ElseInfo.check_y_current
        
        data = Finstats.objects.filter(
            year=f_yaer,
            fintype='연결연도',
            quarter=0,
            영업이익__gt=0  # 2024년 영업이익은 양수
        ).annotate(
            prev_year_profit=Subquery(
                Finstats.objects.filter(
                    ticker=OuterRef('ticker'),
                    fintype='연결연도',
                    year=c_year,
                    quarter=0
                ).values('영업이익')[:1]
            )
        ).filter(
            prev_year_profit__isnull=False,
            prev_year_profit__gt=0,     # 2023년 영업이익도 양수인 경우만
            영업이익__gte=F('prev_year_profit') * (1 + pct)
        ).select_related('ticker')

        # 결과 출력
        for item in data:
            try:
                growth_rate = ((item.영업이익 / item.prev_year_profit) - 1) * 100
            
                print(f"""
                기업: {item.ticker.name}
                2024년 영업이익: {item.영업이익:,.0f}
                2023년 영업이익: {item.prev_year_profit:,.0f}
                증가율: {growth_rate:.1f}%
                """)
            except:
                print(f"""
                기업: {item.ticker.name}
                2024년 영업이익: {item.영업이익:,.0f}
                2023년 영업이익: {item.prev_year_profit:,.0f}
                """)
        return data
    
        
    def __str__(self):
        return f"Fin [{self.ticker.name}, year {self.year}({self.quarter}), 영업이익{self.영업이익}]"
    
    
    class Meta:
        unique_together = (
            "ticker",
            "fintype",
            "year",
            "quarter",
            )  # 특정 Ticker의 날짜별 데이터가 중복되지 않도록
        ordering = ['year', 'quarter']
        verbose_name='재무제표'
        verbose_name_plural = '재무제표 목록'


class InvestorTrading(models.Model):
   
    INVESTOR_TYPES=(
        ('개인', '개인'),
        ('외국인', '외국인'),
        ('기관합계', '기관합계'),
        ('금융투자', '금융투자'),
        ('보험', '보험'),
        ('은행', '은행'),
        ('투신', '투신'),
        ('사모', '사모'),
        ('연기금', '연기금'),
        ('기타법인', '기타법인'),
        ('기타금융', '기타금융'),
        ('기타외국인', '기타외국인'),
    )
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    날짜 = models.DateField()  # 거래 일자
    투자자 = models.CharField(max_length=50,choices=INVESTOR_TYPES)  # 투자자 유형 (예: 개인, 기관, 외국인)
    매도거래량 = models.BigIntegerField()
    매수거래량 = models.BigIntegerField()
    순매수거래량 = models.BigIntegerField(null=True)
    매도거래대금 = models.BigIntegerField()
    매수거래대금 = models.BigIntegerField()
    순매수거래대금 = models.BigIntegerField(null=True)
    
    class Meta:
        unique_together = ('ticker', '날짜', '투자자')
        verbose_name='투자자'
        verbose_name_plural = '투자자 목록'
        indexes = [
            models.Index(fields=['ticker', '-날짜','투자자']),
            ]
        # db_table = 'stock_dashboard_investortrading'
    
    # 최근 10(n)일 동향 가져오기
    @classmethod
    def trader_trade(cls, n=10):
        
        the_day = list(InvestorTrading.objects.values_list('날짜',flat=True)
                       .distinct().order_by('-날짜')[:n])[-1] 
        n_list = [10, 5, 3, 1]
        the_days = [list(InvestorTrading.objects.values_list('날짜',flat=True)
                       .distinct().order_by('-날짜')[:n])[-1] 
                    for n in n_list
        ]
        
        tickers = []
        
        for the_day in the_days:
            qs = InvestorTrading.objects.filter(날짜__gte=the_day)
            qs1 = qs.filter(투자자='투신')
            qs2 = qs1.filter(매도거래대금__gt=0)
            qs3 = qs2.annotate(
                total_sell = Sum('매도거래대금'),
                total_buy = Sum('매수거래대금'),).annotate(
                ratio = F('total_buy') / F('total_sell')).filter(
                ratio__gt=2).order_by('-ratio')[:20]
            tickers = [investor.ticker for investor in qs3]
            tickers += tickers
        result = list(set(tickers))
        return result
        
    ## idea 각 기관마다. 외인, 연기금,  사모, 투신 ,
    ## 10일간 각일, 각5일, 10일 전체 매수 top 10위 종목을 모아서 --> 종목 선정.
    ## 선정된 종목들 10일간 매수동향!!  > BrokerTrading 도 마찬가지. !!
    
     
    
    
    def __str__(self):
        return f"Investor[{self.ticker} - {self.날짜} - {self.투자자} - {self.순매수거래량}]"
        
        
class BrokerTrading(models.Model):
    ticker = models.ForeignKey(
        Ticker, on_delete=models.CASCADE
    )  # 여러 개의 Ohlcv가 한 Ticker에 연결
    date = models.DateField()  # 거래 일자
    broker_name = models.CharField(max_length=100, null=True)  # 거래원 이름,
    buy = models.BigIntegerField(null=True)  # 매수량
    sell = models.BigIntegerField(null=True)  # 매도량

    class Meta:
        unique_together = ('ticker', 'date', 'broker_name')
        ordering = ['-date']
        verbose_name='거래원'
        verbose_name_plural = '거래원 목록'
        # db_table = 'stock_dashboard_brokertrading'

    def __str__(self):
        return f"Broker [{self.ticker.name} - {self.date} - {self.broker_name} +{self.buy} -{self.sell}]"        
        



class ChangeLog(models.Model):
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    change_date = models.DateTimeField(auto_now_add=True)
    change_field = models.CharField(max_length=30)
    gb = models.CharField(null=True)
    old_value = models.FloatField(null=True)
    new_value = models.FloatField(null=True)

    def __str__(self):
        return f"ChangeLog [ch_date:{self.change_date} field: {self.change_field} old:{self.old_value} new{self.new_value}] "
    
    class Meta():
        unique_together = ['ticker','change_date','change_field']
        ordering = ['change_date','change_field']
        verbose_name='데이터 변경'
        verbose_name_plural = '데이터변경 목록'
        # db_table = 'stock_dashboard_changelog'




class Iss(models.Model):
    
    tickers = models.ManyToManyField(Ticker, related_name='iss_set')
    issn = models.IntegerField()
    iss_str = models.CharField(max_length=50)
    hl_str = models.CharField(max_length=200)
    regdate = models.DateField()
    ralated_codes = models.CharField(max_length=200)
    ralated_code_names = models.CharField(max_length=200)
    hl_cont_text = models.TextField()
    hl_cont_url = models.CharField(max_length=200, unique=True) # 이걸로 url이없는건 저장 불가능.
    
    def __str__(self):
        return f"Issue {self.hl_str}"
    
    class Meta:
        verbose_name='이슈'
        verbose_name_plural = '이슈 목록'
        # db_table = 'stock_dashboard_iss'


class Theme(models.Model):
    tickers = models.ManyToManyField(Ticker, through='ThemeDetail', related_name='theme_set')
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"Theme {self.name}"
    
    class Meta:
        verbose_name='테마'
        verbose_name_plural = '테마 목록'
        # db_table = 'stock_dashboard_theme'

    
class ThemeDetail(models.Model):
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE, related_name='themedtail_set')
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE)
    description = models.TextField()
    class Meta:
        unique_together = ('ticker', 'theme')
        verbose_name='테마텍스트'
        verbose_name_plural = '테마텍스트 목록'
        # db_table = 'stock_dashboard_themedetail'

    def __str__(self):
        return f"<ThemeDetail {self.ticker}>"
    
    
class Upjong(models.Model):
    tickers = models.ManyToManyField(Ticker, related_name='upjong_set')
    name = models.CharField(max_length=20)
    
    def __str__(self):
        return f"Upjong {self.name}"
    
    class Meta:
        verbose_name='업종'
        verbose_name_plural = '업종 목록'
        # db_table = 'stock_dashboard_upjong'

class News(models.Model):
    no = models.BigIntegerField()
    tickers = models.ManyToManyField(Ticker, related_name='news_set')
    title = models.CharField(max_length=200)
    createdAt =models.DateTimeField()
    writerName = models.CharField(max_length=20)
    # db_table = 'stock_dashboard_news'

    @classmethod
    def remove_duplicates(cls):
        # 'name'과 'price' 필드 기준으로 중복된 항목 찾기
        filters = ['title','createdAt']
        duplicates = (cls.objects
                    .values(*filters)
                    .annotate(count=Count('id'))
                    .filter(count__gt=1))
        if len(duplicates):
            for duplicate in duplicates:
                filters_kwargs = {item: duplicate[item] for item in filters} ## 아래 for 단수명을 따라야한다. (duplicate)
                items = cls.objects.filter(**filters_kwargs)
                items.exclude(id=items.first().id).delete()
        else:
            print('중복데이터가 없습니다. ')            
                

    def __str__(self):
        return f"<News {self.title}"


class ChartValue(models.Model):
    ticker = models.OneToOneField(Ticker, on_delete=models.CASCADE)
    cur_price = models.FloatField(null=True, blank=True)
    growth_y1 = models.FloatField(null=True, blank=True)
    growth_y2 = models.FloatField(null=True, blank=True)
    growth_q = models.FloatField(null=True, blank=True)
    chart_d_bb60_upper20 = models.FloatField(null=True, blank=True)
    chart_d_bb60_upper10 = models.FloatField(null=True, blank=True)
    chart_d_bb60_upper = models.FloatField(null=True, blank=True)
    chart_d_bb60_width = models.FloatField(null=True, blank=True)
    chart_d_bb240_upper20 = models.FloatField(null=True, blank=True)
    chart_d_bb240_upper10 = models.FloatField(null=True, blank=True)
    chart_d_bb240_upper = models.FloatField(null=True, blank=True)
    chart_d_bb240_width = models.FloatField(null=True, blank=True)
    chart_d_sun_width = models.FloatField(null=True, blank=True)
    chart_d_new_phase = models.BooleanField(null=True)
    chart_d_ab = models.BooleanField(null=True)
    chart_d_ab_v = models.BooleanField(null=True)
    chart_d_good_array = models.BooleanField(null=True)
    reasons = models.TextField(blank=True)
    reasons_30 = models.TextField(blank=True)
    chart_30_bb60_upper20 = models.FloatField(null=True, blank=True)
    chart_30_bb60_upper10 = models.FloatField(null=True, blank=True)
    chart_30_bb60_upper = models.FloatField(null=True, blank=True)
    chart_30_bb60_width = models.FloatField(null=True, blank=True)
    chart_30_bb240_upper20 = models.FloatField(null=True, blank=True)
    chart_30_bb240_upper10 =models.FloatField(null=True, blank=True)
    chart_30_bb240_upper = models.FloatField(null=True, blank=True)
    chart_30_bb240_width = models.FloatField(null=True, blank=True)
    chart_30_sun_width = models.FloatField(null=True, blank=True)
    chart_30_new_phase = models.BooleanField(null=True)
    chart_30_ab = models.BooleanField(null=True)
    chart_30_ab_v = models.BooleanField(null=True)
    chart_30_good_array = models.BooleanField(null=True)
    chart_5_bb60_upper20 = models.FloatField(null=True, blank=True)
    chart_5_bb60_upper10 = models.FloatField(null=True, blank=True)
    chart_5_bb60_upper = models.FloatField(null=True, blank=True)
    chart_5_bb60_width = models.FloatField(null=True, blank=True)
    chart_5_bb240_upper20 = models.FloatField(null=True, blank=True)
    chart_5_bb240_upper10 = models.FloatField(null=True, blank=True)
    chart_5_bb240_upper = models.FloatField(null=True, blank=True)
    chart_5_bb240_width = models.FloatField(null=True, blank=True)
    chart_5_sun_width = models.FloatField(null=True, blank=True)
    chart_5_new_phase = models.BooleanField(null=True)
    chart_5_ab = models.BooleanField(null=True)
    chart_5_ab_v = models.BooleanField(null=True)
    chart_5_good_array = models.BooleanField(null=True)
        
    
    def __str__(self):
        return f"{self.ticker.name} {self.reasons[:10]}"