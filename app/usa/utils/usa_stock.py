from dashboard.utils.chart import Chart
from usa.models import *

class Stock_usa():
    def __init__(self, symbol):
        self.symbol = symbol
        ticker = Ticker_usa.objects.get(symbol=self.symbol)
        ohlcv_d = Ohlcv_usa.get_data(ticker=ticker)
        self.chart = Chart(ohlcv_d)

    


# class Anal():
#     tickers = Ticker_usa.objects.all()
#     # tickers = {ticker.symbol:ticker for ticker in tickers}
    
#     for ticker in tickers:
#         stock = Stock_usa(ticker.symbol)