import asyncio
import re
import warnings
import numpy as np
import pandas as pd
# warnings.filterwarnings('ignore')
import talib
from datetime import datetime
from bokeh.models import DatetimeTickFormatter, Span, TableColumn, DataTable
import itertools
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, Range1d, RangeTool, FactorRange
from bokeh.models import HoverTool, CustomJS
from bokeh.models import Span, Label
from bokeh.layouts import gridplot, column, row
from bokeh.models.formatters import NumeralTickFormatter
from bokeh.models import SingleIntervalTicker, AdaptiveTicker
# from bokeh.io import output_notebook
# output_notebook()

class LineCross:
    """
    ma +- 연산시 두 ma에 대한 MaCross 객체 반환
    """

    def __init__(self, line1, line2):

        self.line1, self.line2 = line1, line2
        self.__s1_name, self.__s2_name = self.line1.name, self.line2.name

        self.diff = self.line1.data - self.line2.data
        self.diff = self.diff.loc[self.diff.notnull()]

        self.gc_date_ls, self.dc_date_ls = self.__get_cross_date()
        self.cross_status, self.last_cross_date = self.__get_array_status()

        # short ma - long ma 이격도 계산
        # self.disparity = (self.s1 / self.s2) * 100  ## 이격도
        self.disparity = (self.line2.data / self.line1.data) * 100  ## 이격도
        self.width = self.__get_width()  ## 두께.

    ##??  너비(%) 이격도 차이 체크.

    def is_gcv(self, n=2, verbose=False):
        """
        n : gc이후 v 개수 n 이하조건
        """
        result = False
        cond_array = self.cross_status == "정배열"  # short 이 정배열인상태조건
        if cond_array:
            if len(self.dc_date_ls):  # 마지막 cross 날짜 가져옴
                if len(self.line1.df_last_low_points):
                    df_the_date = self.line1.df_last_low_points.loc[
                        self.gc_date_ls[-1] :
                    ]  # gc이후의 저점 데이터 가져옴.
                    ## 1개이면 첫번째 v
                    (
                        print(f"조건만족 저점개수: {len(df_the_date)} 개 in is_gcv")
                        if verbose
                        else None
                    )
                    (
                        print(f"조건 저점일 데이터{df_the_date} in is_gcv")
                        if verbose
                        else None
                    )
                    if 0 < len(df_the_date) <= n:
                        result = True

        print(f"정배열 {cond_array} in is_gcv") if verbose else None

        return result

        print("몇번째인지 return 하기.") if verbose else None

    def __get_width(self):

        lines = pd.concat([self.line1.data, self.line2.data], axis=1)
        width_s = lines.apply(
            lambda x: (
                max(x[self.__s1_name], x[self.__s2_name])
                / min(x[self.__s1_name], x[self.__s2_name])
                - 1
            )
            * 100,
            axis=1,
        )
        width_s.name = "width"
        return width_s

    def plot(self):
        ax = self.line1.data.plot()
        self.line2.data.plot(ax=ax)
        return ax

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def __get_cross_date(self):
        """
        Cross State
        """
        if len(self.diff):
            gc_cond = (self.diff.shift(1) < 0) & (self.diff > 0)
            dc_cond = (self.diff.shift(1) > 0) & (self.diff < 0)
            gc_date = list(gc_cond.loc[gc_cond].index)
            dc_date = list(gc_cond.loc[dc_cond].index)

            공집합 = set(gc_date) & set(dc_date)

            if 공집합:
                for date in 공집합:
                    gc_date.remove(date)
                    dc_date.remove(date)

        else:
            gc_date, dc_date = [], []
        return gc_date, dc_date

    def __get_array_status(self):
        """
        return : 배열상태 ( "역배열", "정배열")
        """
        if len(self.gc_date_ls) == 0 and len(self.dc_date_ls) == 0:
            last_cross_date = None
            cross_status = (
                "정배열"
                if self.line1.data.iloc[-1] > self.line2.data.iloc[-1]
                else "역배열"
            )
        elif len(self.gc_date_ls) and len(self.dc_date_ls) == 0:
            last_cross_date = self.gc_date_ls[-1]
            cross_status = "정배열"
        elif len(self.gc_date_ls) == 0 and len(self.dc_date_ls):
            last_cross_date = self.dc_date_ls[-1]
            cross_status = "역배열"
        else:
            cross_status = (
                "정배열" if self.dc_date_ls[-1] < self.gc_date_ls[-1] else "역배열"
            )
            last_cross_date = max(self.dc_date_ls[-1], self.gc_date_ls[-1])
        return cross_status, last_cross_date

    def __repr__(self):
        return f"{self.line1.name}_{self.line2.name} Array State"


