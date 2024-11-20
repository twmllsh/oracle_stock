import asyncio
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from io import StringIO 
import FinanceDataReader as fdr
from usa.models import Ticker_usa, Info_usa, Ohlcv_usa
from django.db import transaction
from dashboard.utils.message import My_discord

mydiscord = My_discord()

def update_ticker_usa():
    to_create = []
    to_update = []
    qs = Ticker_usa.objects.all()
    if qs:
        exist_tickers = {ticker.symbol : ticker for ticker in qs}
    else:
        exist_tickers = []
        
    sp500 = fdr.StockListing('S&P500')
    for dic in sp500.to_dict('records'):
        if dic['Symbol'] in exist_tickers:
            ticker = exist_tickers.get(dic['Symbol'])

            
            ticker.name = dic['Name']
            ticker.sector = dic['Sector']
            ticker.industry = dic['Industry']
            to_update.append(ticker)
        else:
            new_dic = {}
            for key, value in dic.items():
                new_dic[f'{key.lower()}'] = value
            ticker = Ticker_usa(**new_dic)
            to_create.append(ticker)
                
    with transaction.atomic():
        if to_update:
            Ticker_usa.objects.bulk_update(to_update, ["name",'sector','industry'])
            print(f"updated 완료 {len(to_update)} ")
            print(to_update)

        if to_create:
            Ticker_usa.objects.bulk_create(to_create)
            print(f"created 완료 {len(to_create)} ")
            print(to_create)

    print(f"updated : {len(to_update)} created : {len(to_create)}")

    asyncio.run(mydiscord.send_message(f"update_ticker_usa finished!!"))
    return sp500


## 데이터 전처리 변환
def _conv_to_float(s):
    if isinstance(s, float):
        return s
    if s.strip() == '-':
        return None
    if '(' in s:
        s = s.split('(')[0].strip()
    if s[-1] == '%':
        s = s.replace('%', '')
    if s[-1] in list('BMK'):
        powers = {'B': 10 ** 9, 'M': 10 ** 6, 'K': 10 ** 3, '': 1}
        m = re.search("([0-9\.]+)(M|B|K|)", s)
        if m:
            val, mag = m.group(1), m.group(2)
            return float(val) * powers[mag]
    try:
        result = float(s)
    except:
        result = s
    
    return result

