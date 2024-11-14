import numpy as np
import pandas as pd
import requests
import FinanceDataReader as fdr
from dashboard.utils import chart
from dashboard.utils.sean_func import Sean_func
from django.db.models import F, Subquery, OuterRef, Q, Sum, Count
from bokeh.models import ColumnDataSource, Range1d
from bokeh.models import RangeTool,HoverTool,Span,DataRange1d,CustomJS
from bokeh.plotting import figure, show
from bokeh.models.formatters import NumeralTickFormatter
from bokeh.layouts import gridplot, column, row
from bokeh.models import FactorRange, LabelSet
from plotly.subplots import make_subplots
import plotly.graph_objects as go

class GetData:

    def _get_ohlcv_from_daum(code, data_type="30분봉", limit=450):
        """
        Big Chart에서 받기.
        """
        acode = "A" + code
        # data_type= '일봉'
        limit = 480
        option_dic = {
            "월봉": "months",
            "주봉": "weeks",
            "일봉": "days",
            "60분봉": "60/minutes",
            "30분봉": "30/minutes",
            "15분봉": "15/minutes",
            "5분봉": "5/minutes",
        }

        str_option = option_dic[data_type]
        url = f"http://finance.daum.net/api/charts/{acode}/{str_option}"
        params = {"limit": f"{limit}", "adjusted": "true"}
        headers = {
            "referer": "https://finance.daum.net/chart/",
            "user-agent": "Mozilla/5.0",
        }

        response = requests.get(url=url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
        else:
            return pd.DataFrame()

        data = data["data"]
        df = pd.DataFrame(data)
        chage_col = {
            "candleTime": "Date",
            "tradePrice": "Close",
            "openingPrice": "Open",
            "highPrice": "High",
            "lowPrice": "Low",
            "candleAccTradePrice": "TradePrice",
            "candleAccTradeVolume": "Volume",
        }
        columns = ["Date", "Open", "High", "Low", "Close", "Volume", "TradePrice"]
        df["candleTime"] = pd.to_datetime(df["candleTime"])
        df.rename(columns=chage_col, inplace=True)
        df = df[columns].set_index("Date")
        return df

    def _get_ohlcv_from_fdr(code):
        limit = 450
        end = pd.Timestamp.now().date()
        start = end - pd.Timedelta(days=limit)
        df = fdr.DataReader(code, start=start, end=end)
        return df


class ElseInfo:
    _, check_y_current, check_y_future = (
        Sean_func._실적기준구하기()
    )  # 0-1 0대비 1성장율..
    _, check_q_current, check_q_future = Sean_func._실적기준구하기(
        "q"
    )  ## 0-2 yoy 1-2 qoq

    ohlcv_end_date = pd.Timestamp.now().date()
    ohlcv_start_date = ohlcv_end_date - pd.Timedelta(days=365 * 2)


class Stock:

    def __init__(self, code, start_date=None, end_date=None, anal=False):
        self.c_year, self.f_year = ElseInfo.check_y_current ## 현재year 미래yaer 
        self.quarters = ElseInfo.check_q_current
        self.code = code
        from dashboard.models import Ticker, Info, Finstats
        self.ticker = Ticker.objects.get(code=self.code)
        self.info: Info = self.ticker.info
        self.액면가 = self.info.액면가
        self.상장주식수 = self.info.상장주식수 if self.info.상장주식수 else self.info.보통발행주식수
        self.유동비율 = self.info.유동비율
        self.유동주식수 = int(
            self.상장주식수 * self.유동비율 / 100 if self.유동비율 else self.상장주식수
        ) if self.유동비율 else self.상장주식수
        self.외국인소진율 = self.info.외국인소진율
        from dashboard.models import Ohlcv
        self.ohlcv_day = Ohlcv.get_data(self.ticker)
        self.chart_d: chart.Chart = chart.Chart(
            self.ohlcv_day,
            mas=[3, 5, 10, 20, 60, 120, 240],
            상장주식수=self.상장주식수,
            유동주식수=self.유동주식수,
        )
        if anal:
            # 5 30 받아서 chart 생성 . 후 필요한 값만 가져오기.
            for _ in range(5):
                try:
                    self.ohlcv_30 = GetData._get_ohlcv_from_daum(
                        code=self.code, data_type="30분봉"
                    )
                    self.ohlcv_5 = GetData._get_ohlcv_from_daum(
                        code=self.code, data_type="5분봉"
                    )
                    break
                except:
                    print('30분봉데이터 다운실패 5초 기다림.')
                    import time
                    time.sleep(5)

            if isinstance(self.ohlcv_30, pd.DataFrame):
                self.chart_30 = chart.Chart(
                    self.ohlcv_30,
                    mas=[10, 20, 60, 120, 240],
                    상장주식수=self.상장주식수,
                    유동주식수=self.유동주식수,
                )

            if isinstance(self.ohlcv_5, pd.DataFrame):
                self.chart_5 = chart.Chart(
                    self.ohlcv_5,
                    mas=[10, 20, 60, 120, 240],
                    상장주식수=self.상장주식수,
                    유동주식수=self.유동주식수,
                )
                  
            if not hasattr(self, 'chart_30'):
                print('30분봉데이터 생성 실패~')
                anal=False
            if not hasattr(self, 'chart_5'):
                print('5분봉데이터 생성 실패~')
                anal=False
                    
    
        
        # investor
        self.investor_part = self.get_investor_part()

        # fin status
        self.fin_df, self.fin_df_q = self.get_fin_status()
        
       
    def get_fin_status(self):
        
        def _get_성장율(data, gap=1):
            ''' 적자 = -10000, 턴어라운드 = -1000'''
            new_data = []
            for i in range(len(data)):
                if i > 0:
                    cur = data.iloc[i]
                    if cur is None:
                        value = None
                        new_data.append(value)
                        continue
                    try:
                        pre = data.iloc[i-gap]
                    except:
                        value = None
                        new_data.append(value)
                        continue
                    if cur < 0 :
                        value = -10000 # 적자
                        new_data.append(value)
                        continue
                    else:
                        if pre <= 0:
                            value = -1000 # 턴어라운드
                            new_data.append(value)
                            continue
                        else:
                            # 성장율 표기 
                            value = round(((cur - pre) / pre) * 100 , 1)
                            new_data.append(value)
                            continue
                else:
                    cur= data.iloc[i]
                    if cur is not None:
                        if cur < 0 :
                            value = -10000
                        else:
                            value = None
                    else:
                        value= None
                    new_data.append(value)
            return new_data   
        
        
        ## 연간 매출액, 영업이익, 당기순이익 데이터 가져오기. ==> models에 함수로 이동하기
        fin: Finstats = self.ticker.finstats_set
        fin_y_qs = fin.filter(fintype="연결연도", quarter=0).values(
            "year", "매출액", "영업이익", "당기순이익"
        )
        fin_qs_q = (
            fin.exclude(quarter=0)
            .filter(fintype="연결분기")
            .values("year", "quarter", "매출액", "영업이익", "당기순이익")
        )

        self.fin_df = pd.DataFrame(fin_y_qs) if fin_y_qs else None
        self.fin_df_q = pd.DataFrame(fin_qs_q) if fin_qs_q else None
        
        if self.fin_df is not None and (isinstance(self.fin_df, pd.DataFrame) and not self.fin_df.empty):
            # self.fin_df = self.fin_df.set_index("year")
            self.fin_df['growth'] = _get_성장율(self.fin_df['영업이익'])
        
        if self.fin_df_q is not None and (isinstance(self.fin_df_q, pd.DataFrame) and not self.fin_df_q.empty):
            self.fin_df_q["index"] = (
                self.fin_df_q["year"].astype(str)
                + "/"
                + self.fin_df_q["quarter"].astype(str).str.zfill(2)
            )
            self.fin_df_q = self.fin_df_q.set_index("index")
            self.fin_df_q['yoy'] = _get_성장율(self.fin_df_q['영업이익'], gap=4)
            self.fin_df_q['qoq'] = _get_성장율(self.fin_df_q['영업이익'])
            
        return self.fin_df, self.fin_df_q
          
    # 날짜범위와 계산값 반환.  to_list or  dict
    def get_investor_part(self):
        from dashboard.models import InvestorTrading
        ls = []
        low_dates = self._get_low_dates()
        if not low_dates:
            return None
        qs = InvestorTrading.objects.filter(ticker=self.ticker).filter(
            날짜__gte=low_dates[0]
        )
        
        investor_df = pd.DataFrame(
            qs.values(
                "날짜",
                "투자자",
                "매도거래량",
                "매수거래량",
                "매도거래대금",
                "매수거래대금",
            )
        )
        if len(investor_df):
            investor_df["순매수거래대금"] = (
                investor_df["매수거래대금"] - investor_df["매도거래대금"]
            )
            investor_df["순매수거래량"] = (
                investor_df["매수거래량"] - investor_df["매도거래량"]
            )
            # 데이터 분리하고.
            investor_df["날짜"] = pd.to_datetime(investor_df["날짜"])
            for i in range(len(low_dates)):
                temp_dic = {}
                if len(low_dates) - 1 == i:
                    start_date = low_dates[i]
                    temp_df = investor_df.loc[(investor_df["날짜"] >= start_date)]
                else:
                    start_date, end_date = low_dates[i], low_dates[i + 1]
                    temp_df = investor_df.loc[
                        (investor_df["날짜"] >= start_date)
                        & (investor_df["날짜"] < end_date)
                    ]

                if len(temp_df):
                    temp_dic = self._cal_investor(temp_df)
                    ls.append(temp_dic)
            try:
                ## ma3값 넣기         
                for item in ls:
                    start = item['start']
                    ## 투자자정보는 있어도 차트데이터가 없을때 그냥 ma3값 과 group값없이 반환.  ************************
                    item['ma3'] = self.chart_d.ma3.data.loc[start]  
                
                ## group 넣기. 
                n = 7  ## 이격도가 7 이상벌어진것을 그룹으로 간주. 
                result_df = pd.DataFrame(ls)
                group_num = 1
                for i in range(len(result_df)-1):
                    a = result_df.iloc[i]['ma3']
                    b =  result_df.iloc[i+1]['ma3']
                    first_value = a
                    pct_first = round((abs(first_value-b) / first_value) * 100,2)  # 그룹 초기값과의 이격도.
                    pct = round((abs(a-b) / a) * 100,2) # 현재값과 다음값과의 이격도.
                    date = result_df['start'].iloc[i]
                    
                    if i ==0:
                        result_df.loc[i,'group'] = group_num
                        continue
                        
                    if (pct > n) & (pct_first > n):
                        result_df.loc[i,'group'] = group_num
                        front_value = b
                        group_num  +=1
                    else:
                        result_df.loc[i,'group'] = group_num
                result_df.loc[i+1,'group'] = group_num
                result_df['group'] = result_df['group'].fillna(1).astype(int)
            except Exception as e:
                print(e, 'group 만들기 오류')
                result_df = pd.DataFrame(ls)
                return result_df
        else:
            return None
        return result_df

    def _get_low_dates(self):
        low3 = self.chart_d.ma3.df_last_low_points if hasattr(self.chart_d, 'ma3') else None
        low3_all = self.chart_d.ma3.df_all_low_points if hasattr(self.chart_d, 'ma3') else None
        low20 = self.chart_d.ma20.df_last_low_points if hasattr(self.chart_d, 'ma20') else None
        start_date = None
        if low20 is None or (isinstance(low20, pd.DataFrame) and low20.empty):
        # if not low20:
            # if not low3:
            if low3 is None or (isinstance(low3, pd.DataFrame) and low3.empty):
                print("not exist ma3 low points")
            else:
                start_date = low3.index[0]
                print("not exist ma20 low points")
            
        else:
            # if len(low20) == 1:
            if len(low20) == 1:
                date20 = low20.index[-1]
            else:
                date20 = low20.index[-2]
            start_date = low3_all[low3_all.index < date20].index[-1]
        
        # low_dates = list(low3_all.loc[low3_all.index >= start_date].index) + [self.chart_d.df.index[-1]]
        try:
            low_dates = list(low3_all.loc[low3_all.index >= start_date].index)
        except:
            low_dates = None
        return low_dates

    def _cal_investor(self, df):
        """
        구간데이터를 주면 정리해주는 함수. return dict
        """
        temp_dic = {}
        if all(
            [
                col in df.columns
                for col in [
                    "날짜",
                    "투자자",
                    "매도거래대금",
                    "매수거래대금",
                    "순매수거래대금",
                ]
            ]
        ):
            temp_df = df.copy()

            ##########################################
            temp_dic["start"], temp_dic["end"] = (
                temp_df["날짜"].iloc[0],
                temp_df["날짜"].iloc[-1],
            )

            ########################################
            grouped_temp_df = temp_df.groupby("투자자")[
                ["매도거래대금", "매수거래대금", "순매수거래대금"]
            ].sum()
            grouped_temp_df = grouped_temp_df.loc[
                ~(
                    (grouped_temp_df["매수거래대금"] == 0)
                    & (grouped_temp_df["매도거래대금"] == 0)
                )
            ]  ## 매수매도 모두 0인값 제거.
            grouped_temp_df["매집비"] = round(
                (grouped_temp_df["매수거래대금"] / grouped_temp_df["매도거래대금"])
                * 100,
                1,
            )
            # inf 값을 10000으로 대체
            # df.replace([np.inf, -np.inf], 10000, inplace=True)
            grouped_temp_df.replace([np.inf, -np.inf], 10000, inplace=True)
            grouped_temp_df["full"] = (
                (grouped_temp_df["순매수거래대금"] == grouped_temp_df["매수거래대금"])
                & (grouped_temp_df["순매수거래대금"] != 0)
                & (grouped_temp_df["매수거래대금"] >= 100000000)
            )  # 1억이상.

            # 주도기관
            적용기관리스트 = list(
                grouped_temp_df.sort_values("매집비", ascending=False).index
            )
            주도기관 = ",".join(적용기관리스트[:2])
            적용기관 = ",".join(적용기관리스트)
            temp_dic["적용기관"] = 적용기관
            temp_dic["주도기관"] = 주도기관

            ##  전체풀매수 여부..
            df_sum = grouped_temp_df.sum()
            매집비 = round(
                df_sum.loc["매수거래대금"] / df_sum.loc["매도거래대금"] * 100, 1
            )
            순매수 = df_sum.loc["순매수거래대금"]
            순매수금액_억 = round(순매수 / 100000000, 1)
            temp_dic["순매수대금"] = 순매수
            temp_dic["순매수금_억"] = 순매수금액_억
            temp_dic["매집비"] = 매집비

            ## 부분 full_buy 여부 ##############################################################
            temp_df["full_b"] = (
                (temp_df["순매수거래대금"] == temp_df["매수거래대금"])
                & (temp_df["매수거래대금"] != 0)
                & (temp_df["매수거래대금"] >= 50000000)
            )
            full_b = temp_df.loc[temp_df["full_b"]]
            if len(full_b):
                # result_b = full_b.groupby('투자자').sum()[['순매수거래량','순매수거래대금','full_b']].sort_values(['순매수거래대금','full_b'],ascending=[False,False])
                result_b = (
                    full_b.groupby("투자자")[
                        ["순매수거래량", "순매수거래대금", "full_b"]
                    ]
                    .sum()
                    .sort_values(["순매수거래대금", "full_b"], ascending=[False, False])
                )
                부분풀매수기관 = ",".join(result_b.index)
                부분풀매수금액 = result_b["순매수거래대금"].sum()
                부분풀매수일 = result_b["full_b"].sum()
                temp_dic["부분풀매수기관"] = 부분풀매수기관
                temp_dic["부분풀매수금액"] = 부분풀매수금액
                temp_dic["부분풀매수일"] = 부분풀매수일
            else:
                temp_dic["부분풀매수기관"] = ""
                temp_dic["부분풀매수금액"] = 0
                temp_dic["부분풀매수일"] = 0

            ## 부분 full_sell 여부 ##############################################################
            temp_df["full_s"] = (
                abs(temp_df["순매수거래대금"]) == temp_df["매도거래대금"]
            ) & (temp_df["매도거래대금"] != 0)
            full_s = temp_df.loc[temp_df["full_s"]]
            if len(full_s):
                # result_s = full_s.groupby('투자자').sum()[['순매수거래량','순매수거래대금','full_s']].sort_values(['순매수거래대금','full_s'],ascending=[True,False])
                result_s = (
                    full_s.groupby("투자자")[
                        ["순매수거래량", "순매수거래대금", "full_s"]
                    ]
                    .sum()
                    .sort_values(["순매수거래대금", "full_s"], ascending=[True, False])
                )
                부분풀매도기관 = ",".join(result_s.index)
                부분풀매도금액 = result_s["순매수거래대금"].sum()
                부분풀매도일 = result_s["full_s"].sum()
                temp_dic["부분풀매도기관"] = 부분풀매도기관
                temp_dic["부분풀매도금액"] = 부분풀매도금액
                temp_dic["부분풀매도일"] = 부분풀매도일
            else:
                temp_dic["부분풀매도기관"] = ""
                temp_dic["부분풀매도금액"] = 0
                temp_dic["부분풀매도일"] = 0

            ## 전체 full 여부
            if len(grouped_temp_df.loc[grouped_temp_df["full"]]):
                풀매수기관 = list(grouped_temp_df.loc[grouped_temp_df["full"]].index)
                풀매수금액 = grouped_temp_df.loc[grouped_temp_df["full"]][
                    "순매수거래대금"
                ].sum()
                풀매수여부 = True if len(풀매수기관) else False
                temp_dic["풀매수여부"] = 풀매수여부
                temp_dic["풀매수기관"] = 풀매수기관
                temp_dic["풀매수금액"] = 풀매수금액
            else:
                temp_dic["풀매수여부"] = False
                temp_dic["풀매수기관"] = ""
                temp_dic["풀매수금액"] = 0
                ## 추후 추가할수 있는 부분.
                # temp_dic["start_ma5_value"] = start_ma5_value
                # temp_dic["저점대비현재가상승률"] = 저점대비현재가상승률

            return temp_dic

    ################  기술적 분석  ######################3
    
        
    def is_good_consen(self, pct=0.3):
        ''' 현재 년도대비 다음년도 성장율 (연결연도 영업이익 기준 ) pct '''
        from dashboard.models import Finstats
        result = self.ticker.finstats_set.filter(
            year=self.f_year,
            fintype='연결연도',
            quarter=0,
            영업이익__gt=0,  # 2024년 영업이익은 양수
        ).annotate(
            prev_year_profit=Subquery(
                Finstats.objects.filter(
                ticker=OuterRef('ticker'),
                fintype='연결연도',
                year=self.c_year,
                quarter=0
            ).values('영업이익')[:1]
        )
        ).filter(
                    prev_year_profit__isnull=False,
                    prev_year_profit__gt=0,     # 2023년 영업이익도 양수인 경우만
                    영업이익__gte=F('prev_year_profit') * (1 + pct)
        )
        if result:
            return True
        else:
            return False
        
        
    def is_good_buy(self):
        ''' 매집비를 어떻게 분석해야하나....?  '''
        # self.investor_part 로 분석. 
        # if self.investor_part is not None and isinstance(self.investor_part, pd.DataFrame) and not self.investor_part.empty:
        pass
        
    
    def is_3w(self):
        ''' is_3wa 인경우 5분봉으로 240선으로 판단하기.  '''
        pass
    
    def is_20w_3w(self):
        ''' 20은 확실한 v 이고 is_3w 이고 3ma값이 20선 위에 있는것.  '''
        
        
    ''' 나머진 그냥 coke 안에서 20 w , '''

    ' value day 30 에서 코크. indicate 값 참조.'
    
    
    def plot(self, option="day"):
        if option == "day":
            chart = getattr(self, "chart_d")
            arr_ma = np.array([3, 20, 60, 120, 240])
        elif '30' in option :
            if not hasattr(self, 'chart_30'):
                self.chart_30 = GetData._get_ohlcv_from_daum(
                code=self.code, data_type="30분봉"
            ) 
            chart = getattr(self, 'chart_30')
            arr_ma = np.array([10, 20, 60, 120, 240])
        elif '5' in option and hasattr(self, 'chart_5'):
            if not hasattr(self, 'chart_5'):
                self.chart_5 = GetData._get_ohlcv_from_daum(
                code=self.code, data_type="5분봉"
            ) 
            chart = getattr(self, 'chart_5')
            arr_ma = np.array([10, 20, 60, 120, 240])
        else:
            return None
        
        df: pd.DataFrame = chart.df.copy()
        # df.columns = [col.lower() for col in df.columns] ## ?왜 바꾼거지.?

        ## ma 데이터 생성 ##################################################
        color = ["black", "red", "blue", "green", "gray"]
        width = [1, 2, 3, 3, 3]
        alpha = [0.7, 0.7, 0.6, 0.6, 0.6 ]

        mas = arr_ma[arr_ma < len(df)]
        colors = color[:len(mas)]
        widths = width[:len(mas)]
        alphas = alpha[:len(mas)]

        for ma in mas:
            df[f"ma{ma}"] = getattr(chart, f"ma{ma}").data

        if hasattr(chart.bb240, "upper"):
            df["upper"] = chart.bb240.upper
            df["lower"] = chart.bb240.lower
            df["bb240_width"] = chart.bb240.two_line.width
                    
        if hasattr(chart.bb60, "upper"):
            df["upper60"] = chart.bb60.upper
            df["lower60"] = chart.bb60.lower
            df["bb60_width"] = chart.bb60.two_line.width
            
        if hasattr(chart.sun, "line_max"):
            df["sun_max"] = chart.sun.line_max.data
            df["sun_min"] = chart.sun.line_min.data
            df["sun_width"] = chart.sun.two_line.width

        df["candle_color"] = [
            "#f4292f" if row["Open"] <= row["Close"] else "#2a79e2"
            for _, row in df.iterrows()
        ]

        ## vol20ma
        if hasattr(chart.vol, "ma_vol"):
            df["vol20ma"] = chart.vol.ma_vol

        유동주식수 = self.유동주식수
        상장주식수 = self.상장주식수

        ## 거래량 color 지정 임시!
        ac_cond = df["Volume"] > df["Volume"].shift(1) * 2
        df["vol_color"] = ["#f4292f" if bl else "#808080" for bl in ac_cond]

        low_cond = df["Volume"] < df["vol20ma"]  # 평균보다 작은조건
        df["vol_color"] = [
            "blue" if bl else value for value, bl in zip(df["vol_color"], low_cond)
        ]

        if 유동주식수:
            cond_유통주식수 = df["Volume"] >= 유동주식수
            if sum(cond_유통주식수):
                df["vol_color"] = [
                    "#ffff00" if bl else value
                    for value, bl in zip(df["vol_color"], cond_유통주식수)
                ]

        if 상장주식수:
            cond_상장주식수 = df["Volume"] >= 상장주식수
            if sum(cond_상장주식수):
                df["vol_color"] = [
                    "#800080" if bl else value
                    for value, bl in zip(df["vol_color"], cond_상장주식수)
                ]

        df = df.reset_index()
        # df["Date"] = pd.to_datetime(df["date"])
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        # df = df.set_index('date_str')
        source = ColumnDataSource(df)
        
        
        # if self.investor_part:
        if self.investor_part is not None and isinstance(self.investor_part, pd.DataFrame) and not self.investor_part.empty:
            invest_df = pd.DataFrame(self.investor_part)
            invest_df['start'] = invest_df['start'].dt.strftime('%Y-%m-%d')
            invest_df['end'] = invest_df['end'].dt.strftime('%Y-%m-%d')
            invest_df['text'] = '주도기관: ' + invest_df['주도기관'] + '\n' + \
            '순매수금(억): ' + invest_df['순매수금_억'].map(lambda x: f"{x:.1f}") + '\n' +  \
            '매집비: ' + invest_df['매집비'].map(lambda x: f"{x:.1f}%") + '\n' +  \
            '풀매수기관: ' + invest_df['풀매수기관'].map(lambda x: ','.join(x) if not type(float) else '')
            # '풀매수기관: ' + invest_df['풀매수기관'] + '\n' 
            try:
                self.investor_part['group_color'] = np.where(self.investor_part['group'] % 2 == 0, 'blue', 'orange')
            except:
                self.investor_part['group_color'] = 'blue'
            source_investor = ColumnDataSource(invest_df)
        
        
        ## p1 그리기 ################################################################
        TOOLS = "pan, zoom_in, zoom_out,wheel_zoom,box_zoom,reset,save"
        title = f"{self.ticker.name}({self.ticker.code})"  ## 타이틀 지정해야함. ....

        plot_option = dict(
            width=800,
            height=300,
            background_fill_color="#ffffff",
            x_range=FactorRange(*df['Date']),
        )

        p1 = figure(
            tools=TOOLS,
            **plot_option,
            # toolbar_location=None,
            title=title,
            )

        ## sun 
        p1.varea(
            x='Date',
            y1='sun_max',
            y2='sun_min',
            color="#bfd8f6",
            alpha=0.5,
            source=source,
            # legend_label="mesh",
        )

        ## 캔들차트 그리기
        p1.segment(
            "Date",
            "High",
            "Date",
            "Low",
            color="candle_color",
            source=source,
        )
        p1.vbar(
            "Date",
            0.6,
            "Open",
            "Close",
            color="candle_color",
            line_width=0,
            source=source,
        )

        multi_line = [getattr(chart, f"ma{ma}").data.to_list() for ma in mas]
        xs = [df.index.to_list()] * len(multi_line)

        p1.multi_line(xs=xs, ys=multi_line, color=colors, alpha=alphas, line_width=widths)

        for item in ['upper', 'lower']:
            for bb in ['bb240', 'bb60']:
                bb_obj = getattr(chart, bb)
                if hasattr(bb_obj, item):
                    colname = f"{item}60" if bb=="bb60" else item
                    color = "#e7effc" if bb=="bb60" else "#f6b2b1"
                    
                    p1.line(
                    x="Date",
                    y=f"{colname}",
                    color=color,
                    alpha=0.8,
                    line_width=2,
                    source=source,
                    )
                    
        ## label 넣기 .. 라벨넣지 말고 표로 넣자 그냥.  점만 그리기. 
        # if len(self.investor_part):
        if self.investor_part is not None and isinstance(self.investor_part, pd.DataFrame) and not self.investor_part.empty:
            if 'group' in df.columns and 'ma3' in df.columns:
                # labels = LabelSet(x='start', y='ma3', text='text', source=source_investor,
                #                   background_fill_alpha=0.3,  # 배경 투명도 설정
                #                   background_fill_color='gray',
                #                   text_font_size="10pt",  # 텍스트 크기 지정
                #                   text_color="navy", 
                #                   text_align="left", 
                #                   x_offset=-30, y_offset=-30) ## 덱스트박스 위치맞추기기 어려움. 
                # p1.add_layout(labels)
            # 그룹별로 점 추가
                p1.scatter('start', 'ma3', fill_color='group_color', size=8, alpha=0.6, source=source_investor )
        
                    
        ## p2 거래량차트 그리기 ################################################33
        plot_option["height"] = 120
        p2 = figure(
            **plot_option,
            toolbar_location=None,
        )  # x_range를 공유해서 차트가 일치하게 만듦

        p2.vbar(
            x="Date",
            top="Volume",
            width=0.7,
            fill_color="vol_color",
            line_width=0,
            source=source,
        )
        ## 평균거래량
        p2.line(
            x="Date",
            y="vol20ma",
            line_width=1,
            line_color="black",
            source=source,
        )

        # ## 주석 (유통주식수, 상장주식수) Line
        if 유동주식수:
            p2_유통주식수 = Span(
                location=유동주식수,
                dimension="width",
                line_color="#9932cc",
                line_width=1,
            )
            p2.add_layout(p2_유통주식수)
        if 상장주식수:
            p2_상장주식수 = Span(
                location=상장주식수,
                dimension="width",
                line_color="#8b008b",
                line_width=1,
            )
            p2.add_layout(p2_상장주식수)        
        
        # range bar 그리기 ########################################################
        plot_option["height"] = 60
        range_bar = figure(
            **plot_option,
            # background_fill_color="#efefef",
            toolbar_location=None,
            y_axis_type=None,
        )

        range_tool = RangeTool(x_range=p1.x_range, start_gesture="pan")
        range_tool.overlay.fill_color = "navy"
        range_tool.overlay.fill_alpha = 0.2

        range_bar.line("Date", "Close", source=source)
        range_bar.ygrid.grid_line_color = None
        range_bar.add_tools(range_tool)        
        
        ## 그외 레이아웃 설정 및 호버 설정 #################################################
        p1.xaxis.major_label_orientation = 0.8  # radians
        p1.x_range.range_padding = 0.05
        # p1.xaxis.ticker = list(range(df.index[0], df.index[-1], 10))
        p1.xaxis.axis_label = "Date"
        p1.yaxis.axis_label = "Price"

        # 그리드 설정
        p1.xgrid.grid_line_color = None
        p1.ygrid.grid_line_alpha = 0.5

        # 축라벨 포멧팅
        p1.yaxis.formatter = NumeralTickFormatter(format="0,0")

        # p2.vbar(x=df.index, top=df.volume,  fill_color="#B3DE69", )
        # 30칸마다 라벨 표시
        x_lable_overrides = {
                    i: date for i, date in enumerate(df['Date']) if i % 30 == 0
                }

        # p1.xaxis.major_label_overrides = x_lable_overrides
        p2.xaxis.major_label_overrides = x_lable_overrides
        p2.x_range.range_padding = 0.05
        p2.xaxis.axis_label = "Date"
        p2.yaxis.axis_label = "Volume"

        ## 그리드 설정
        p2.xgrid.grid_line_color = None
        p2.ygrid.grid_line_alpha = 0.5
        p1.xaxis.ticker = []  # This removes the tick marks
        p2.xaxis.ticker = []  # This removes the tick marks
        p1.xaxis.axis_label = None  # This removes the x-axis label
        p2.xaxis.axis_label = None  # This removes the x-axis label
        ## 주석 (유통주식수, 상장주식수)



        # 그래프간 공백제거
        p1.min_border_bottom = 0
        p2.min_border_top = 0

        ## 거래량 최소값부터 보이기
        p2.y_range.start = source.data["Volume"].min() / 2
        p2.y_range = DataRange1d()  # Y축을 DataRange1d로 설정하여 동적 범위 설정


        # HoverTool 추가 data source 에서 값갖온다.
        hover = HoverTool()
        hover.tooltips = [
            ("Date:", "@Date{%F}"),
            ("open", "@Open{0,0}"),
            ("high", "@High{0,0}"),
            ("low", "@Low{0,0}"),
            ("close", "@Close{0,0}"),
            ("volume", "@Volume{0,0}"),
            ("volma20", "@vol20ma{0,0}"),
            ("upper240", "@upper{0,0}"),
            ("lower240", "@lower{0,0}"),
            ("bb240_width", "@bb240_width{0,0}"),
            ("upper60", "@upper60{0,0}"),
            ("lower60", "@lower60{0,0}"),
            ("bb60_width", "@bb60_width{0,0}"),
            ("mesh_width", "@sun_width{0,0}"),
            
        ]  # 툴팁 설정
        hover.formatters = {"@Date": "datetime"}  # '@date' 열을 datetime으로 처리
        # HoverTool 스타일 설정 필요 ( 투명도 )
        # hover.renderers = 
        p1.add_tools(hover)
        p2.add_tools(hover)


        # 축 범위 업데이트를 위한 CustomJS 콜백
        callback = CustomJS(args=dict(source=source, y_range=p2.y_range), code="""
            const data = source.data;
            const start = cb_obj.start;
            const end = cb_obj.end;
            const y_values = data['volume'];
            const x_values = data.index;
            let min_y = Infinity;
            let max_y = -Infinity;

            for (let i = 0; i < x_values.length; i++) {
                if (x_values[i] >= start && x_values[i] <= end) {
                    min_y = Math.min(min_y, y_values[i]);
                    max_y = Math.max(max_y, y_values[i]);
                }
            }
            y_range.start = min_y - 1; // 작은 여유 추가
            y_range.end = max_y + 1; // 작은 여유 추가
        """)

        # x축이 변경될 때 콜백 트리거 설정
        p2.x_range.js_on_change('start', callback)
        p2.x_range.js_on_change('end', callback)        
        
        ## merge graph
        layout = column(p1, p2, range_bar, sizing_mode="stretch_both")
        
        return layout

    def plot1(self, option='day', cnt=180, investor=True):
        title = f'{self.ticker.name}({self.ticker.code})'
        ## data 준비. 
        if option == "day":
            chart_obj = getattr(self, "chart_d")
            arr_ma = np.array([3, 20, 60, 120, 240])
        elif '30' in str(option) :
            if not hasattr(self, 'chart_30'):
                new_ohlcv = GetData._get_ohlcv_from_daum(
                code=self.code, data_type="30분봉"
            ) 
                self.chart_30 = chart.Chart(new_ohlcv)
            chart_obj = getattr(self, 'chart_30')
            arr_ma = np.array([10, 20, 60, 120, 240])
            title += ' 30분봉'
        elif '5' in str(option):
            if not hasattr(self, 'chart_5'):
                new_ohlcv = GetData._get_ohlcv_from_daum(
                code=self.code, data_type="5분봉"
            ) 
                self.chart_5 = chart.Chart(new_ohlcv)
            chart_obj = getattr(self, 'chart_5')
            arr_ma = np.array([10, 20, 60, 120, 240])
            title += ' 5분봉'
        else:
            return None
        
        df: pd.DataFrame = chart_obj.df.iloc[-cnt:].copy()
        df = df.reset_index()
        if option =='day':
            if isinstance(self.investor_part, pd.DataFrame):
                start_date = df['Date'].iloc[0]
                investor_part = self.investor_part.loc[self.investor_part['start'] >= start_date]
                investor_part = investor_part.reset_index(drop=True)
        
        sun_min = chart_obj.sun.line_min.data.reset_index().iloc[-cnt:] if hasattr(chart_obj.sun, 'line_min') else None
        sun_max = chart_obj.sun.line_max.data.reset_index().iloc[-cnt:] if hasattr(chart_obj.sun, 'line_max') else None

        
        
        # subplot 생성
        fig = make_subplots(rows=2, cols=1, 
                            shared_xaxes=True,
                            # shared_yaxes=True,
                            vertical_spacing=0.1,
                            # subplot_titles=("Candlestick Chart", "Volume"),
                            row_heights=[0.7, 0.3])

        # 캔들차트 추가
        fig.add_trace(
            go.Candlestick(x=df['Date'],
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'],
                        name='',
                        increasing=dict(line=dict(color='red')),  # 상승 시 빨간색
                        decreasing=dict(line=dict(color='blue')),
                        )
            , row=1, col=1)


        # 이동평균선 추가
        colors = ['black', 'red','blue','green','gray']
        widths = [1,2,2,2,3]
        for ma, color, width in zip(arr_ma, colors, widths):
            strma =  f"ma{ma}"
            if hasattr(chart_obj, strma):
                line_obj = getattr(chart_obj, strma)
                ma_data = line_obj.data.reset_index().iloc[-cnt:]
                fig.add_trace(
                    go.Scatter(x=ma_data['Date'], 
                            y=ma_data[f'{strma}'], 
                            mode='lines', 
                            name='', 
                            line=dict(color=color, width=width),
                            ), 
                    row=1, col=1)

        # bb 추가
        bb_names = ['bb60','bb240']
        bb_colors = ['blue','gray']
        bb_widths = [2,4]
        for bb_name, bb_color, bb_width in zip(bb_names, bb_colors, bb_widths):
            if hasattr(chart_obj, bb_name):
                bb_obj = getattr(chart_obj, bb_name) 
                for line in ["line_lower", "line_upper"]:
                    if hasattr(bb_obj, f"{line}"):
                        line_data = getattr(bb_obj, f"{line}").data
                        line_data = line_data.iloc[-cnt:]
                        fig.add_trace(go.Scatter(
                                    x=line_data.reset_index()['Date'], 
                                    y=line_data, 
                                    mode='lines', 
                                    name='', 
                                    line=dict(color=bb_color, width=bb_width),
                                    ), 
                                    row=1, col=1)

        ###########################################################################################
        # sun 두 선 사이를 채우기
        # 두 번째 선과의 채우기
        if isinstance(sun_max, (pd.DataFrame, pd.Series)):
            fig.add_trace(go.Scatter(
                x=sun_max['Date'],
                y=sun_max['max'],
                mode='lines',
                line=dict(color='rgba(0,0,0,0)'),  # 투명한 선
                showlegend=False,
                fill='tonexty',  # 다음 y축으로 채우기
                fillcolor='rgba(255,165,0,0.2)',  # 채우기 색상
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=sun_min['Date'],
                y=sun_min['min'],
                mode='lines',
                line=dict(color='rgba(0,0,0,0)'),  # 투명한 선
                showlegend=False,
                fill='tonexty',  # 다음 y축으로 채우기
                fillcolor='rgba(0,100,80,0.2)',  # 채우기 색상
            ), row=1, col=1)


        # 매물대 수평선 추가 매물대가 하나일때도 있어서 일단 예외처리로 막아놓음. 
        try:
            price_values = chart_obj.pricelevel.first, chart_obj.pricelevel.second
            
            widths = [2,1]
            for value, width in zip(price_values, widths):
                if not value is None:
                    fig.add_shape(type='line',
                                x0=chart_obj.pricelevel.start_date, x1=chart_obj.pricelevel.end_date,  # x축 범위 설정
                                y0=value, y1=value,  # y축 값 설정
                                line=dict(
                                    color='purple', 
                                    width=width, 
                                    # dash='dash',
                                ),  # 선의 스타일 설정
                                row=1, col=1)  # 첫 번째 서브플롯에 수평선 추가
        except:
            pass
        ##############################################################################################

        ## 거래량 바차트
        ## 평균거래량 추가
        if hasattr(chart_obj.vol, 'ma_vol'):
            vol20 = chart_obj.vol.ma_vol.reset_index().iloc[-cnt:]
            fig.add_trace(
                go.Scatter(x=vol20['Date'], 
                        y=vol20[f'20ma'], 
                        mode='lines', 
                        name='', 
                        line=dict(color='red', width=1),
                        ), 
                row=2, col=1)

        # 상장주식수 수평선 추가
        x_values = [self.상장주식수, self.유동주식수]
        widths = [3,1]
        colors = ['red','purple']
        for value, width, color in zip(x_values, widths, colors):
            if value:
                fig.add_hline(y=value,
                              line_dash='dot',
                                line_color=color,
                                line_width=5, 
                                opacity=0.7, 
                                row=2, 
                                col=1,
                                )

        # 거래량 바 색상 설정
        # vol20['20ma'] 보다 작은값 blue
        if hasattr(chart_obj.vol, 'ma_vol'):
            vol_colors = ['blue' if vol < ma20 else 'gray' for vol, ma20 in zip(df['Volume'], vol20['20ma'])]
        else:
            vol_colors = ['gray' for vol in df['Volume']]
        # 전일거래량 또는 전전일보다 2배이상 red
        vol_colors = ['red' if pre_vol * 2 < vol else color 
                    for pre_vol, vol, color in zip(df['Volume'].shift(1), df['Volume'],vol_colors)]
        # 유동주식수보다 많은거 yellow
        if self.유동주식수:
            vol_colors = ['yellow' if self.유동주식수 <= vol else color 
                        for color, vol in zip(vol_colors, df['Volume'])]
        # 상장주식수보다 많은거 purple
        if self.상장주식수:
            vol_colors = ['purple' if self.상장주식수 <= vol else color 
                        for color, vol in zip(vol_colors, df['Volume'])]

        fig.add_trace(go.Bar(x=df['Date'], 
                            y=df['Volume'], 
                            name='', 
                            marker_color=vol_colors), 
                    row=2, col=1)


        min_range = int(df['Volume'].iloc[-60:].min() * 0.8)
        max_range = int(df['Volume'].iloc[-60:].max() * 1.2)
        fig.update_yaxes(range=[min_range, max_range], row=2, col=1)  # 거래량 차트 y축 범위 설정

        fig.update_yaxes(autorange=True, row=1, col=1)

        # 존재하는 데이터 중 매월 첫 번째 날짜 추출

        df['YearMonth'] = df['Date'].dt.to_period('M')  # 연-월로 변환
        monthly_first_dates = df.groupby('YearMonth').first().reset_index()['Date']  # 첫 번째 날짜 추출
        tick_labels = monthly_first_dates.dt.strftime('%Y-%m').tolist()  # 레이블 형식 설정

        # 레이아웃 설정
        fig.update_layout(title=title,
                        xaxis_title='',
                        yaxis_title='Price',
                        xaxis_rangeslider_visible=False,
                        xaxis_type='category', # xaxis를 category로 설정 (빈공간 무시)
                        width=800, 
                        height=600,
                        xaxis=dict(
                            tickvals=monthly_first_dates,  # tick 위치 설정
                            ticktext=tick_labels,  # tick 레이블 설정
                        ), 
                        showlegend=False,
                        # dragmode='zoom'
                        )  
        fig.update_xaxes(type='category')
        fig.update_xaxes(tickvals=monthly_first_dates, ticktext=tick_labels, row=2, col=1)


        # y축 동기화
        fig.update_xaxes(matches='x')

        
        ## investor_part plot
        if option =='day':
            if investor:
                if isinstance(investor_part, pd.DataFrame):
                    import math
                    # color_palette = ['lightcoral','lightpink']
                    # group_cnt = len(investor_part['group'].unique())
                    # color_palette = color_palette * math.ceil(group_cnt/len(color_palette))
                                
                    investor_part['text'] = '주도기관: ' + investor_part['주도기관'] + '<br>' + \
                    '순매수금(억): ' + investor_part['순매수금_억'].map(lambda x: f"{x:.1f}") + '<br>' +  \
                    '매집비: ' + investor_part['매집비'].map(lambda x: f"{x:.1f}%") + '<br>' +  \
                    '풀매수기관: ' + investor_part['풀매수기관'].map(lambda x: ','.join(x) if not type(float) else '')
                    
                    try:
                        investor_part['group_color'] = np.where(investor_part['group'] % 2 == 0, 'lightcoral', 'lightpink')
                    except:
                        investor_part['group_color'] = 'blue'

                    annotations = [dict(
                        x=row['start'], 
                        y = row['ma3'], 
                        text=row['text'],showarrow=True ,
                        ax=0, ay=40,
                        font=dict(color='black', size=8),
                        bgcolor=row['group_color'],  # 배경 색상
                        # bgcolor='lightpink',  # 배경 색상
                        # bordercolor='black',    # 테두리 색상
                        # borderwidth=2,          # 테두리 두께
                        opacity=0.8,             # 투명도
                        )
                    for _, row in investor_part.iterrows()]
                    fig.update_layout(annotations=annotations)
                    
        
        '''
        fig = stock.plot1()
        graph_html = fig.to_html(full_html=False)
        
        1. 쥬피터 노트북 
        from IPython.display import display, HTML
        display(HTML(graph_html))
        
        2. 장고
        context = {graph : graph_html}
        '''
        return fig
    
    def plot_consen(self, gb='y', limit=6):
        '''
        y: 연간, q: 분기
        '''
        if gb=='y':
            if self.fin_df is not None and (isinstance(self.fin_df, pd.DataFrame) and not self.fin_df.empty):
                df = self.fin_df.copy().iloc[-limit:]
                df['text'] = df['growth'].apply(lambda x: "적자" if x == -10000 else '턴어라운드' 
                                                if x==-1000 else f"{x} %")        
                df['text'] = df['text'].astype(str) + "<br>(" +  df['영업이익'].astype(int).apply(lambda x:f"{x:,}") + "억원)"
                title = f'Year {self.ticker.name}({self.ticker.code})'
                ext_x = self.f_year
        else:
            if self.fin_df_q is not None and (isinstance(self.fin_df_q, pd.DataFrame) and not self.fin_df_q.empty):
                df = self.fin_df_q.copy().iloc[-limit:]
                df['year'] = df.index
                df['text_yoy'] = df['yoy'].apply(lambda x: "yoy : 적자" if x == -10000 else 'yoy : 턴어라운드' 
                                                if x==-1000 else f"yoy :{x} %")  
                df['text_qoq'] = df['qoq'].apply(lambda x: "qoq : 적자" if x == -10000 else 'qoq : 턴어라운드' 
                                                if x==-1000 else f"qoq : {x} %")  
                df['text'] = df['text_yoy'] + "<br>" + df['text_qoq']
                title = f'Quarter {self.ticker.name}({self.ticker.code})'
                ext_x = self.quarters[-1]
        

        fig = make_subplots(rows=1, cols=1, specs=[[{'secondary_y': True}]])

        fig.add_trace(
            go.Scatter(
                x = df['year'],
                y = df['매출액'],
                mode = 'lines+markers+text',
                name = '매출액(억)',
                line = dict(color='red', width=2),
                marker= dict(size=8, color='red'),
            ), secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x = df['year'],
                y = df['영업이익'],
                mode = 'lines+markers+text',
                name = '영업이익(억)',
                text = df['text'],
                textposition='bottom center',
                textfont=dict(color='black',size=12),  # 텍스트 색상 설정
                line = dict(color='blue', width=2),
                marker= dict(size=8, color='blue'),
            ), secondary_y=True
        )
        fig.update_yaxes(title_text='매출(억원)', secondary_y=False)
        fig.update_yaxes(title_text='영업이익(억원)', secondary_y=True)

        ## 특정연도분기 표기
        if ext_x in str(df['year']):
            fig.add_vline(x=ext_x,
                line_color="magenta",
                line_width=80, 
                opacity=0.3, 
                )
        # 레이아웃 설정
        fig.update_layout(title=title)
        return fig
    
    
    
    def __repr__(self):
        return f"<Stock> {self.ticker.name}({self.ticker.code})"