class Line:
    """
    단순 line 객체
    ignore_cnt_dict = {3:1, 5:1, 10:2, 20:2, 40:2, 60:3, 120:4, 240:5,}
    """

    def __init__(self, data, start=None, end=None, ignore_cnt=1, allow_rate=1):

        self.data = data  # Series with name
        if not isinstance(self.data, (pd.DataFrame, pd.Series)):
            self.data = pd.Series(data)
        if not self.data.name:
            self.data.name = "name"
        self.name = data.name

        self.__start = start
        self.__end = end

        if not self.__start is None and self.__start in data.index:
            self.data = self.data.loc[self.__start :]
        if not self.__end is None and self.__end in data.index:
            self.data = self.data.loc[: self.__end]

        self._ignore_cnt = ignore_cnt
        self._allow_rate = allow_rate

        self._value_column, self._change_column = (
            f"{self.name}_변곡점",
            f"{self.name}_변곡점_변화량",
        )
        ## 상장된지얼마 안된종목을 위한 예외처리
        try:
            self.current_value = self.data.iloc[-1]
            self.current_direction = (
                "up"
                if data.iloc[-2] < self.data.iloc[-1] and data.iloc[-3] < self.data.iloc[-1]
                else "down"
            )  # 방향. 2일 연속 만족해야 인정.
        except:
            self.current_value = None
            self.current_direction = 'down'
            
        try:    
            self.df_curve = pd.DataFrame(self.data)
            self.df_curve[f"{self.name}_변화량"] = self.data.pct_change()
            self.df_curve = pd.concat(
                [
                    self.df_curve,
                    self._add_low_high(
                        self.df_curve[self.name], ignore_cnt=self._ignore_cnt
                    ),
                ],
                axis=1,
            )
            self.df_all_low_points, self.df_all_high_points, self.df_last_low_points = (
                self._get_low_high_points(allow_rate=self._allow_rate)
            )
        except:
            self.df_curve = pd.DataFrame(self.data)
            self.df_all_low_points, self.df_all_high_points, self.df_last_low_points = (pd.DataFrame(),pd.DataFrame(),pd.DataFrame())

        try:
            self.inclination20 = self.df_curve[f"{self.name}"].pct_change(20)
            self.inclination20.name = f"{self.name}_inclination20"
            self.inclination10 = self.df_curve[f"{self.name}"].pct_change(10)
            self.inclination10.name = f"{self.name}_inclination10"

            self.inclination20_value = round(
                self.inclination20.iloc[-1] * 100, 1
            )  ## 편평도.
            self.inclination10_value = round(
                self.inclination10.iloc[-1] * 100, 1
            )  ## 편평도.
        except Exception as e:
            self.inclination20_value, self.inclination10_value = None, None
            self.inclination20, self.inclination10 = pd.Series(), pd.Series()
            
            
            
    def _add_low_high(self, series, ignore_cnt=0):
        """
        return df
        """
        series1 = series.copy()

        while sum(series1 == series1.shift(-1)):
            series1 = series1.loc[~(series1 == series1.shift(-1))]
            # print("같은값제거")

        # print('같은값 제거: ' ,len(series) - len(series1),'개')

        variation_cond = (
            (series1.shift(-1) < series1) & (series1 > series1.shift(1))
        ) | ((series1.shift(-1) > series1) & (series1 < series1.shift(1)))
        result = series.loc[variation_cond[variation_cond].index]

        col_name = f"{series.name}_변곡점"
        # print("col_name : ", col_name)
        result.name = col_name
        result = result.to_frame()

        # ##
        # ignore_cnt 제거하기.
        if len(result) > 1:
            for i in range(len(result) - 1):
                start = result.index[i]
                end = result.index[i + 1]
                distance = len(series.loc[start:end]) - 1  # 실제차이수.
                if i == len(result) - 1:
                    # print('exit')
                    break
                if distance <= ignore_cnt:
                    if not np.isnan(result.loc[start, f"{col_name}"]):
                        if not np.isnan(result.loc[end, f"{col_name}"]):
                            # print("제거날짜!!",  start , end)
                            result.loc[start, f"{col_name}"] = np.nan
                            result.loc[end, f"{col_name}"] = np.nan
            result = result[col_name].dropna()
            # check 용.
            # print("2: ", len(result))

            result = result.to_frame()
            ## 변화량 계산
            if len(result) > 0:
                result[f"{series.name}_변곡점_변화량"] = result[col_name].pct_change()
            else:
                result[f"{series.name}_변곡점_변화량"] = result[col_name]

        # result_df = pd.concat([series, result], axis=1)
        else:
            result[[f"{series.name}_변곡점", f"{series.name}_변곡점_변화량"]] = (
                np.nan,
                np.nan,
            )

        return result

        # self.df[[f"{self.str_ma}_변곡점",f"{self.str_ma}_변곡점_변화량"]]= self.__add_low_high(self.df[self.str_ma], ignore_cnt=self.ignore_cnt)
        # self.temp_df= self.__add_low_high(self.df[self.str_ma], ignore_cnt=ignore_cnt)

    def _get_low_high_points(self, allow_rate=1):
        """
        df: ohlcv 로 여러 지표데이터 포함된 데이터
        value_column : 변곡점 컬럼
        change_column  : 변곡점 변화율 컬럼
        allow_rate : 저점 인지 허용비율.
        저점리스트 마지막값과 고점리스트 마지막값으로 상황 파악해야함.
        return : all_low_points, all_high_points, 연속저점 묶음
        """
        df = self.df_curve

        if not len(df):
            all_low_points, all_high_points, last_low_points = (
                pd.Series(),
                pd.Series(),
                pd.Series(),
            )
            return all_low_points, all_high_points, last_low_points

        # ma = .value_column.split("_")[0]
        ma = self.name

        if not self._value_column in df.columns:
            df[f"{ma}"].plot()
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        if not self._change_column in df.columns:
            df[f"{ma}"].plot()
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        df1 = df.loc[df[f"{self._value_column}"].notnull()].copy()
        # df[f'{value_column}'].plot()

        # 저점 추출
        cond_low = df1[f"{self._change_column}"] < 0
        cond_high = df1[f"{self._change_column}"] > 0

        ## stock.chart_d.df.filter(['ma3','ma5']).loc[stock.chart_d.all_low_points.index]

        all_low_points = df1.filter([self._value_column, self._change_column]).loc[
            cond_low
        ]  # DataFrame
        all_high_points = df1.filter([self._value_column, self._change_column]).loc[
            cond_high
        ]  # DataFrame
        # all_low_points = cond_low.loc[cond_low] # Series
        # all_high_points = cond_high.loc[cond_high]

        low_df = df1.loc[cond_low].copy()

        # 좌우 조건 입력  # 한저점에서 왼쪽과의 성립여부와 오른쪽과의 성립여부
        l = (
            low_df[f"{self._value_column}"].shift(1) * allow_rate
            < low_df[f"{self._value_column}"]
        )
        l.name = "left"
        r = low_df[f"{self._value_column}"] * allow_rate < low_df[
            f"{self._value_column}"
        ].shift(-1)
        r.name = "right"
        temp_df = pd.concat([l, r], axis=1)
        # display(low_df.tail(2))

        try:
            temp_df.loc[(~temp_df["left"]) & (temp_df["right"]), "gubun"] = 1
            temp_df.loc[(temp_df["left"]) & (~temp_df["right"]), "gubun"] = 0
            temp_df.loc[(temp_df["left"]) & (temp_df["right"]), "gubun"] = 0
            temp_df.loc[~(temp_df["left"]) & (~temp_df["right"]), "gubun"] = 1

            # temp_df = temp_df.loc[(temp_df['left']) | (temp_df['right'])]
            temp_df["cumsum"] = temp_df["gubun"].cumsum()
            # # display(low_df.tail(3))

            s = temp_df["cumsum"]
            # 변화 감지 및 누적 합계 계산
            groups = (s != s.shift()).cumsum().to_frame(name="gubun")
            groups["value"] = df[f"{self._value_column}"]
            # 그룹별로 분리
            # display(groups)

            last_low_date = []
            grouped = groups.groupby("gubun")
            cnt = len(grouped)
            # print("cnt : ", cnt)
            for idx1, group in grouped:
                # print(idx1, end=',')
                index = group.index  ## 저점 인덱스
                last_low_date.append(index)
            if len(last_low_date[-1]):
                # print('존재함.',last_low_date[-1])
                last_low_points = all_low_points.loc[last_low_date[-1]]
            else:
                last_low_points = pd.DataFrame()
        except:
            last_low_points = pd.DataFrame()

        return all_low_points, all_high_points, last_low_points
        # return all_low_points, all_high_points, last_low_date

    def is_w(self, verbose=False):

        w_cond = False

        if len(self.df_last_low_points):
            w_cond1 = (
                self.df_last_low_points.index[-1] == self.df_all_low_points.index[-1]
            )  # 마지막w가 현재 진행중이다.
            w_cond2 = (
                len(self.df_last_low_points) > 1
            )  # 마지막 저점리스트가 1개 이상이다.
            w_cond3 = (
                self.df_all_high_points.index[-1] < self.df_all_low_points.index[-1]
                if len(self.df_all_high_points)
                else False
            )  # 최근고점보다 최근저점이 크다.
            up_cond4 = self.current_direction == "up"
            w_cond = w_cond1 & w_cond2 & w_cond3 & up_cond4
            ## 저점이후 지속일 체크해야함. ## 현재가와 비교해야함. 현재가가 높아야 계속 끌어올린다.
            if verbose:
                print(f"마지막저점 : {self.df_last_low_points.index[-1]}")
                print(
                    f"지속일 :{len(self.data.loc[self.df_last_low_points.index[-1]:])} 일 "
                )
                print(f"현재이격도: {round(self.disparity[-1],2)}")
        if w_cond:
            return len(
                self.data.loc[self.df_last_low_points.index[-1] :]
            )  ## 지속일 반환.
        else:
            return 0

    def is_wa(self, verbose=False):

        ww_cond = False
        if len(self.df_last_low_points):
            ww_cond1 = (
                len(self.df_last_low_points) > 0
            )  # 마지막 저점리스트가 0개 이상이다.
            ww_cond2 = (
                self.df_all_high_points.index[-1] > self.df_all_low_points.index[-1]
                if len(self.df_all_high_points)
                else False
            )  # 최근이 고점이다.
            ww_cond3 = (
                self.df_all_low_points[self._value_column].iloc[-1]
                <= self.df_curve[self.name].iloc[-1]
            )  ## 전저점 지키는 중이다.
            up_cond4 = self.current_direction == "down"
            ## 단봉이거나. 기울기가 변하는 중이거나 현재가가 ma위로 뚫은것들만
            #  아주 중요하게 현재가를 넣어줭한다. 그래야 방향이 꺽일수 있다.
            ww_cond = all([ww_cond1, ww_cond2, ww_cond3, up_cond4])
            if verbose:
                print(f"마지막저점 : {self.df_last_low_points.index[-1]}")
                print(
                    f"지속일 :{len(self.data.loc[self.df_last_low_points.index[-1]:])} 일 "
                )
                print(f"현재이격도: {round(self.disparity[-1],2)}")
        return ww_cond

    def is_ab_value(self, verbose=False):
        """
        가격ab파동
        """
        result = False
        if self.is_w():
            a_value = self.df_curve.loc[self.df_all_low_points.index[-2], self.name]
            b_value = self.df_curve.loc[self.df_all_high_points.index[-1], self.name]
            c_value = self.df_curve.loc[self.df_all_low_points.index[-1], self.name]

            a = b_value - a_value
            b = b_value - c_value
            result = a > b
            if result:
                print(f"상태: w") if verbose else None

        elif self.is_wa():
            a_value = self.df_curve.loc[self.df_all_low_points.index[-1], self.name]
            b_value = self.df_curve.loc[self.df_all_high_points.index[-1], self.name]
            c_value = self.df_curve.iloc[-1][self.name]
            a = b_value - a_value
            b = b_value - c_value
            result = a > b
            if result:
                print(f"상태: wa") if verbose else None
        return result

    def is_ab_period(self, verbose=False):
        """
        기간ab파동
        """
        result = False
        if self.is_w():
            a = self.df_curve.loc[
                self.df_all_low_points.index[-2] : self.df_all_high_points.index[-1]
            ]
            b = self.df_curve.loc[
                self.df_all_high_points.index[-1] : self.df_all_low_points.index[-1]
            ]
            result = len(a) >= len(b)
            if result:
                (
                    print(
                        f"상태: w",
                    )
                    if verbose
                    else None
                )
                print(f"a:", a) if verbose else None
                print(f"b:", b) if verbose else None

        elif self.is_wa():
            a = self.df_curve.loc[
                self.df_all_low_points.index[-1] : self.df_all_high_points.index[-1]
            ]
            b = self.df_curve.loc[self.df_all_high_points.index[-1] :]
            result = len(a) >= len(b)
            if result:
                print(f"상태: wa") if verbose else None
                print(f"a:", a) if verbose else None
                print(f"b:", b) if verbose else None
        return result

    def plot(self):
        ax = self.data.plot()
        return ax

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def __repr__(self):
        return f"{self.name} Line"

    def __add__(self, other):
        return LineCross(self, other)

    def __sub__(self, other):
        return LineCross(self, other)


class Ma(Line):
    """
    특정ma에 대한 정보
    ignore_cnt_dict = {3:1, 5:1, 10:2, 20:2, 40:2, 60:3, 120:4, 240:5,}
    """

    def __init__(self, df, ma=3, start=None, end=None, allow_rate=1, ignore_cnt=0):

        self.ma = ma
        self.allow_rate = allow_rate
        self.ignore_cnt = ignore_cnt

        self.__start = start
        self.__end = end

        df, self.str_ma = self._get_ma_data(df, ma)

        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        super().__init__(
            data=df[self.str_ma], ignore_cnt=ignore_cnt, allow_rate=allow_rate
        )

        self.df_curve = pd.concat(
            [df.filter(regex=f"^(?!.*{self.str_ma}).*"), self.df_curve], axis=1
        )

        # self.df_curve = pd.concat([df, self.df_curve],axis=1)
        # columns = list(set(self.df_curve.columns))
        # self.df_curve = self.df_curve[columns]

        ## ma 특성.
        self.disparity = (self.df_curve["Close"] / self.df_curve[self.str_ma]) * 100

        self._get_전저점()

    def __adjust_columns(self, df):
        new_name_dict = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
            "value": "Value",
            "change": "Change",
        }
        df = df.rename(columns=new_name_dict)
        # temp_df = df.copy()
        return df

    def _get_ma_data(self, df, ma):
        ## df 체크
        if not df is None and isinstance(df, pd.DataFrame):
            df = self.__adjust_columns(df).copy()
        else:
            df = pd.DataFrame()  ## 직접 데이터 다운로드.?

        ## ma 체크
        if re.match("^\d+$", str(ma)):
            str_ma = f"ma{ma}"
        else:
            str_ma = f"{ma}"

        ## 데이터개수 체크후 add _ma
        if ma > 300:
            print(f"ma가 너무 크다 -> ma: {ma}")

        df[str_ma] = talib.MA(df["Close"], ma)  # line

        return df, str_ma

    def _get_전저점(self):
        """
        전저점, 전저점날짜  None, None
        """
        self.전저점, self.전저점날짜 = None, None
        if len(self.df_all_low_points):
            the_date = self.df_all_low_points.index[-1]
            # print('0')
            try:
                except_word = "ma\d+"
                if not re.findall(
                    f"^(?!.*{except_word}).*", self.name
                ):  ## ma가 아닌게 아니면. -> ma이면   ex) ma40 (o)  rsi(x)
                    # cnt = int(re.findall('\d+', self.name)[0])
                    # print('1')
                    if 0 < self.ma < 120:
                        temp_df = self.df_curve.loc[:the_date].iloc[-self.ma :]
                        temp_df = temp_df["Low"]
                        # print("2")
                        if len(temp_df):
                            # print("3")
                            self.전저점 = temp_df.min()
                            self.전저점날짜 = temp_df.idxmin()

                else:
                    self.전저점날짜 = self.df_all_low_points.index[-1]
                    # print('4')

            except Exception as e:
                print(e, "asdfasdf", self.ma, len(self.df_curve))

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def __repr__(self):
        return f"{self.str_ma} MA"

    def __add__(self, other):
        return LineCross(self, other)

    def __sub__(self, other):
        return LineCross(self, other)