def get_stock_factors(sym):
    # Market Cap: 회사의 시가총액으로, 주가에 발행 주식 수를 곱한 값입니다. 회사의 규모를 나타냅니다.
    # Income: 회사의 총 수익을 나타내며, 일정 기간 동안의 총 수익에서 비용을 뺀 값입니다.
    # Sales: 회사의 총 매출을 의미하며, 제품이나 서비스 판매로 얻은 총 수익입니다.
    # Book/sh: 주당 장부가치로, 회사의 총 자산에서 총 부채를 뺀 후 발행 주식 수로 나눈 값입니다.
    # Cash/sh: 주당 현금 보유량으로, 회사의 총 현금을 발행 주식 수로 나눈 값입니다.
    # Dividend Est.: 예상 배당금으로, 주주에게 지급될 것으로 예상되는 배당금의 추정치입니다.
    # Dividend TTM: 최근 12개월 동안 지급된 배당금 총액입니다.
    # Dividend Ex-Date: 배당금 지급의 기준일로, 이 날짜 이전에 주식을 보유한 주주에게 배당금이 지급됩니다.
    # Employees: 회사의 전체 직원 수입니다.
    # Option/Short: 옵션과 공매도 비율을 나타내며, 주식의 유동성과 투자자들의 시장 전망을 반영합니다.
    # Sales Surprise: 예상 매출과 실제 매출 간의 차이를 나타냅니다.
    # P/E: 주가수익비율로, 주가를 주당 순이익(EPS)으로 나눈 값입니다. 기업의 가치를 평가하는 데 쓰입니다.
    # Forward P/E: 예상 주가수익비율로, 미래의 예상 순이익을 기준으로 한 P/E입니다.
    # PEG: 주가수익성장비율로, P/E를 예상 성장률로 나눈 값입니다. 성장성을 고려한 평가입니다.
    # P/S: 주가매출비율로, 주가를 주당 매출로 나눈 값입니다.
    # P/B: 주가장부가치비율로, 주가를 주당 장부가치로 나눈 값입니다.
    # P/C: 주가현금흐름비율로, 주가를 주당 현금 흐름으로 나눈 값입니다.
    # P/FCF: 주가자유현금흐름비율로, 주가를 주당 자유현금흐름으로 나눈 값입니다.
    # Quick Ratio: 유동비율의 변형으로, 단기 채무 상환 능력을 나타내는 지표입니다.
    # Current Ratio: 현재 비율로, 유동 자산을 유동 부채로 나눈 값입니다.
    # Debt/Eq: 부채비율로, 총 부채를 자기자본으로 나눈 값입니다.
    # LT Debt/Eq: 장기 부채비율로, 장기 부채를 자기자본으로 나눈 값입니다.
    # EPS Surprise: 예상 주당 순이익과 실제 주당 순이익 간의 차이를 나타냅니다.
    # SMA50: 50일 단순 이동 평균으로, 최근 50일 동안의 평균 주가입니다.
    # EPS (ttm): 최근 12개월 동안의 주당 순이익입니다.
    # EPS next Y: 다음 해의 주당 순이익 예상치입니다.
    # EPS next Q: 다음 분기의 주당 순이익 예상치입니다.
    # EPS this Y: 올해의 주당 순이익 예상치입니다.
    # EPS next 5Y: 향후 5년간의 주당 순이익 예상 성장률입니다.
    # EPS past 5Y: 지난 5년간의 주당 순이익 성장률입니다.
    # Sales past 5Y: 지난 5년간의 매출 성장률입니다.
    # EPS Y/Y TTM: 전년 대비 최근 12개월 동안의 주당 순이익 성장률입니다.
    # Sales Y/Y TTM: 전년 대비 최근 12개월 동안의 매출 성장률입니다.
    # EPS Q/Q: 전 분기 대비 주당 순이익 변화율입니다.
    # Sales Q/Q: 전 분기 대비 매출 변화율입니다.
    # SMA200: 200일 단순 이동 평균으로, 최근 200일 동안의 평균 주가입니다.
    # Insider Own: 내부자 소유 비율로, 회사의 주식을 보유한 임원 및 주요 주주의 비율입니다.
    # Insider Trans: 내부자 거래로, 최근 일정 기간 동안 내부자가 주식을 매도하거나 매입한 거래 내역입니다.
    # Inst Own: 기관 투자자 소유 비율로, 기관 투자자들이 보유한 주식의 비율입니다.
    # Inst Trans: 기관 투자자 거래로, 최근 일정 기간 동안 기관 투자자들이 주식을 매도하거나 매입한 거래 내역입니다.
    # ROA: 총자산이익률로, 총 자산 대비 순이익을 나타냅니다.
    # ROE: 자기자본이익률로, 자기자본 대비 순이익을 나타냅니다.
    # ROI: 투자 수익률로, 투자 대비 수익을 나타내는 비율입니다.
    # Gross Margin: 매출총이익률로, 매출에서 매출원가를 뺀 비율입니다.
    # Oper. Margin: 운영이익률로, 운영 이익을 매출로 나눈 비율입니다.
    # Profit Margin: 순이익률로, 순이익을 매출로 나눈 비율입니다.
    # Payout: 배당성향으로, 순이익 중 배당금으로 지급된 비율입니다.
    # Earnings: 회사의 총 수익이나 순이익을 의미합니다.
    # Trades: 거래량으로, 특정 기간 동안의 거래 횟수를 나타냅니다.
    # Shs Outstand: 발행 주식 수로, 시장에 유통되는 주식의 총 수입니다.
    # Shs Float: 유통 가능한 주식 수로, 일반 투자자들이 거래할 수 있는 주식의 수입니다.
    # Short Float: 공매도 비율로, 전체 유통 주식 수에 대한 공매도 주식 수의 비율입니다. 높은 비율은 투자자들이 주가 하락을 예상하고 있다는 의미일 수 있습니다.
    # Short Ratio: 공매도 비율로, 공매도 주식 수를 일일 평균 거래량으로 나눈 값입니다. 이 값이 높을수록 공매도 포지션을 청산하는 데 걸리는 시간이 길어질 수 있습니다.
    # Short Interest: 공매도 잔고로, 특정 날짜에 공매도된 주식의 총 수량입니다. 이는 투자자들이 해당 주식에 대해 얼마나 베팅하고 있는지를 나타냅니다.
    # 52W Range: 52주 범위로, 주식의 지난 52주간 최고가와 최저가를 나타냅니다.
    # 52W High: 52주 최고가로, 지난 52주 동안의 가장 높은 주가입니다.
    # 52W Low: 52주 최저가로, 지난 52주 동안의 가장 낮은 주가입니다.
    # RSI (14): 상대 강도 지수로, 14일간의 주가 상승과 하락을 비교하여 주식이 과매도 또는 과매수 상태인지 평가하는 지표입니다. 70 이상은 과매수, 30 이하는 과매도로 간주됩니다.
    # Recom: 추천 등급으로, 애널리스트들이 해당 주식에 대해 매수, 보유, 매도 중 어떤 의견을 내고 있는지를 나타냅니다.
    # Rel Volume: 상대 거래량으로, 현재 거래량을 과거 일정 기간의 평균 거래량과 비교한 값입니다. 1보다 크면 현재 거래량이 평균보다 높음을 의미합니다.
    # Avg Volume: 평균 거래량으로, 일정 기간 동안의 일일 평균 거래량입니다.
    # Volume: 특정 기간 동안의 총 거래량을 나타냅니다.
    # Perf Week: 주간 성과로, 최근 1주일 동안의 주가 변화율입니다.
    # Perf Month: 월간 성과로, 최근 1개월 동안의 주가 변화율입니다.
    # Perf Quarter: 분기 성과로, 최근 3개월 동안의 주가 변화율입니다.
    # Perf Half Y: 반기 성과로, 최근 6개월 동안의 주가 변화율입니다.
    # Perf Year: 연간 성과로, 최근 1년 동안의 주가 변화율입니다.
    # Perf YTD: 연초 대비 성과로, 올해 초부터 현재까지의 주가 변화율입니다.
    # Beta: 베타 값으로, 주식의 변동성을 시장 전체와 비교한 지표입니다. 1보다 높으면 시장보다 더 변동성이 크고, 1보다 낮으면 덜 변동성이 크다는 의미입니다.
    # ATR (14): 평균 진폭 범위로, 14일 동안의 주가 변동성을 측정하는 지표입니다. 주식의 가격 변동성이 클수록 ATR 값이 높아집니다.
    # Volatility: 변동성으로, 주가의 변동 정도를 나타내며, 일반적으로 주식의 위험도를 평가하는 데 사용됩니다.
    # Target Price: 목표 주가로, 애널리스트들이 해당 주식의 미래 가격에 대해 예상하는 가격입니다.
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(f'https://finviz.com/quote.ashx?t={sym}', headers=headers)
    print("status_code", r.status_code)
    if not r.status_code==200:
        return None
    soup = BeautifulSoup(r.text, 'html.parser')
    # tables = soup.find_all('table')
    snapshot_table2 = soup.find('table', attrs={'class': 'snapshot-table2'})
    tables = pd.read_html(StringIO(str(snapshot_table2)))
    df = tables[0]
    df.columns = ['key', 'value'] * 6

    ## 컬럼을 행으로 만들기
    df_list = [df.iloc[:, i*2: i*2+2] for i in range(6)]
    df_factor = pd.concat(df_list, ignore_index=True)
    df_factor.set_index('key', inplace=True)
    # return df_factor
    need_col = ['Index','Market Cap','Income','Sales','Book/sh','Cash/sh','Dividend Est.',
                'Dividend TTM','Dividend Ex-Date','Employees','Sales Surprise',
                'P/E','Forward P/E','PEG','P/S','P/B','P/C','P/FCF',
                'Debt/Eq','LT Debt/Eq','EPS Surprise','EPS (ttm)',
                'EPS next Y','EPS next Q','EPS this Y','EPS next Y', 'EPS next 5Y', 'EPS past 5Y',
                'Sales past 5Y', 'EPS Y/Y TTM', 'Sales Y/Y TTM', 'EPS Q/Q', 'Sales Q/Q',
                'Insider Own', 'Insider Trans', 'Inst Own', 'Inst Trans','ROA', 'ROE', 'ROI',
                'Gross Margin', 'Oper. Margin', 'Profit Margin','Payout', 'Shs Outstand', 'Shs Float',
                'Short Float', 'Short Ratio', 'Short Interest', 'Recom', 'Perf Week','Perf Month', 
                'Perf Quarter','Perf Half Y','Perf Year','Perf YTD','Beta','Target Price']
    trans_df = df_factor.transpose()
    trans_df = trans_df[need_col]
    df_factor = trans_df.transpose()
 
    df_factor.index = df_factor.index.str.replace(r'[^a-zA-Z0-9_]', '_', regex=True)
    df_factor.index = df_factor.index.str.replace(r'__', '_', regex=True)
    # 마지막 글자가 _인 경우, _를 공백으로 변경
    df_factor.index = df_factor.index.str.replace(r'_$', '', regex=True)
    # 숫자로 시작되는 인덱스 제거
    df_factor = df_factor[~df_factor.index.str.match(r'^\d')]
    
    print(len(df_factor))
    
    data = df_factor.to_dict()['value']
    data = {key:_conv_to_float(value) if key!='Index' else value  for key, value in data.items() }
    data = {key : pd.to_datetime(value) if 'Date' in key else value for key , value  in data.items()}
    return data



