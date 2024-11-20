from django.db import models
from model_utils import FieldTracker
import pandas as pd 



# Create your models here.
class Ticker_usa(models.Model):
    symbol = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=50)
    sector = models.CharField(max_length=100)
    industry = models.CharField(max_length=100)
    create_at = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"Ticker_usa[{self.name}({self.symbol})]"

    class Meta:
        verbose_name='Ticker_usa'
        verbose_name_plural = 'Tickers_usa'
        # db_table = 'stock_dashboard_ticker'
        
class Info_usa(models.Model):
 
    ticker = models.OneToOneField(Ticker_usa, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True) #
    Index =  models.CharField(max_length=30)
    Market_Cap =  models.FloatField(null=True , blank=True)
    Income =  models.FloatField(null=True , blank=True)
    Sales =  models.FloatField(null=True , blank=True)
    Book_sh =  models.FloatField(null=True , blank=True)
    Cash_sh =  models.FloatField(null=True , blank=True)
    Dividend_Est =  models.FloatField(null=True , blank=True)
    Dividend_TTM =  models.FloatField(null=True , blank=True)
    Dividend_Ex_Date =  models.DateField(null=True) 
    Employees =  models.FloatField(null=True , blank=True)
    Sales_Surprise =  models.FloatField(null=True , blank=True)
    P_E =  models.FloatField(null=True , blank=True)
    Forward_P_E =  models.FloatField(null=True , blank=True)
    PEG =  models.FloatField(null=True , blank=True)
    P_S =  models.FloatField(null=True , blank=True)
    P_B =  models.FloatField(null=True , blank=True)
    P_C =  models.FloatField(null=True , blank=True)
    P_FCF =  models.FloatField(null=True , blank=True)
    Debt_Eq =  models.FloatField(null=True , blank=True)
    LT_Debt_Eq =  models.FloatField(null=True , blank=True)
    EPS_Surprise =  models.FloatField(null=True , blank=True)
    EPS_ttm =  models.FloatField(null=True , blank=True)
    EPS_next_Y =  models.FloatField(null=True , blank=True)
    EPS_next_Q =  models.FloatField(null=True , blank=True)
    EPS_this_Y =  models.FloatField(null=True , blank=True)
    EPS_next_5Y =  models.FloatField(null=True , blank=True)
    EPS_past_5Y =  models.FloatField(null=True , blank=True)
    Sales_past_5Y =  models.FloatField(null=True , blank=True)
    EPS_Y_Y_TTM =  models.FloatField(null=True , blank=True)
    Sales_Y_Y_TTM =  models.FloatField(null=True , blank=True)
    EPS_Q_Q =  models.FloatField(null=True , blank=True)
    Sales_Q_Q =  models.FloatField(null=True , blank=True)
    Insider_Own =  models.FloatField(null=True , blank=True)
    Insider_Trans =  models.FloatField(null=True , blank=True)
    Inst_Own =  models.FloatField(null=True , blank=True)
    Inst_Trans =  models.FloatField(null=True , blank=True)
    ROA =  models.FloatField(null=True , blank=True)
    ROE =  models.FloatField(null=True , blank=True)
    ROI =  models.FloatField(null=True , blank=True)
    Gross_Margin =  models.FloatField(null=True , blank=True)
    Oper_Margin =  models.FloatField(null=True , blank=True)
    Profit_Margin =  models.FloatField(null=True , blank=True)
    Payout =  models.FloatField(null=True , blank=True)
    Shs_Outstand =  models.FloatField(null=True , blank=True)
    Shs_Float =  models.FloatField(null=True , blank=True)
    Short_Float =  models.FloatField(null=True , blank=True)
    Short_Ratio =  models.FloatField(null=True , blank=True)
    Short_Interest =  models.FloatField(null=True , blank=True)
    Recom =  models.FloatField(null=True , blank=True)
    Perf_Week =  models.FloatField(null=True , blank=True)
    Perf_Month =  models.FloatField(null=True , blank=True)
    Perf_Quarter =  models.FloatField(null=True , blank=True)
    Perf_Half_Y =  models.FloatField(null=True , blank=True)
    Perf_Year =  models.FloatField(null=True , blank=True)
    Perf_YTD =  models.FloatField(null=True , blank=True)
    Beta =  models.FloatField(null=True , blank=True)
    Target_Price =  models.FloatField(null=True , blank=True)
   
    tracker = FieldTracker(fields=['ROE', 'EPS_next_Y', 'Cash_sh', 'Employees', 'EPS_Surprise', 'Target_Price'])

    def __str__(self):
        return f"Info_usa[{self.ticker.name} 업종 : {self.ticker.symbol} EPS_next_Y : {self.EPS_next_Y} EPS_next_5Y: {self.EPS_next_5Y}]"

    class Meta:
        verbose_name='기본정보'
        verbose_name_plural = '기본정보 목록'
        # db_table = 'stock_dashboard_info'
    

      
class Ohlcv_usa(models.Model):
    ticker = models.ForeignKey(
        Ticker_usa, on_delete=models.CASCADE
    )  # 여러 개의 Ohlcv가 한 Ticker에 연결
    Date = models.DateField()  # 날짜
    # open = models.DecimalField(max_digits=10, decimal_places=2)  # 시가
    Open = models.FloatField()  # 시가
    High = models.FloatField()   # 고가
    Low = models.FloatField()   # 저가
    Close = models.FloatField()   # 종가
    Volume = models.BigIntegerField()  # 거래량
  

    class Meta:
        unique_together = (
            "ticker",
            "Date",
        )  # 특정 Ticker의 날짜별 데이터가 중복되지 않도록
        ordering = ['Date']
        verbose_name='OHLCV_usa'
        # db_table = 'stock_dashboard_ohlcv'
        
 
    @classmethod
    def get_data(cls, ticker:Ticker_usa):
        """특정 ticker ohlcv 데이터 가져오기"""
        qs = cls.objects.filter(ticker=ticker)
        field_names = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        qs = qs.values(*field_names)
        df = pd.DataFrame(qs)
        df['Date'] = pd.to_datetime(df['Date'])
        if df.index.name != 'Date' and 'Date' in df.columns:
            df = df.set_index('Date')
        return df
    
    
    def __str__(self):
        return f"Ohlcv_usa [{self.Date} {self.ticker.name} close : {self.Close}]"