class Ac111:

    def __init__(self, df, start=None, end=None, pre_vol_rate=2, ma20vol_rate=2):

        self._start = start
        self._end = end
        self._pre_vol_rate = pre_vol_rate
        self._ma20vol_rate = ma20vol_rate
        self._ac_info = self._get_ac_info(df)
        self.last_date = df.index[-1]
        # keys : ['ac', 'ma5', 'ma20', 'sun_max', 'upper_bb_60','upper_bb_240']

    def _get_ac_info(self, df):
        """
        ac의 위치, 관계등 확인하기.
        through_mas =['5', '20', 'sun_max', 'upper_bb_60','upper_bb_240']
        pre_vol_rate : 전일 또는 전전일 거래량대비율.
        ma20vol_rate : ma20vol 대비 거래량대비율

        through_mas = ['5', 'sun_max', 'upper_bb_60', 'upper_bb_240']
        last_ac:bool,
        start_date:'',
        through:bool,

        """
        through_mas = ["5", "20", "sun_max", "upper_bb_60", "upper_bb_240"]

        if not self._start is None and self._start in df.index:
            df = df.loc[self._start :]
        if not self._end is None and self._end in df.index:
            df = df.loc[: self._end]
            print("end run")

        ac_cond = False
        new_mas = []  #
        through_cond_ls = []
        if len(df):
            #
            ac_cond1 = (df["Close"] > df["Close"].shift(1)) & (
                (df["Volume"] > df["Volume"].shift(1) * self._pre_vol_rate)
                | (df["Volume"] > df["Volume"].shift(2) * self._pre_vol_rate)
            )
            ac_cond2 = (df["Close"] > df["Close"].shift(1)) & (
                (df["Volume"] > df["vol20ma"] * self._ma20vol_rate)
                | (df["Volume"] > df["vol240ma"] * self._ma20vol_rate * 1.5)
            )
            ac_cond3 = (df["Close"] > df["Open"]) & (
                (df["Volume"] > df["Volume"].shift(1) * 1.5)
                | (df["Volume"] > df["Volume"].shift(2) * 1.5)
            )
            ac_cond = ac_cond1 | ac_cond2 | ac_cond3

            cond_data = ac_cond.loc[ac_cond]
            if len(cond_data):
                new_mas.append("ac")
                through_cond_ls.append(cond_data.index)

        if not through_mas is None:
            if len(through_mas):
                for ma in through_mas:
                    pattern = "^\d+$"
                    if re.match(pattern, ma):
                        ma = f"ma{ma}"
                    if ma in df.columns:
                        through_cond = (df["Low"] < df[f"{ma}"]) & (
                            df[f"{ma}"] < df["Close"]
                        )
                        cond = ac_cond & through_cond

                        # sun 이면 너비 cond 추가.  ## 좁은상태에서 돌파했다면 전일거래량보다크기만 해도 조건완성으로 볼까.???????????
                        pattern = "^sun.+$"  # sun_width
                        if re.match(pattern, ma):
                            print(ma, "조건이전 개수:", sum(cond))
                            cond_ext = df["sun_width"] < 50  #  sun_width
                            cond = cond & cond_ext
                            print(ma, "조건이후 개수:", sum(cond))

                        # upp 이면 너비와 편평도 추가.  # coke_width_60 , ma-편평도 이 모든 조건이 만족한다면 거래량은 무시해도 될까.?
                        if re.match("^upper.+$", ma):
                            print(ma, "조건이전 개수:", sum(cond))
                            if re.match("^upper.+60$", ma):
                                coke_width_col = "coke_width_60"
                            elif re.match("^upper.+240$", ma):
                                coke_width_col = "coke_width_240"
                            # 편평도 조건
                            # upper = ma 그대로 사용. 실제ma 최근20일 방향도 체크하기. - 0.02 이상.?
                            flat_rate = pd.concat(
                                [df[ma].pct_change(20), df[ma].pct_change(10)], axis=1
                            ).mean(axis=1)
                            cond_ext1 = flat_rate < 0.02

                            pattern = "\d+"
                            ma_text = f"ma{re.findall(pattern , ma)[-1]}"
                            # ma_change_rate = pd.concat([df[ma_text].pct_change(20),df[ma_text].pct_change(10)], axis=1).mean(axis=1)
                            ma_change_rate = df[ma_text].pct_change(20)
                            cond_ext2 = ma_change_rate > -0.01
                            bb_cond = cond_ext1 & cond_ext2

                            ## 너비조건
                            # cond_width = True
                            cond_width = df[coke_width_col] <= 60

                            cond = cond & bb_cond & cond_width

                            print(ma, "조건이후 개수:", sum(cond))

                        cond_data = cond.loc[cond]
                        if len(cond_data):
                            new_mas.append(ma)
                            through_cond_ls.append(cond_data.index)

            result_dict = dict(zip(new_mas, through_cond_ls))

        return result_dict

    def is_ac_today(self, vervose=False):
        result = False
        if self._ac_info["ac"][-1] == self.last_date:
            result = True
        return result

    def is_ac_through_sun_today(self):
        result = False
        key = "sun_max"
        if key in self._ac_info.keys():
            if self._ac_info[key][-1] == self.last_date:
                result = True
        return result

    def is_ac_through_coke60_today(self):
        result = False
        key = "upper_bb_60"
        if key in self._ac_info.keys():
            if self._ac_info[key][-1] == self.last_date:
                result = True
        return result

    def is_ac_through_coke240_today(self):
        result = False
        key = "upper_bb_240"
        if key in self._ac_info.keys():
            if self._ac_info[key][-1] == self.last_date:
                result = True
        return result

    def __repr__(self):
        return f"AC class"


class BB:
    """
    볼린져 상태
    bb_upper, bb_lower, bb_width
    (너비 , 기울기, 변화율(상중하), 방향(상중하), 값(상중하)
    """

    def __init__(self, df, ma=240, start=None, end=None):

        # start=None, end=None
        self.__start = start
        self.__end = end
        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        self.exist = False
        self.cur_width = None
        self.cur_upper_value = None
        self.cur_middle_value = None
        self.cur_lower_value = None

        self.upper_direction = None  # 방향.
        self.inclination20 = None
        self.inclination10 = None
        self.ma = ma
        self.__get_line(df, ma)
        self.__get_info()

    def __get_line(self, df, ma):
        arr = np.array([ma])
        used_ma = arr[arr < len(df)]
        if used_ma:
            self.exist = True
            self.upper, self.middle, self.lower = talib.BBANDS(df["Close"], ma, 2, 2)
            self.upper.name, self.middle.name, self.lower.name = (
                f"upper",
                f"middle",
                f"lower",
            )
            self.line_upper = Line(self.upper)
            self.line_middle = Line(self.middle)
            self.line_lower = Line(self.lower)

            self.two_line = self.line_upper - self.line_lower

    def __get_info(self):

        if self.exist:
            self.cur_width = round(self.two_line.width.iloc[-1], 1)
            self.cur_upper_value = int(self.upper.iloc[-1])
            self.cur_middle_value = int(self.middle.iloc[-1])
            self.cur_lower_value = int(self.lower.iloc[-1])

            self.upper_direction = (
                "up" if self.upper.iloc[-2] < self.upper.iloc[-1] else "down"
            )  # 방향.
            self.upper_inclination20 = self.line_upper.inclination20_value
            self.upper_inclination10 = self.line_upper.inclination10_value

            self.lower_direction = (
                "up" if self.upper.iloc[-2] < self.upper.iloc[-1] else "down"
            )  # 방향.
            self.lower_inclination20 = self.line_lower.inclination20_value
            self.lower_inclination10 = self.line_lower.inclination10_value

    def check_status(self, verbose=False):
        # 괜찮은상태인지 확인하는 로직.
        # 좀은상태 편평한데 뚫었다.
        pass

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def __repr__(self):
        return f"{self.ma} BB instance"


class Sun:
    """
    그물망상태,
    sun_max, sun_min, sun_width
    (너비, short, long 대비 치우침정도, 특정기간동안 평균 너비)
    """

    def __init__(self, df, start=None, end=None):
        # sun_width
        # sun_array long ma 에 비해서 위 아래 어느쪽으로 치우쳐져있나.
        # sun_width_avg_priod

        # start=None, end=None
        self.__start = start
        self.__end = end
        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        ## sun
        sun_df = pd.DataFrame()
        # for i in range(10,max(mas)+1,10):
        for i in range(
            10, min(len(df), 200) + 1, 10
        ):  ## 최고 200까지만 보기로 함. ??????
            sun_df[i] = talib.MA(df["Close"], i)

        s_max = sun_df.apply(lambda x: max(x[sun_df.columns]), axis=1)
        s_min = sun_df.apply(lambda x: min(x[sun_df.columns]), axis=1)
        s_max.name, s_min.name = "max", "min"
        self.line_max = Line(s_max)
        self.line_min = Line(s_min)
        ## 데이터 적은 종목을 위한 예외처리
        try:
            self.two_line = self.line_max - self.line_min

            self.width = round(self.two_line.width.iloc[-1], 1)
            self.cur_max_value = int(s_max.iloc[-1])
            self.cur_min_value = int(s_min.iloc[-1])
        except:
            pass
    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def __repr__(self):
        return f"SUN instance"


class Rsi:

    def __init__(
        self, df, period=11, low_value=40, high_value=70, start=None, end=None
    ):

        # start=None, end=None
        self.__start = start
        self.__end = end
        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        self._period = period
        self._low_value = low_value
        self._high_value = high_value

        self.data = talib.RSI(df["Close"], self._period)
        self.data.name = "rsi"
        self.line_rsi = Line(self.data)
        self.current_value = self.line_rsi.df_curve[self.line_rsi.name].iloc[-1]

    def is_rsi_w(self, verbose=False):

        # w 이고
        cond_v = (len(self.line_rsi.df_last_low_points) > 0) and (
            self.line_rsi.df_last_low_points.index[-1]
            == self.line_rsi.df_all_low_points.index[-1]
        )

        # w 최근두번중 한번 low_value 에 빠졌다 나온것
        cond_value = (
            sum(
                self.line_rsi.df_last_low_points[f"{self.line_rsi.name}_변곡점"][-2:]
                < self._low_value
            )
            > 0
        ) if len(self.line_rsi.df_last_low_points) > 0 else False

        # 현재는 low_value 위로 올라온것.
        cond_current_value = self.current_value > self._low_value

        cond = all([cond_v, cond_value, cond_current_value])
        if verbose:
            print(
                f"지속일 : {len(self.data.loc[self.line_rsi.df_last_low_points.index[-1]:])} candle"
            )
            print(f"현재값 : {self.current_value:,.1f}")
            print(f"기준값 : {self._low_value:,.1f}")
            print(
                f"최근 최저점값 : {self.line_rsi.df_last_low_points['rsi_변곡점'].iloc[-2:].min():,.1f}"
            )

        # cond = all([cond_v , cond_value])
        return cond

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def plot(self):
        ax = self.line_rsi.df_curve[f"{self.line_rsi.name}"].plot()
        ax.hlines(
            [self._low_value, self._high_value],
            self.line_rsi.df_curve.index[0],
            self.line_rsi.df_curve.index[-1],
            colors="red",
        )
        return ax

    def __repr__(self):
        return f"RSI instance"