def update_factor_data():
    
    def bulk_job(mymodel, to_update, to_create, update_fileds=None):
        with transaction.atomic():
            if to_update:
                mymodel.objects.bulk_update(to_update, update_fileds)
                print(f"updated 완료 {len(to_update)} ")
                print(to_update)

            if to_create:
                mymodel.objects.bulk_create(to_create)
                print(f"created 완료 {len(to_create)} ")
                print(to_create)

    sp500 = update_ticker_usa()
    
    infos = Info_usa.objects.all()
    tickers = Ticker_usa.objects.all()
    exists_infos = {info.ticker.symbol: info for info in infos}
    exists_tickers = {ticker.symbol: ticker for ticker in tickers}
    to_create = []
    to_update = []
    import time
    for i, row in sp500.iterrows():
        time.sleep(1)
        symbol = row['Symbol']
        print(i, symbol)
        for _ in range(3):
            data = get_stock_factors(symbol)
            if data is not None and len(data) > 0:
                break
            print(f'{symbol} 데이터 가져오기 실패 10초 후에 재시도....... ')
            time.sleep(10)
        if i ==0:
            first_data = data
        if data is not None and len(data) > 0:
            if symbol in exists_infos:
                # continue # 임시
                print('update')
                info = exists_infos.get(symbol)
                for key, value in data.items():
                    setattr(info, key, value)
                to_update.append(info)
                
            else:
                ticker = exists_tickers.get(symbol)
                info = Info_usa(ticker=ticker, **data)
                to_create.append(info)
        else:
            print(f"{symbol} get data failed! ")
            bulk_job(Info_usa, to_update, to_create, list(first_data.keys()))
            to_create=[]
            to_update=[]
    
        if len(to_create) + len(to_update) >= 50:
            bulk_job(Info_usa, to_update, to_create, list(first_data.keys()))
            to_create=[]
            to_update=[]
        
    if len(to_create) + len(to_update) >= 0:
        bulk_job(Info_usa, to_update, to_create, list(first_data.keys()))
        to_create=[]
        to_update=[]