class Ac:

    def __init__(self, df, pre_vol_rate=2, ma20vol_rate=2, start=None, end=None):

        # start=None, end=None
        self.__start = start
        self.__end = end
        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        self.df = df
        self._pre_vol_rate = pre_vol_rate
        self._ma20vol_rate = ma20vol_rate
        self.last_date = self.df.index[-1]

        if len(self.df) > 20:
            self.vol20 = Volume(self.df, 20)

        if len(self.df) > 240:
            self.vol240 = Volume(self.df, 240)

        self.ac_dates = self._get_ac_date(
            pre_vol_rate=self._pre_vol_rate, ma20vol_rate=self._ma20vol_rate
        )  ## default
        self.ac_dates_big = self._get_ac_date(pre_vol_rate=8, ma20vol_rate=8)

    def _get_ac_date(self, pre_vol_rate, ma20vol_rate):

        if len(self.df):
            handycap = 3 / 4
            cond_pre_plus = self.df["Close"] > self.df["Close"].shift(1)
            cond_plus = self.df["Close"] > self.df["Open"]
            cond_전일대비거래량비율 = (
                self.df["Volume"] > self.df["Volume"].shift(1) * pre_vol_rate
            )
            cond_전전일대비거래량비율 = (
                self.df["Volume"] > self.df["Volume"].shift(2) * pre_vol_rate
            )
            cond_전일대비거래량비율_handycap = (
                self.df["Volume"] > self.df["Volume"].shift(1) * pre_vol_rate * handycap
            )
            cond_전전일대비거래량비율_handycap = (
                self.df["Volume"] > self.df["Volume"].shift(2) * pre_vol_rate * handycap
            )

            cond_20평균대비거래량비율 = (
                (self.df["Volume"] > self.vol20.ma_vol * ma20vol_rate)
                if "vol20" in dir(self)
                else False
            )
            cond_240평균대비거래량비율 = (
                (self.df["Volume"] > self.vol240.ma_vol * ma20vol_rate * 1.5)
                if "vol240" in dir(self)
                else False
            )

            ac_cond1 = cond_pre_plus & (
                cond_전일대비거래량비율 | cond_전전일대비거래량비율
            )

            ac_cond2_1 = cond_pre_plus & cond_20평균대비거래량비율
            ac_cond2 = (
                cond_pre_plus & (cond_20평균대비거래량비율 | cond_240평균대비거래량비율)
                if "vol240" in dir(self)
                else ac_cond2_1
            )

            # 전전일과 전일 조건 모두 만족할때. default의 3/4 적용.
            ac_cond3 = cond_plus & (
                cond_전일대비거래량비율_handycap & cond_전전일대비거래량비율_handycap
            )

            ac_cond = ac_cond1 | ac_cond2 | ac_cond3

            cond_data = ac_cond.loc[ac_cond]

        return cond_data.index

    def is_ac_today(self, n봉전=0, verbose=False):
        n = -(n봉전) - 1
        result = False
        if self.df.index[n] in self.ac_dates:
            result = True
        return result

    def __repr__(self):
        return f"AC instance"

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]


class Volume:
    """
    volume 분석데이터 ab_v
    """

    def __init__(self, df, ma=20, big_v_rate=5, start=None, end=None):

        # start=None, end=None
        self.__start = start
        self.__end = end
        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        self.exist = False
        self.big_v_rate = big_v_rate
        self.ma = ma
        self.df = df
        self.data = self.df["Volume"]
        if len(df) > ma:
            self.exist = True
            self.ma_vol = talib.MA(self.df["Volume"], ma)
            self.ma_vol.name = f"{ma}ma"
            self.line = Line(self.ma_vol)
            ma_cond = self.df["Volume"] >= self.ma_vol * big_v_rate
        else:
            ma_cond = False
        pre_v_cond = self.df["Volume"] >= self.df["Volume"].shift(1) * big_v_rate

        self.big_volume_df = df.loc[ma_cond | pre_v_cond]

    def remove_extra_value(self, s, threshold=2.5):
        """
        s 받아서 특이한값 제거하는함수. 평균낼때 이 함수로 거른담에 평균내기.. .
        """
        z_score = (s - s.mean()) / s.std()
        s_cleaned = s[np.abs(z_score) < threshold]
        return s_cleaned

    def is_ab_by_ma(self, ma=20, period=50, verbose=False):
        rate = 1.2
        # pass ## ma big_V 에 의한 ab 분리
        if len(self.df) < period:
            return False
        result_bool = False
        period_date = self.df.index[-period]
        ma20 = Ma(self.df, ma=ma)
        v_df = ma20.df_all_low_points
        v_df1 = v_df.loc[period_date:]
        if len(v_df1):
            the_date = v_df.index[-1]
            a_vol_data = self.df.loc[:the_date, "Volume"][-20:-1]
            a_vol_avg = self.remove_extra_value(a_vol_data).mean()  ## 저점날짜 제외
            b_vol_data = self.df.loc[the_date:, "Volume"][1:]
            b_vol_avg = self.remove_extra_value(b_vol_data).mean()  ## 저점날짜 제외.
            last5_vol_data = self.df.loc[the_date:, "Volume"][-5:]
            last5_vol_avg = self.remove_extra_value(last5_vol_data).mean()

            result_bool = (a_vol_avg * rate <= b_vol_avg) & (a_vol_avg < last5_vol_avg)
            result_rate = round(b_vol_avg / a_vol_avg, 1)

            (
                print(
                    f"{the_date} ma20:{result_rate}배 , a:{a_vol_avg:,.0f}, b:{b_vol_avg:,.0f}, last5:{last5_vol_avg:,.0f}"
                )
                if verbose
                else None
            )
        return result_bool

    def is_ab_by_big_v(self, period=50, verbose=False):
        rate = 1.2
        if len(self.df) < period:
            return False
        result_bool = False
        period_date = self.df.index[-period]
        big_v = (self.df["Volume"] > self.ma_vol * self.big_v_rate) & (
            self.df["Open"].shift(1) < self.df["Open"]
        )
        big_v = big_v.loc[big_v]
        big_v = big_v.loc[period_date:]
        if len(big_v):
            the_date = big_v.index[0]
            a_vol_data = self.df.loc[:the_date, "Volume"][-20:-1]
            a_vol_avg = self.remove_extra_value(a_vol_data).mean()  ## 저점날짜 제외
            b_vol_data = self.df.loc[the_date:, "Volume"][1:]
            b_vol_avg = self.remove_extra_value(b_vol_data).mean()  ## 저점날짜 제외.
            last5_vol_data = self.df.loc[the_date:, "Volume"][-5:]
            last5_vol_avg = self.remove_extra_value(last5_vol_data).mean()

            result_bool = (a_vol_avg * rate <= b_vol_avg) & (a_vol_avg < last5_vol_avg)
            result_rate = round(b_vol_avg / a_vol_avg, 1)

            ## plot 때 사용하는 기간별 평균거래량 표시.
            if result_bool:
                self.a_vol_avg = a_vol_avg
                self.a_vol_data = a_vol_data
                self.b_vol_avg = b_vol_avg
                self.b_vol_data = b_vol_data
                self.last5_vol_avg = last5_vol_avg
                self.last5_vol_data = last5_vol_data
                self.ab_vol_rate = result_rate

            (
                print(
                    f"{the_date} big:{result_rate}배 , a:{a_vol_avg:,.0f}, b:{b_vol_avg:,.0f}, last5:{last5_vol_avg:,.0f}"
                )
                if verbose
                else None
            )
            # print(the_date, 'big', result_rate) if verbose else None
        return result_bool

    def is_ab(self, period=50, verbose=False):
        return any(
            [
                self.is_ab_by_big_v(period=period, verbose=verbose),
                self.is_ab_by_ma(period=period, verbose=verbose),
            ]
        )

    def plot(self):
        ax = self.ma_vol.plot(kind="bar")
        return ax

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def __repr__(self):
        return f"Volume instance"


class Candle:
    """
    최근 바닥캔들, 상투캔들 여부 체크. (주봉일때 유용.)
    """

    def __init__(self, df: pd.DataFrame, start=None, end=None):

        # start=None, end=None
        self.__start = start
        self.__end = end
        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        self.df = df
        self.plot_df = df.iloc[-5:, :].copy()

        self.week_status, self.week_df = self.is_바닥캔들_status()
        self.month_status, self.month_df = self.is_바닥캔들_status(option="M")

    def __candle_status(self, o, h, l, c):
        """
        캔들상태
        """
        dic = {}
        all_len = h - l
        if all_len == 0:
            head_rate = 0
            body_rate = 0
            tail_rate = 0
        else:
            head_len = h - max(o, c)
            body_len = max(o, c) - min(o, c)
            tail_len = min(o, c) - l
            head_rate = round(head_len / all_len * 100, 0)
            body_rate = round(body_len / all_len * 100, 0)
            tail_rate = round(tail_len / all_len * 100, 0)

        ## 비율이기 때문에 크기에 대한 수치가 필요함. ....

        dic["up_tail"] = head_rate
        dic["body"] = body_rate
        dic["dow_tail"] = tail_rate

        return dic

    def get_candle_info(self, n봉전=0):

        n_for_df = -(n봉전 + 1)
        data = self.df.iloc[n_for_df]  #

    
        c_data = self.__candle_status(
            data["Open"], data["High"], data["Low"], data["Close"]
        )
    
        return c_data

    def get_short_candle_date(
        self, n: int = 30, quantile_rate: float = 0.25, verbose=False
    ) -> list[datetime]:
        """
        n일 이내
        quantile_rate 0 ~ 1
        """
        data = self.df.apply(
            lambda x: self.__candle_status(x["Open"], x["High"], x["Low"], x["Close"])[
                "body"
            ],
            axis=1,
        )[-n:]
        short_dates = data.loc[data < data.quantile(quantile_rate)].index
        (
            print(
                f"최근 {n}일간 short_candle {len(short_dates)}개 (quantile_rate:{quantile_rate})"
            )
            if verbose
            else None
        )
        return short_dates

    def is_today_short_candle(self, verbose=False) -> bool:
        result = False
        short_dates = self.get_short_candle_date(verbose=verbose)
        if not short_dates.empty:
            result = True if self.df.index[-1] == short_dates[-1] else False
        return result

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    def is_바닥캔들_status(self, option="W", verbose=False) -> dict:
        """
        return : dict (주봉에 사용하기.)
        result, case, info
        option : 'W','M'
        """
        if option == "W":
            df = self.df.resample("W").agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            )
        elif option == "M":
            df = self.df.resample("ME").agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            )
        elif option == "":
            df = self.df

        # temp_df = df.iloc[-5:,:4]
        temp_df = df[["Open", "High", "Low", "Close"]].tail(5)

        dic = {}
        # 111
        try:
            first_candle = temp_df.iloc[-3].to_dict()
            second_candle = temp_df.iloc[-2].to_dict()
            third_candle = temp_df.iloc[-1].to_dict()
            dic["111"] = {
                "1": first_candle,
                "2": second_candle,
                "3": third_candle,
            }
        except:
            pass

        # 121
        try:
            first_candle = temp_df.iloc[-4].to_dict()
            second_candle = {
                "Open": temp_df.iloc[-3:-1]["Open"].iloc[0],
                "High": temp_df.iloc[-3:-1]["High"].max(),
                "Low": temp_df.iloc[-3:-1]["Low"].min(),
                "Close": temp_df.iloc[-3:-1]["Close"].iloc[-1],
            }
            third_candle = temp_df.iloc[-1].to_dict()
            dic["121"] = {
                "1": first_candle,
                "2": second_candle,
                "3": third_candle,
            }
        except:
            pass

        # 112
        try:
            first_candle = temp_df.iloc[-4].to_dict()
            second_candle = temp_df.iloc[-3].to_dict()
            third_candle = {
                "Open": temp_df.iloc[-2:]["Open"].iloc[0],
                "High": temp_df.iloc[-2:]["High"].max(),
                "Low": temp_df.iloc[-2:]["Low"].min(),
                "Close": temp_df.iloc[-2:]["Close"].iloc[-1],
            }
            dic["112"] = {
                "1": first_candle,
                "2": second_candle,
                "3": third_candle,
            }
        except:
            pass

        # 131
        try:
            first_candle = temp_df.iloc[-5].to_dict()
            second_candle = {
                "Open": temp_df.iloc[-4:-1]["Open"].iloc[0],
                "High": temp_df.iloc[-4:-1]["High"].max(),
                "Low": temp_df.iloc[-4:-1]["Low"].min(),
                "Close": temp_df.iloc[-4:-1]["Close"].iloc[-1],
            }
            third_candle = temp_df.iloc[-1].to_dict()
            dic["131"] = {
                "1": first_candle,
                "2": second_candle,
                "3": third_candle,
            }
        except:
            pass

        # 122
        try:
            first_candle = temp_df.iloc[-5].to_dict()
            second_candle = {
                "Open": temp_df.iloc[-4:-2]["Open"].iloc[0],
                "High": temp_df.iloc[-4:-2]["High"].max(),
                "Low": temp_df.iloc[-4:-2]["Low"].min(),
                "Close": temp_df.iloc[-4:-2]["Close"].iloc[-1],
            }
            third_candle = {
                "Open": temp_df.iloc[-2:]["Open"].iloc[0],
                "High": temp_df.iloc[-2:]["High"].max(),
                "Low": temp_df.iloc[-2:]["Low"].min(),
                "Close": temp_df.iloc[-2:]["Close"].iloc[-1],
            }

            dic["122"] = {
                "1": first_candle,
                "2": second_candle,
                "3": third_candle,
            }

        except:
            pass

        ### 여기까지는 경우의 수 범위 지정.

        ## 실제 바닥캔들인지 확인하기.
        result_dic = {}
        ls = []
        info = []
        if len(dic):
            for key, value in dic.items():
                첫째봉_음봉조건 = value["1"]["Open"] > value["1"]["Close"]  # 1음봉
                두번째봉_아래꼬리조건 = value["2"]["Close"] > value["2"]["Low"]  # 2단봉
                두번째봉_고가조건 = value["1"]["High"] > value["2"]["High"]  # 3양봉
                세번째봉_전고돌파조건 = (
                    max(value["2"]["Close"], value["2"]["Open"]) < value["3"]["Close"]
                )  # 2캔들보다 3종가가 큼.
                세번째봉_양봉조건 = value["3"]["Open"] < value["3"]["Close"]  # 3 양봉

                if all(
                    [
                        첫째봉_음봉조건,
                        두번째봉_아래꼬리조건,
                        두번째봉_고가조건,
                        세번째봉_전고돌파조건,
                        세번째봉_양봉조건,
                    ]
                ):

                    ls.append(key)

                    low = self.df["Low"].min()
                    try:
                        ma20_value = self.df.loc[self.df["Low"].idxmin(), "ma20"]
                        이격도_20_저가 = round(low / ma20_value * 100, 1)
                    except:
                        이격도_20_저가 = np.nan
                    try:
                        ma60_value = self.df.loc[self.df["Low"].idxmin(), "ma60"]
                        이격도_60_저가 = round(low / ma60_value * 100, 1)
                    except:
                        이격도_60_저가 = np.nan

        if len(ls):
            result_dic["result"] = True
            result_dic["case"] = ls
            result_dic["info"] = {
                "이격도_20_저가": 이격도_20_저가,
                "이격도_60_저가": 이격도_60_저가,
            }

            # f = self.plot(df)
            # show(f)

        else:
            result_dic["result"] = False
            result_dic["case"] = []
            result_dic["info"] = {"이격도_20_저가": np.nan, "이격도_60_저가": np.nan}

        print(result_dic) if verbose else None

        return result_dic["result"], temp_df

    def plot(self, option="W", recent_high=None, title=""):
        """
        가격데이터(데이터프레임)을 캔들차트로 그립니다.
        * df: 데이터프레임
        * start(기본값: None):
        * end(기본값: None)
        * recent_high: 이전 고점 표시 여부 혹은 N일전까지 고점 표시 (-1 이면 어제까지 고점표시)
        """

        if option == "W":
            df = self.df.resample("W").agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            )
        elif option == "M":
            df = self.df.resample("M").agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            )
        elif option == "":
            df = self.df

        df = df.iloc[-10:, :4]

        df["ma3"] = talib.MA(df["Close"], 3)
        df["ma5"] = talib.MA(df["Close"], 5)
        # 가격 그리기
        inc = df.Close > df.Open
        dec = df.Open > df.Close

        x = np.arange(len(df))
        pp = figure(
            title=str(title),
            plot_width=750,
            plot_height=300,
            min_width=750,
            min_height=300,
            x_range=(max(1, len(df) - 15), max(15, len(df))),
        )
        pp.segment(x[inc], df.High[inc], x[inc], df.Low[inc], color="red")
        pp.segment(x[dec], df.High[dec], x[dec], df.Low[dec], color="blue")
        pp.vbar(
            x[inc], 0.8, df.Open[inc], df.Close[inc], fill_color="red", line_color="red"
        )
        pp.vbar(
            x[dec],
            0.8,
            df.Open[dec],
            df.Close[dec],
            fill_color="blue",
            line_color="blue",
        )
        pp.yaxis[0].formatter = NumeralTickFormatter(format="0,0")
        pp.xaxis.visible = False

        (
            pp.line(
                x, df["ma3"].reset_index(drop=True), line_width=1, line_color="black"
            )
            if len(df["ma3"])
            else None
        )
        (
            pp.line(x, df["ma5"].reset_index(drop=True), line_width=2, line_color="red")
            if len(df["ma5"])
            else None
        )

        plot_list = [[pp]]

        p = gridplot(plot_list)
        # show(p)
        return p

    def __repr__(self):
        return f"Candle instance"


class PriceLevel:
    """
    매물대
    """

    def __init__(self, df, period=120):
        """
        pricelevel1 : 첫번째매물대
        """
        self.period = period
        the_values = self._get_price_level(df, period=120) # 6개월
        ## 유동적으로 속성 지정. 
        names= ['first','second', 'third']
        for i in range(len(the_values)):
            setattr(self, names[i], the_values[i])

    def _get_price_level(self, df, parts=10, period=240):
        """
        df : ohlcv , parts : 구분
        return : list 240거래일기준 가장많은 매물대 1, 2위 가격.
        """
        try:
            df = df[-period:].copy()
            self.start_date , self.end_date= df.index[0], df.index[-1] # 범위
            df = df[["Close", "Open", "High", "Low", "Volume"]]
            all_v = df["Volume"].sum()
            df["rate_v"] = df["Volume"] / all_v
            # df['mprice']= (df['High'] + df['Low']) /2
            df["mprice"] = (df["High"] + df["Low"] + df["Open"] + df["Close"]) / 4
            max_price = df["High"].max()
            min_price = df["Low"].min()
            bins = np.linspace(min_price, max_price, parts)
            labels = [str(int((bins[i] + bins[i + 1]) / 2)) for i in range(len(bins) - 1)]
            df["bin"] = pd.cut(df["mprice"], bins=bins, labels=labels)
            result = (
                df.groupby("bin", observed=True)
                .sum()["rate_v"]
                .sort_values(ascending=False)
            )
            return [int(index) for index in result.index[0:2]]

        except:
            return None, None