from django.db.models import Max
import FinanceDataReader as fdr
import pandas as pd

def update_ohlcv():
    
    def bulk_job(mymodel, to_update, to_create, update_fileds=None):
        with transaction.atomic():
            if to_update:
                mymodel.objects.bulk_update(to_update, update_fileds)
                print(f"updated 완료 {len(to_update)} ")
                print(to_update)

            if to_create:
                mymodel.objects.bulk_create(to_create)
                print(f"created 완료 {len(to_create)} ")
                print(to_create)

    last_dates = Ohlcv_usa.objects.values('ticker__symbol').annotate(last_date=Max('Date'))
    last_dates = {item['ticker__symbol']:item['last_date']for item in last_dates}
    # {'MMM': datetime.date(2022, 12, 21)}
    sp500 = update_ticker_usa()
    exists_ohlcvs = {ohlcv.ticker.symbol: ohlcv for ohlcv in Ohlcv_usa.objects.all()}
    exists_tickers = {ticker.symbol: ticker for ticker in Ticker_usa.objects.all()}
    
    to_create=[]
    to_update=[]
    update_fields = ["Open", "High", "Low", "Close", "Volume"]
    import time
    for i, row in sp500.iterrows():
        symbol = row['Symbol']
        exists_last_date = last_dates.get(symbol)
        update=False
        if exists_last_date is None: ## 데이터가 없어. 
            last_date = pd.Timestamp.now() - pd.Timedelta(days=700)
            last_date = last_date.date()
        else:
            last_date = exists_last_date     ## 데이터가 있는상태 update가 들어간다. 
            update = True
        if symbol in exists_tickers:
            ticker = exists_tickers.get(symbol)
        else:
            continue
        print(i, symbol)
        for _ in range(3):
            try:
                ohlcv = fdr.DataReader(symbol, start=last_date)
            except:
                print(f'{symbol} 데이터 가져오기 실패 50초 후에 재시도....... ')
                time.sleep(50)
        if len(ohlcv) ==0:
            time.sleep(1)
            continue
 
        for date, row1 in ohlcv.iterrows():
            date = date.date()
            if date == last_date and update:
                ohlcv_model = Ohlcv_usa.objects.filter(ticker=ticker, Date=last_date)[0]
                ohlcv_model.Open = row1['Open']
                ohlcv_model.High = row1['High']
                ohlcv_model.Low = row1['Low']
                ohlcv_model.Close = row1['Adj Close']
                ohlcv_model.Volume = row1['Volume']
                ohlcv_model.save()
                
                print(f'update................{date}')
            else:
                print("create")
                ohlcv_model = Ohlcv_usa(ticker=ticker, Date=date, 
                          Open=row1['Open'],
                          High=row1['High'],
                          Low=row1['Low'],
                          Close=row1['Adj Close'],
                          Volume=row1['Volume'],
                          )
                to_create.append(ohlcv_model)
            
        to_update=[]  
        bulk_job(Ohlcv_usa, to_update, to_create, update_fields)
        to_create=[]
        
        time.sleep(1)
        
       
    