class Chart:

    def __init__(
        self,
        df: pd.DataFrame = None,
        mas=None,
        start=None,
        end=None,
        n봉=0,
        *args,
        **kwargs,
    ):
        """
        df : kind ohlcv,
        일봉, 주봉 : mas = [3,5,10,20,60,120,240] default
        분봉 : mas = [1,10,20,40,60,120,240]
        월봉 : mas = [1,3,10,20]
        """

        if df is None:
            print("download needs")
            return
        # start=None, end=None
        self.__start = start
        self.__end = end
        if not self.__start is None and self.__start in df.index:
            df = df.loc[self.__start :]
        if not self.__end is None and self.__end in df.index:
            df = df.loc[: self.__end]

        self.df = df

        ## n봉전 데이터
        if n봉:
            self.df = df.iloc[:-(n봉)]
            print(f"n봉전 적용 {n봉} last_date : {self.df.index[-1]}")

        if len(kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        if mas is None:
            mas = [1, 3, 5, 10, 20, 60, 120, 240]

        ignore_cnt_dict = {
            1: 0,
            3: 1,
            5: 1,
            10: 2,
            20: 2,
            40: 2,
            60: 3,
            120: 4,
            240: 5,
        }
        ## ma setting
        if len(df):
            self.ma_arr = np.array(mas)
            self.ma_arr = list(self.ma_arr[self.ma_arr < len(df)])
            if self.ma_arr:
                for ma in self.ma_arr:
                    if ma in ignore_cnt_dict:
                        ignore_cnt = ignore_cnt_dict[ma]
                    else:
                        ignore_cnt = 1
                    setattr(
                        self,
                        f"ma{ma}",
                        Ma(
                            df,
                            ma,
                            start=self.__start,
                            end=self.__end,
                            ignore_cnt=ignore_cnt,
                        ),
                    )
        ## ma1 추가
        if not hasattr(self, "ma1"):
            setattr(self, "ma1", Ma(df, ma=1, start=self.__start, end=self.__end))

        self.vol = Volume(df, start=self.__start, end=self.__end)
        try:
            self.rsi = Rsi(
                df,
                period=11,
                low_value=40,
                high_value=70,
                start=self.__start,
                end=self.__end,
            )
        except Exception as e:
            print("rsi 생성실패", e)

        self.sun = Sun(df, start=self.__start, end=self.__end)
        self.bb60 = BB(df, ma=60, start=self.__start, end=self.__end)
        self.bb240 = BB(df, ma=240, start=self.__start, end=self.__end)
        self.candle = Candle(df, start=self.__start, end=self.__end)
        self.volume = Volume(df, start=self.__start, end=self.__end)
        self.volume_big = Volume(df, big_v_rate=8, start=self.__start, end=self.__end)
        self.ac = Ac(df, start=self.__start, end=self.__end)
        self.pricelevel = PriceLevel(df)

    def get_attr(self, start_except_word="__"):
        pattern = f"^{start_except_word}"
        return [item for item in dir(self) if re.match(pattern, item)]

    ########################################   기술적 분석 start    ####################################

    def is_w_a_short(self, ma=3, with_vol=True, verbose=False):
        """
        (w or wa) and (short_candle)  저점부터.
        보완 : with_vol 이면 거래량 줄어든거까지 확인한다.

        """

        ma_instance: Ma = getattr(self, f"ma{ma}" if isinstance(ma, int) else ma)
        cond_w = ma_instance.is_w(verbose=verbose)
        cond_wa = ma_instance.is_wa(verbose=verbose)
        cond_short = self.candle.is_today_short_candle(verbose=verbose)

        if with_vol and len(ma_instance.df_all_low_points.index) >= 2:
            the_date = ma_instance.df_all_low_points.index[-2]
            ma_up_data = self.volume.data > self.volume.ma_vol
            check_data = ma_up_data.loc[the_date:]
            vol_cond = (
                sum(check_data) > 0 and sum(check_data[-2:]) <= 1
            )  ## 전저점기준으로 평균거래량 이상인게 있고 -1일 또는 -2 일 저점이있는경우.
        else:
            the_date = []
            vol_cond = True

        (
            print(
                f"cond_w {cond_w} cond_wa {cond_wa} cond_short {cond_short} with_vol {vol_cond} the_date: {the_date}"
            )
            if verbose
            else None
        )
        return (cond_w | cond_wa) & cond_short & vol_cond

    def is_w20_3w(self, verbose=False):
        """
        보완점 : 20wa 인경우는 (3ma > 20ma) or (low > 20ma) 조건을 넣으면 좋다. (안착개념으로.)
        """
        result = False
        results = [hasattr(self, item) for item in ["ma20", "ma3"]]
        if all(results):
            ma3: Ma = getattr(self, "ma3")
            ma20: Ma = getattr(self, "ma20")
            result = ma3.is_w(verbose=verbose) and (
                ma20.is_w(verbose=verbose) or ma20.is_wa(verbose=verbose)
            )

        return result

    # ab파동,
    def is_ab(self, ma: int = 3, verbose=False):
        """
        알아야할점 : 최소 ab기간이어야 하고 . 가격은 전저점 지키는 조건이다.
        """
        result = False
        ma_instance: Ma = getattr(self, f"ma{ma}" if isinstance(ma, int) else ma)
        result = ma_instance.is_ab_value(verbose=verbose) & ma_instance.is_ab_period(
            verbose=verbose
        )

        return result

    # ab거래량
    def is_ab_volume(self, verbose=False):
        """
        보완한점 : 앞뒤 거래량중 특이값을 제외한 값의 평균을 냄.
        보완해야할점. : ab이다가도 죽어가는것이 있다. 그래서 최근 n일 거래량도 기준이전 평균거래량보다 많아야하는걸로 하자.
        보완해야할점 : 간헐적 거래량이 나타날때.  맨 앞 거래량만 기준으로 삼는다. ( 복잡하다. )
        """
        return self.volume.is_ab(verbose=verbose)

    # 3w_ac
    def is_w3_ac(self, verbose=False):
        """
        w3이 아니고 w5 포함해야하는게 좋을듯.
        보완한 점 : ac에서 ma3 ma5 보다 ac 종가가 커야한다.

        """
        result = False
        try:
            ma3: Ma = getattr(self, "ma3")
            ma5: Ma = getattr(self, "ma5")
            ac: Ac = getattr(self, "ac")
            # ma line 자체에 데이터를 -n으로 넣어줌.
            cond1 = (
                ma3.is_w(verbose=verbose)
                or ma3.is_wa(verbose=verbose)
                or ma5.is_w(verbose=verbose)
                or ma5.is_wa(verbose=verbose)
            )
            cond2 = ac.is_ac_today(verbose=verbose)
            cond3 = (
                max(ma3.data.iloc[-1], ma5.data.iloc[-1]) < self.df["Close"].iloc[-1]
            )
            result = cond1 & cond2 & cond3
        except Exception as e:
            print("ma3정보가 없음 이 데이터는 분봉! ") if verbose else None
            return result

        (
            print(
                f"is_w(a): {cond1},  is_ac : {cond2} locate_cur_close_with_short_ma : {cond3}"
            )
            if verbose
            else None
        )
        return result

    def is_good_array(self, option="normal", verbose=False):
        """
        option : normal, perpect(완전개정배열.)
        """
        arr = np.array([60, 120, 240])
        check_mas = arr[arr < len(self.df)]
        datas = {f"ma{ma}": getattr(self, f"ma{ma}").current_value for ma in check_mas}
        print(datas) if verbose else None

        result_ls = [
            datas[a] > datas[b] for a, b in itertools.combinations(datas.keys(), 2)
        ]
        if option == "perpect":
            # 방향까지 전부 우상향인것.
            direction_datas = {
                f"ma{ma}": getattr(self, f"ma{ma}").current_direction
                for ma in check_mas
            }
            result_directions = [
                True if v == "up" else False for k, v in direction_datas.items()
            ]
            result = all(result_ls) & all(result_directions)
        else:
            result = all(result_ls)
        return result

    def is_bad_array(self, verbose=False):
        arr = np.array([60, 120, 240])
        check_mas = arr[arr < len(self.df)]
        datas = {f"ma{ma}": getattr(self, f"ma{ma}").current_value for ma in check_mas}
        print(datas) if verbose else None

        result_ls = [
            datas[a] <= datas[b] for a, b in itertools.combinations(datas.keys(), 2)
        ]
        return all(result_ls)

    ############################################             여기부터 아래로 확인하기.  이거 확실히 고치고 stock에서 다시 정의해야함. n봉전, with_ac 등 적극활용하기.  ####################################

    # sun_ac
    def is_sun_ac(self, sun_width=30, with_ac=True, n봉전이내=0, verbose=False):
        """
        ac 이고 꼬리 까지 확인하기.
        """

        for n봉전 in range(n봉전이내 + 1):
            n = -(n봉전) - 1
            cond_through = (
                self.df["Low"].iloc[n]
                < self.sun.two_line.line1.data.iloc[n - 1]
                < self.df["Close"].iloc[n]
            )
            cur_width = self.sun.two_line.width.iloc[n]
            cond_width = cur_width <= sun_width
            cond_up = self.df["Open"].iloc[n] < self.df["Close"].iloc[n]
            if with_ac:
                cond_ac = True if self.ac.is_ac_today(n봉전=n봉전) else False
                candle_rate = sum(
                    [
                        v
                        for k, v in self.candle.get_candle_info(n봉전=n봉전).items()
                        if k in ["body", "dow_tail"]
                    ]
                )
                if not candle_rate >= 65:
                    cond_ac = False

            else:
                cond_ac = True

            cond = all([cond_through, cond_width, cond_up, cond_ac])
            if cond:
                break

        if verbose:
            print("n봉전: ", n)
            print("Date: ", self.df.index[n])
            print(f"cond_through: {cond_through}")
            print(f"width: {cur_width}")
            print(f"cond_up: {cond_up}")
        return cond

    # coke_ac
    def is_coke_ac(
        self, coke_width=60, period=240, with_ac=True, n봉전이내=0, verbose=False
    ):
        """
        보완해야할점 : 60 up 은 240 안에 60 도 나란히 있을때만 적용시켜야함. 기울기값이 중요함.
        """
        result = False
        for n봉전 in range(n봉전이내 + 1):
            n = -(n봉전) - 1

            cond_ac = True
            if with_ac:
                cond_ac = True if self.ac.is_ac_today(n봉전=n봉전) else False
                candle_rate = sum(
                    [
                        v
                        for k, v in self.candle.get_candle_info(n봉전=n봉전).items()
                        if k in ["body", "dow_tail"]
                    ]
                )
                if not candle_rate >= 65:
                    cond_ac = False

            if period == 240:
                if "bb240" in dir(self):
                    # coke_width = 70
                    if "two_line" in dir(self.bb240):
                        cond_through = (
                            self.df["Low"].iloc[n]
                            < self.bb240.upper.iloc[n - 1]
                            < self.df["Close"].iloc[n]
                        )
                        cur_width = self.bb240.two_line.width.iloc[n]
                        cond_width = cur_width <= coke_width
                        result = all([cond_through, cond_width, cond_ac])
                        if result:
                            break

            elif period == 60:
                if "bb60" in dir(self):
                    # coke_width = 50
                    if "two_line" in dir(self.bb60):
                        cond_through = (
                            self.df["Low"].iloc[n]
                            < self.bb60.upper.iloc[n - 1]
                            < self.df["Close"].iloc[n]
                        )
                        cur_width = self.bb60.two_line.width.iloc[n]
                        cond_width = cur_width <= coke_width

                        result = all([cond_through, cond_width, cond_ac])
                        if result:
                            break

        print("n봉전: ", n) if verbose else None
        print("Date: ", self.df.index[n]) if verbose else None
        print(f"bb period : {period}") if verbose else None
        print(f"현재너비 : {cur_width}") if verbose else None
        print(f"기준너비: {coke_width}") if verbose else None
        print(f"돌파여부: {cond_through}") if verbose else None
        print(f"ac여부: {cond_ac}") if verbose else None

        print(f"result: {result}") if verbose else None

        return result

    def is_multi_through(self, with_ac=True, n봉전이내=0, verbose=False):
        """
        (60 20 through), (20 60 up1 ) ,   ac,
        """
        result = False
        exists_conds = [hasattr(self, item) for item in ["ma20", "ma60"]]
        if all(exists_conds):
            ma20: Ma = getattr(self, "ma20")
            ma60: Ma = getattr(self, "ma60")
            for n봉전 in range(n봉전이내 + 1):
                n = -(n봉전) - 1
                if pd.notna(ma20.data.iloc[n]) and pd.notna(ma60.data.iloc[n]):
                    ma20_current_value = ma20.data.iloc[n]
                    ma60_current_value = ma60.data.iloc[n]
                    cond_through1 = (
                        self.df["Low"].iloc[n]
                        < ma20_current_value
                        < self.df["Close"].iloc[n]
                    )
                    cond_through2 = (
                        self.df["Low"].iloc[n]
                        < ma60_current_value
                        < self.df["Close"].iloc[n]
                    )
                    cond_ac = True
                    print(f"20돌파: {cond_through1}") if verbose else None
                    print(f"60돌파: {cond_through2}") if verbose else None
                    if with_ac:
                        cond_ac = True if self.ac.is_ac_today(n봉전=n봉전) else False
                        print(f"ac: {cond_ac}") if verbose else None
                    result = cond_through1 & cond_through2 & cond_ac
                    if result:
                        print("n봉전: ", n) if verbose else None
                        break

        return result

    def is_alphabeta_status(self, cross_mas=[60, 120, 240], verbose=False):
        """
        장기이평과 ma20상태만 고려함.  +ma3 ma5 와 함께 사용해야함.
        보완한점. gc 된것중 낮은값보다 ma20 이 위에있어야 성립된다.
        보완해야할점 있긴한데 머라 설명하기 힘듬.
        """
        result = False
        ## ma20 is_w is_wa 인지 확인.
        if self.ma20.is_w():
            v1 = self.ma20.df_last_low_points.index[-2]
            v2 = self.ma20.df_last_low_points.index[-1]
            # v1 = self.ma20.df_last_low_points.index[0]
            # v2 = self.ma20.df_last_low_points.index[-1]
        elif self.ma20.is_wa():
            v1 = self.ma20.df_last_low_points.index[-1]
            v2 = self.ma20.data.index[-1]
        else:
            v1, v2 = None, None
            return result

        print("v1 :", v1) if verbose else None
        print("v2 :", v2) if verbose else None

        # 존재하는 ma str으로 변경해서 짝지어서 cross 가 있는지 확인하고 cross 날짜 구하기 ('ma60', 'ma120', )
        cross_arr_str = [
            (
                f"ma{item[0]}",
                f"ma{item[1]}",
            )
            for item in itertools.combinations(cross_mas, 2)
            if item[0] < item[-1]
        ]
        long_cross_dates = []
        for item in cross_arr_str:
            if all([True for i in item if i in dir(self)]):
                two_line = getattr(self, item[0]) - getattr(self, item[1])
                # two_line 중 gc만족하면 gc날짜가져오기.
                if two_line.cross_status == "정배열" and two_line.gc_date_ls:
                    long_cross_dates.append((item, two_line.gc_date_ls.iloc[-1]))

        # --> long_cross_dates = [ (('ma60', 'ma120'), Timestamp('2024-02-08 00:00:00')),
        # (('ma60', 'ma120'), Timestamp('2024-02-08 00:00:00')), ]
        print("long_cross_dates : ", long_cross_dates) if verbose else None

        ## cross 가 있으면 날짜비교해서 조건 만족하는지 확인.
        if long_cross_dates:
            cond_list = [item for item in long_cross_dates if v1 < item[-1] < v2]
            if cond_list:
                print("cond_list: ", cond_list) if verbose else None
                max_long_value = max(
                    list(
                        set(
                            [
                                getattr(self, item).data.iloc[-1]
                                for items in cond_list
                                for item in items[0]
                            ]
                        )
                    )
                )
                ma20_value = getattr(self, "ma20").data.iloc[-1]
                print("max_long_value : ", max_long_value) if verbose else None
                print("20_value : ", ma20_value) if verbose else None
                if max_long_value < ma20_value:
                    result = True

        return result

    # abc
    def is_abc(self, verbose=False):
        result = False
        try:
            # 큰거래중 4프로이상만 추출
            big_ac_df = self.volume_big.big_volume_df.loc[
                self.volume_big.big_volume_df["Change"] >= 0.04
            ]
        except:
            return result
        
        exist_df = pd.DataFrame()
        if self.is_w_a_short(with_vol=False):
            if len(self.ma3.df_last_low_points) >= 2:
                s_date = self.ma3.df_last_low_points.index[-2]
                e_date = self.ma3.df_last_low_points.index[-1]
            elif len(self.ma3.df_last_low_points) == 1:
                s_date = self.ma3.df_last_low_points.index[-1]
                e_date = self.ma3.data.index[-1]
            # print(f" s_date: {s_date} , e_date: {e_date} in is_abc func ")
            exist_df = big_ac_df.loc[s_date:e_date]
            if len(exist_df):
                last_big_vol_date = exist_df.index[-1]
                # abc 구하기.
                a = int(self.ma3.data[:last_big_vol_date][-3:].min())
                c = self.ma1.data[last_big_vol_date]
                b = int((a + c) / 2)
                최소기준 = int((a + b) / 2)
                최소기준 = b
                print(f"a,b,c : {a} {b} {c}") if verbose else None
                after_data_big = self.ma3.data.loc[
                    last_big_vol_date:
                ]  # 빅거래이후 ma3 추이.
                if not len(after_data_big.loc[after_data_big < 최소기준]):

                    result = True
                    (
                        print(
                            "최소기준아래로 떨어진데이터",
                            after_data_big.loc[after_data_big < 최소기준],
                        )
                        if verbose
                        else None
                    )
                    print("dates", exist_df.index) if verbose else None
                    print("cnt ", len(exist_df)) if verbose else None

        return result #, exist_df

    def is_coke_gcv(self, ma=3, bb_ma=240, with_ac=True, bb_width=50, verbose=False):
        """
        bb_ma : 60, 240
        추가하고 싶은것. with_ext_ac True 이면 gcv 사이에 bb를 뚫는 ac가 존재까지 조건으로 본다.

        end_date = two.last_cross_date
        start_date =  s.chart_d.ma3.df_last_low_points.loc[:end_date].index[-1]
        print(start_date, end_date)

        s.chart_d.volume.big_volume_df.loc[start_date: end_date]

        bb_width 는 with_ac 가 True 일때만 적용.


        """
        # upper 편평도 확인. 후 upper와 ma3 체크. 후 diff 로 low high checking
        result = False
        try:
            bb_instance = getattr(self, f"bb{bb_ma}")
            line_upper = bb_instance.line_upper
            short_ma_line = getattr(self, f"ma{ma}")
            two = short_ma_line - line_upper

            ac_cond = True
            cond_width = True
            if with_ac:
                try:
                    end_date = two.last_cross_date
                    start_date = short_ma_line.df_last_low_points.loc[:end_date].index[
                        -1
                    ]
                    # big_vol_df = self.volume.big_volume_df.loc[start_date: end_date]
                    ac_dates = self.ac.ac_dates[
                        (self.ac.ac_dates >= start_date)
                        & (self.ac.ac_dates <= end_date)
                    ]

                    if len(ac_dates):
                        cur_width = bb_instance.two_line.width.loc[ac_dates[-1]]
                        cond_width = True if bb_width >= cur_width else False
                        print("cur_width in ac_dates: ", cur_width) if verbose else None

                    print("ac dates: ", ac_dates) if verbose else None
                    ac_cond = True if len(ac_dates) else False
                except:
                    ac_cond = False

            if two.is_gcv(verbose=verbose) and ac_cond and cond_width:
                result = True
        except Exception as e:
            print(e, f"data_cnt: {len(self.df)}")
        return result

    # sun_gcv
    def is_sun_gcv(self, ma=3, with_ac=True, verbose=False):
        result = False
        try:
            line_max = getattr(self, f"sun").line_max
            short_ma_line = getattr(self, f"ma{ma}")
            two = short_ma_line - line_max

            ac_cond = True
            if with_ac:
                try:
                    end_date = two.last_cross_date
                    start_date = short_ma_line.df_last_low_points.loc[:end_date].index[
                        -1
                    ]
                    # big_vol_df = self.volume.big_volume_df.loc[start_date: end_date]
                    ac_dates = self.ac.ac_dates[
                        (self.ac.ac_dates >= start_date)
                        & (self.ac.ac_dates <= end_date)
                    ]

                    # width

                    print("ac dates: ", ac_dates) if verbose else None
                    ac_cond = True if len(ac_dates) else False
                except:
                    ac_cond = False

            if two.is_gcv(verbose=verbose) and ac_cond:
                result = True
        except Exception as e:
            print(e)
        return result

    def is_w_with_ext_ac(self, s_ma_nm="ma3", l_ma_nm="ma240"):
        """
        l_ma_nm : ma60, ma240, upper, sun_max ...
        """
        pass

    def is_rsi(self, short_ma=3, option="new_phase", verbose=False):
        """
        보완해야할점. 차트에서는 정배열이어야함 또는 new_phase,
        option : new_phase, good_array, 'all', 'any'
        """
        short_ma_str = f"ma{short_ma}"
        result = False

        if option == "new_phase":
            option_cond = self.is_new_phase(short_ma=short_ma, verbose=verbose)
            print("new_phase_cond : ", option_cond) if verbose else None
        elif option == "array_cond":
            option_cond = self.is_good_array(option="perfect")
            print("is_good_array : ", option_cond) if verbose else None
        elif option == "all":
            option_cond = self.is_new_phase(short_ma=short_ma, verbose=verbose) & self.is_good_array(
                "perfect"
            )
        elif option == "any":
            option_cond = self.is_new_phase(short_ma=short_ma, verbose=verbose) | self.is_good_array(
                "perfect"
            )
        else:
            print(
                "지정된 option 이 올바르지 않는다. 'new_phase', 'good_array', 'all', 'any' "
            )
            return False

        rsi_w_cond = self.rsi.is_rsi_w(verbose=verbose)

        if rsi_w_cond and option_cond:
            result = True
        return result

    def is_new_phase(self,short_ma : int = 3,  bb : int = 240, verbose=False) -> bool:
        """
        코크 방향이 하방이 아니고.
        코크돌파 경험이 있고(너비 60 이하에서)
        그 돌파시 종가보다 현재가가 높고.
        아직 3일선이 20선 위에있는 종목들
        """
        bb_text = f"bb{bb}"
        result = False
        if hasattr(self, bb_text):
            bb240 = getattr(self, bb_text)
            if hasattr(bb240, 'line_upper'):
                line_upper = getattr(bb240, 'line_upper')
            else:
                return False
        
        if "bb240" not in dir(self):
            print("have no bb240")
            return False
        if "line_upper" not in dir(self.bb240):
            print("have no bb240.line_upper") if verbose else None
            return False
            # cond_upper_direct = self.upper_inclination20 > -1
        
        cond_upper_direct = self.bb240.line_upper.inclination20_value > -1 if hasattr(line_upper, 'inclination20_value') else False
        if not cond_upper_direct:
            return False
            
        temp_df = self.df.iloc[-120:]

        upper_data = self.bb240.line_upper.data.iloc[-120:]

        cond_coke_up1 = (temp_df["Open"] < upper_data) & (temp_df["Close"] > upper_data)
        cond_coke_up2 = (temp_df["Close"].shift(1) < upper_data) & (
            temp_df["Close"] > upper_data
        )

        cond_coke_width = self.bb240.two_line.width <= 60

        # change_rate = temp_df['upper_bb'].pct_change(20)
        change_rate = self.bb240.line_upper.inclination20
        change_rate_cond = (-0.05 <= change_rate) & (change_rate <= 0.05)

        all_cond = (cond_coke_up1 | cond_coke_up2) & (
            cond_coke_width | change_rate_cond
        )

        short_ma_str = f"ma{short_ma}"
        # print('만족데이터',temp_df.loc[all_cond])
        if sum(all_cond):
            temp_price = temp_df.loc[all_cond].iloc[0]["Close"]  ## 돌파시 종가체크하기.
            cond_price = temp_df.iloc[-1]["Close"] > temp_price
            # print('돌파시 종가',temp_df.loc[all_cond].index[0], temp_price)
            # else:
            #     cond_price = False
            if hasattr(self, short_ma_str):
                s_ma = getattr(self, short_ma_str)
                try:
                    cond_current_status1 = (
                        s_ma.data.iloc[-1] >= self.ma60.data.iloc[-1]
                    )  ## 아직 3선이 60선위에 있는것만.
                except:
                    try:
                        cond_current_status1 = (
                            s_ma.data.iloc[-1] >= self.ma20.data.iloc[-1]
                        )
                    except:
                        print("ma 오류")
                        cond_current_status1 = False

                try:
                    cond_current_status2 = (s_ma.is_w() | self.ma5.is_w()) & (
                        s_ma.data.iloc[-1] >= self.ma240.data.iloc[-1]
                    )
                except:
                    cond_current_status2 = False

                cond_current_status = (
                    cond_current_status1 | cond_current_status2
                )  # 60선위에 있거나 240위에서 w를 그린것.

                cond_coke = cond_current_status & cond_upper_direct & cond_price

                if cond_coke:
                    result = True

        return result

    ########################################   기술적 분석 end    ####################################

    # self.ac 와 self.ma3 인스턴스를 이용해서 돌파후 v존 찾는 로직 만들어야함.  ac w 도 여기서 정리해보기.

    ##############      plot    @############################
    def df_to_plot_df(df: pd.DataFrame):
        df1 = df.copy()
        df1 = df1.reset_index(names="Date")
        df1["str_date"] = df1["Date"].dt.strftime("%Y.%m.%d")
        df1 = df1.set_idex("str_date")
        return df1

    def plot_bokeh(self, **kwargs):
        """
        kwargs : '상장주식수', '유동주식수',
        """
        df: pd.DataFrame = self.df.reset_index().copy()

        # rename
        rename_col = {
            "날짜": "date",
            "Date": "date",
            "시가": "open",
            "Open": "open",
            "OPEN": "open",
            "고가": "high",
            "High": "high",
            "HIGH": "high",
            "저가": "low",
            "Low": "low",
            "LOW": "low",
            "종가": "close",
            "Close": "close",
            "CLOSE": "close",
            "거래량": "volume",
            "Volume": "volume",
            "VOLUME": "volume",
            "등락률": "change",
            "Change": "change",
        }
        df.rename(columns=rename_col, inplace=True)

        df["date"] = pd.to_datetime(df["date"])
        # df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')

        ## p1 데이터 ################################################
        bb_period = 240
        if hasattr(self.bb240, "upper"):
            df["upper"] = self.bb240.upper
            df["lower"] = self.bb240.lower

        if hasattr(self.bb60, "upper"):
            df["upper60"] = self.bb60.upper
            df["lower60"] = self.bb60.lower

        if hasattr(self.sun, "line_max"):
            df["sun_max"] = self.sun.line_max.data
            df["sun_min"] = self.sun.line_min.data

        df["candle_color"] = [
            "#f4292f" if row["open"] <= row["close"] else "#2a79e2"
            for _, row in df.iterrows()
        ]

        ## ma 데이터 생성
        mas = [3, 20, 60]
        mas = self.ma_arr[1:]  # 1 제외한 3,5,10, 20, 60, 240 ,,,
        for ma in mas:
            df[f"ma{ma}"] = getattr(self, f"ma{ma}").data

        ## p2 데이터 ##############################################################3

        ## vol20ma
        if hasattr(self.vol, "ma_vol"):
            df["vol20ma"] = self.vol.ma_vol

        유동주식수 = kwargs["유동주식수"] if "유동주식수" in kwargs else None
        상장주식수 = kwargs["상장주식수"] if "상장주식수" in kwargs else None
        print("유동주식수", 유동주식수)
        print("상장주식수", 상장주식수)

        ## 거래량 color 지정 임시!
        ac_cond = df["volume"] > df["volume"].shift(1) * 2
        df["vol_color"] = ["#f4292f" if bl else "#808080" for bl in ac_cond]

        low_cond = df["volume"] < df["vol20ma"]  # 평균보다 작은조건
        df["vol_color"] = [
            "blue" if bl else value for value, bl in zip(df["vol_color"], low_cond)
        ]

        if 유동주식수:
            cond_유통주식수 = df["volume"] >= 유동주식수
            if sum(cond_유통주식수):
                print("1")
                df["vol_color"] = [
                    "#ffff00" if bl else value
                    for value, bl in zip(df["vol_color"], cond_유통주식수)
                ]

        if 상장주식수:
            cond_상장주식수 = df["volume"] >= 상장주식수
            if sum(cond_상장주식수):
                print("2")
                df["vol_color"] = [
                    "#800080" if bl else value
                    for value, bl in zip(df["vol_color"], cond_상장주식수)
                ]

        source = ColumnDataSource(df)

        ###### plot ####################################################
        plot_option = dict(
            width=800,
            height=300,
            background_fill_color="#ffffff",
        )
        all_tools = [
            "PanTool",
            "WheelZoomTool",
            "BoxZoomTool",
            "ResetTool",
            "SaveTool",
            "CrosshairTool",
            "HoverTool",
            "TapTool",
            "LassoSelectTool",
            "PolySelectTool",
            "ZoomInTool",
            "ZoomOutTool",
            "FreehandDrawTool",
            "EditTool",
            "BoxSelectTool",
        ]

        TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

        title = kwargs["title"] if "title" in kwargs else "Company1"
        p1 = figure(
            tools=TOOLS,
            **plot_option,
            title=title,
        )

        ## 캔들차트 그리기
        p1.segment(
            "index",
            "high",
            "index",
            "low",
            color="candle_color",
            source=source,
        )
        p1.vbar(
            "index",
            0.6,
            "open",
            "close",
            color="candle_color",
            line_width=0,
            source=source,
        )

        # x축 범위 설정 (마지막 데이터 포인트가 보이도록)
        p1.x_range.start = source.data["index"][-180]
        p1.x_range.end = (
            source.data["index"][-1] + 30
        )  # + pd.Timedelta(days=1)  # 마지막 데이터 포인트 이후로 범위 확장

        # ## 이동평균선 그리기

        colors = ["blue", "red", "green"]
        widths = [1, 2, 3]
        alphas = [0.7, 0.7, 0.6]

        for ma, color, width, alpha in zip(mas, colors, widths, alphas):
            str_ma = f"ma{ma}"
            p1.line(
                df.index,
                df[f"{str_ma}"],
                color=color,
                line_width=width,
                alpha=alpha,
                source=source,
            )

        # ## BB
        for data in ["upper", "lower"]:
            p1.line(
                "index",
                f"{data}",
                color="#f6b2b1",
                alpha=0.8,
                line_width=2,
                # legend_label='BB',
                source=source,
            )
        ## sun
        p1.varea(
            x="index",
            y1="sun_max",
            y2="sun_min",
            color="#bfd8f6",
            alpha=0.5,
            # legend_label='mesh',
            source=source,
        )

        ## 간단한 정보 Label로 넣기
        # 그래프에 간단한 텍스트 박스(Label) 추가
        plot_option["height"]
        # label = Label(
        #     x=plot_option['width'] * 0.8,
        #     y=plot_option['height'] * 0.8,  # 위치 조정 (픽셀 단위)
        #     text='''
        #     bb:240
        #     mesh :23
        #     ''',
        #     x_units='screen', y_units='screen',  # 픽셀 단위 지정
        #     text_font_size='12pt',
        #     text_color='navy',
        #     text_align='center',
        #     text_baseline='top',
        #     border_line_color='black',
        #     border_line_alpha =0.1,
        #     background_fill_color='white',
        # )

        # # Label을 plot에 추가
        # p1.add_layout(label)

        # ## p1 설정
        # p1.xaxis.major_label_orientation = 0.8 # radians
        # p1.x_range.range_padding = 0.05

        # map dataframe indices to date strings and use as label overrides
        x_lable_overrides = {
            i: date.strftime("%y-%m-%d") for i, date in zip(df.index, df["date"])
        }

        ## p1 layout 설정
        p1.xaxis.major_label_overrides = x_lable_overrides  # tick label override

        # # one tick per week (5 weekdays)
        # p1.xaxis.ticker = list(range(df.index[0], df.index[-1], 10))
        # p1.xaxis.axis_label = 'Date'
        # p1.yaxis.axis_label = 'Price'
        # # 그리드 설정
        # p1.xgrid.grid_line_color=None
        # p1.ygrid.grid_line_alpha=0.5

        ## p2 거래량 플롯
        # plot_option['height'] = plot_option['height'] * 0.4
        plot_option["height"] = 120
        p2 = figure(
            **plot_option,
            x_range=p1.x_range,
        )  # x_range를 공유해서 차트가 일치하게 만듦
        p2.vbar(
            x="index",
            top="volume",
            width=0.7,
            fill_color="vol_color",
            line_width=0,
            source=source,
        )
        ## 평균거래량
        p2.line(
            x="index",
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

        p2.xaxis.major_label_overrides = x_lable_overrides

        ## range tool 삽입구간
        plot_option["height"] = 60
        range_bar = figure(
            **plot_option,
            # background_fill_color="#efefef",
            y_axis_type=None,
        )

        range_tool = RangeTool(x_range=p1.x_range, start_gesture="pan")
        range_tool.overlay.fill_color = "navy"
        range_tool.overlay.fill_alpha = 0.2

        range_bar.line("index", "close", source=source)
        range_bar.ygrid.grid_line_color = None
        range_bar.add_tools(range_tool)
        range_bar.xaxis.major_label_overrides = x_lable_overrides

        # 위쪽 그래프의 x축 틱 라벨 제거
        # Y축 틱 라벨 형식 설정 (천 단위 구분 표시)
        p1.yaxis.formatter = NumeralTickFormatter(
            format="0,0"
        )  # 천 단위 쉼표 형식 적용
        p2.yaxis.formatter = NumeralTickFormatter(
            format="0,0"
        )  # 천 단위 쉼표 형식 적용

        # # Y축 틱 설정 ()
        p1.yaxis.ticker = AdaptiveTicker(min_interval=1000, max_interval=100000)
        p2.yaxis.ticker = AdaptiveTicker(min_interval=100000, max_interval=10000000)

        p1.xaxis.major_tick_line_color = None  # 주 눈금 선 제거
        p1.xaxis.minor_tick_line_color = None  # 부 눈금 선 제거

        # x축 제목은 아래쪽 그래프에만 표시
        p1.xaxis.axis_label = None
        p2.xaxis.axis_label = None
        p2.xaxis.major_label_text_font_size = "0pt"  # 라벨 크기를 0으로 설정
        # range_bar
        range_bar.xaxis.major_label_text_font_size = "0pt"  # 라벨 크기를 0으로 설정
        range_bar.xaxis.major_tick_line_color = None  # 주 눈금 선 제거
        range_bar.xaxis.minor_tick_line_color = None  # 부 눈금 선 제거

        # 그래프간 공백제거
        p1.min_border_bottom = 0
        p2.min_border_top = 0

        ## 거래량 최소값부터 보이기
        p2.y_range.start = source.data["volume"].min() / 2

        # HoverTool 추가 data source 에서 값갖온다.
        hover = HoverTool()
        hover.tooltips = [
            ("Date:", "@date{%F}"),
            ("open", "@open{0,0}"),
            ("high", "@high{0,0}"),
            ("low", "@low{0,0}"),
            ("close", "@close{0,0}"),
            ("volume", "@volume{0,0}"),
        ]  # 툴팁 설정
        hover.formatters = {"@date": "datetime"}  # '@date' 열을 datetime으로 처리
        # HoverTool 스타일 설정 필요 ( 투명도 )

        p1.add_tools(hover)
        p2.add_tools(hover)

        ## 전체 플롯하기
        layout = column(p1, p2, range_bar, sizing_mode="stretch_both")
        return layout
