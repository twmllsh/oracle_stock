import asyncio
import json
import random
import re
import csv
import os
import time
import pickle
import functools
from collections import Counter
import aiohttp
import numpy as np
import requests
import pandas as pd
from io import StringIO
from typing import Optional, List, Dict, Tuple, Iterable
from pathlib import Path
from pykrx import stock as pystock
import FinanceDataReader as fdr
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from django.db import transaction
from django.conf import settings
from django.db.models import Max
from django.db import DatabaseError
from django.db import connection
from dashboard.models import *
from dashboard.utils.sean_func import Text_mining
from dashboard.utils.mystock import Stock, ElseInfo
from .message import My_discord

mydiscord = My_discord()

ua = UserAgent()


class StockFunc:

    def to_number(value: str):
        if isinstance(value, str):
            if "조" in value:
                value = value.replace("조", "").replace(" ", "")
            pattern = re.compile("\d*,?\d*.?\d+")
            sub_pattern = re.compile("[,% ]")
            find = pattern.search(value)
            if find:
                value = find.group()
                value = sub_pattern.sub("", value)
                if value:
                    if "." in value:
                        value = float(value)
                    else:
                        value = int(value)
                else:
                    value = None
            else:
                value = None
        else:
            value = value

        if type(value) == float and (
            value == float("inf") or value == float("-inf") or pd.isna(value)
        ):
            value = None

        return value

    def remove_nomean_index_col(df: pd.DataFrame):
        df = df.transpose()
        df.columns = df.iloc[0]
        df = df.drop(df.index[0])
        return df

    def _cal_investor(df: pd.DataFrame):
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
                    # "순매수거래대금",
                ]
            ]
        ):
            temp_df = df.copy()

            ##########################################
            start_date, end_date = temp_df["날짜"].iloc[0], temp_df["날짜"].iloc[-1]
            temp_dic["start"] = start_date
            temp_dic["end"] = end_date

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

    def get_investor_part(code: str, low_dates: List):
        """
        애초부터 investor_ls 자료만 가져온다.
        """
        ls = []
        investor_ls = ["외국인", "투신", "금융투자", "연기금", "사모"]
        if len(low_dates):
            temp_low_dates = [
                date.date() for date in low_dates
            ]  # 임시변환 ? 이게 웨데이터 받는거랑 db 데이터 받는거랑 달라.?
            qs = InvestorTrading.objects.filter(
                ticker__code=code,
                날짜__gte=temp_low_dates[0],
                투자자__in=investor_ls,
            )
            df = pd.DataFrame(
                qs.values("날짜", "투자자", "매도거래대금", "매수거래대금")
            )
            if len(df):
                df["날짜"] = pd.to_datetime(df["날짜"])

                ## low_dates 별로 나누기. 시작 포함 끝 미포함.
                for i in range(len(low_dates) - 1):
                    temp_dic = {}
                    start_date, end_date = low_dates[i], low_dates[i + 1]
                    temp_df = df.loc[
                        (df["날짜"] >= start_date) & (df["날짜"] < end_date)
                    ]
                    if len(temp_df):
                        temp_dic = StockFunc._cal_investor(temp_df)
                        ls.append(temp_dic)
                ls.append(StockFunc._cal_investor(df))  # 마지막을 전체 데이터 계산.

        return pd.DataFrame(ls)

    def delete_old_data(the_model: models.Model, date_field="date", days=800):
        """
        대상
        """
        # model 있는지 확인
        if days < 800:
            print(
                "데이터 삭제 위험이 있습니다. 현재 n일이 {days} 일로 지정되어있습니다. 데이터 지우기를 취소합니다. "
            )
            return

        try:
            the_model.objects.exists()
            print("모델이 존재합니다.")
        except DatabaseError:
            print("테이블이 존재하지 않습니다.")
            return

        # date_field 있는지 확인
        exist_fields = [
            field.name
            for field in the_model._meta.get_fields()
            if field.name == date_field
        ]
        if not exist_fields:
            print("field가 존재하지 않습니다.")
            return
        # 데이터 있는지 확인
        if the_model.objects.exists():
            the_date = pd.Timestamp.now().date()
            the_date = the_date - pd.Timedelta(days=days)
            filter_args = {f"{date_field}__lte": the_date}  ##
            qs = the_model.objects.filter(**filter_args)
            if qs.exists():
                print(qs.values())

                # 있다면 삭제.
                # qs.delete()


import os
from .message import My_discord


class DBUpdater:

    def update_ticker():
        print("====================================")
        print("update_ticker running.......")
        print("====================================")

        asyncio.run(mydiscord.send_message(f"update_ticker start! "))

        datas = asyncio.run(GetData.get_code_info_df_async())
        print("데이터 다운로드 완료!")
        print("db update 중.")
        datas = datas.to_dict("records")

        new_codes = [data["code"] for data in datas]
        existing_tickers = Ticker.objects.filter(code__in=new_codes)
        existing_tickers_dict = {ticker.code: ticker for ticker in existing_tickers}
        # existing_codes = set(existing_tickers.values_list('code', flat=True))

        ## 업데이트할것과 새로 생성하는것을 분리
        to_update = []
        to_create = []

        for data in datas:
            code = data["code"]
            if code in existing_tickers_dict:
                # 존재하면
                ticker = existing_tickers_dict[code]
                if ticker.name != data["name"] or ticker.구분 != data["gb"]:
                    ticker.name = data["name"]
                    ticker.구분 = data["gb"]
                    to_update.append(ticker)
            else:
                # 존재하지 않으면
                to_create.append(
                    Ticker(code=data["code"], name=data["name"], 구분=data["gb"])
                )

        with transaction.atomic():
            if to_update:
                Ticker.objects.bulk_update(to_update, ["name", "구분"])
                print(f"updated 완료 {len(to_update)} ")
                print(to_update)

            if to_create:
                Ticker.objects.bulk_create(to_create)
                print(f"created 완료 {len(to_create)} ")
                print(to_create)

        print(f"updated : {len(to_update)} created : {len(to_create)}")

        asyncio.run(mydiscord.send_message(f"update_ticker finished!!"))
        return datas

    def ohlcv_from_backupfile_to_db(backup_file_name, backup_codes: List[str] = None):
        """
        backup_codes 는 리스트, 주어지면 리스트안에 있는 code 들만 백업.
        backup_codes
        """
        if backup_codes is None:
            backup_codes = []

        # backup_file_name = "ohlcv.csv"
        fn = Path(settings.BASE_DIR) / backup_file_name
        if os.path.exists(fn):

            def csv_data_generator(file_path):
                with open(file_path, mode="r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        yield row

            # data_gen = csv_data_generator(backup_file_name)
            # codes_in_new_datas = list({row["code"] for row in data_gen})
            tickers_dict = {ticker.code: ticker for ticker in Ticker.objects.all()}

            data_gen = csv_data_generator(backup_file_name)
            ohlcv_objects = []
            new_tickers = []
            for i, row in enumerate(data_gen):
                code = row["code"]

                if backup_codes and code not in backup_codes:
                    continue

                ticker = tickers_dict.get(code)
                if not ticker:  # ticker 객체가 없으면 만들기
                    ticker = Ticker(
                        code=code,
                    )
                    new_tickers.append(ticker)

                ohlcv_obj = Ohlcv(
                    ticker=ticker,
                    Date=pd.to_datetime(row["Date"]).date(),
                    Open=row["Open"],
                    High=row["High"],
                    Low=row["Low"],
                    Close=row["Close"],
                    Volume=row["Volume"],
                    Change=row["Change"],
                    Amount=row["Amount"],
                )
                ohlcv_objects.append(ohlcv_obj)

                # 일정 개수 이상일 때 bulk_create()로 한 번에 저장

                if len(ohlcv_objects) >= 2000:
                    print(f"{i} --2000개 bulk_create중....")
                    if new_tickers:
                        Ticker.objects.bulk_create(new_tickers)
                        new_tickers = []
                    Ohlcv.objects.bulk_create(ohlcv_objects)
                    ohlcv_objects = []  # 저장 후 리스트 초기화

            # 남은 객체들도 저장
            if ohlcv_objects:
                print("마지막데이터 bulk_create중....")
                if new_tickers:
                    Ticker.objects.bulk_create(new_tickers)
                Ohlcv.objects.bulk_create(ohlcv_objects)

        print("데이터 복원완료! ")

    def update_ohlcv(장중=None, codes:list = None):
        ''' option : , codes : '''
        print("====================================")
        print("update_ohlcv running.......")
        print("====================================")
        asyncio.run(mydiscord.send_message(f"update_ohlcv running.."))

        def _all_data_from_fdr():
            ## 만약 금요일이면,  전체데이터 새로 fdr로 받기.
            tickers = Ticker.objects.all()
            exist_ticker_dict = {ticker.code: ticker for ticker in tickers}

            
            start_date = pd.Timestamp.now().date() - pd.Timedelta(days=600)

            ## 데이터 모두 먼저 지우기
            Ohlcv.objects.all().delete()
            with connection.cursor() as cursor:
                # cursor.execute("CREATE SEQUENCE IF NOT EXISTS dashboard_ohlcv_id_seq;")
                cursor.execute("ALTER SEQUENCE dashboard_ohlcv_id_seq RESTART WITH 1;")
                # cursor.execute("ALTER TABLE dashboard_ohlcv ALTER COLUMN id SET DEFAULT nextval('dashboard_ohlcv_id_seq');")
            print('ohlcv id 초기화 성공!!!!!!!!')
            
            to_create_add = []
            ticker_list = []
            for code, ticker_obj in exist_ticker_dict.items():
                if ticker_obj:
                    print(ticker_obj.name, "...")
                    data = fdr.DataReader(code, start=start_date)
                    if len(data):
                        for date, row in data.iterrows():
                            ohlcv = Ohlcv(
                                ticker=ticker_obj,
                                Date=date,
                                Open=row["Open"],
                                High=row["High"],
                                Low=row["Low"],
                                Close=row["Close"],
                                Volume=row["Volume"],
                                Change=row["Change"],
                            )
                            to_create_add.append(ohlcv)
                            ticker_list.append(code)
                    
                if len(ticker_list) > 10: ## 10개씩 삭제 저장! 
                    ## 한 종목씩 저장하는 방식. 
                    with transaction.atomic():
                        # 기존 데이터 삭제
                        print(f"{ticker_list} db에 데이터 삭제 및 데이터 삽입 작업....")
                        # 새로운 데이터 일괄 삽입
                        Ohlcv.objects.bulk_create(to_create_add, batch_size=1000)
                    to_create_add = []
                    ticker_list = []
                    print('저장완료')
            print("finished!! ")

        # 금요일이면 _all_data_from_fdr 실행하기.
        today = pd.Timestamp.now()
        if today.weekday() == 6:  # 토요일이면
            # if today.weekday() ==4: # 0 :월
            print("전체 데이터 fdr 작업중.....")
            _all_data_from_fdr()
            return

        data = Ohlcv.objects.first()
        if not data:
            print(
                "데이터가 없어 백업파일 가져오기 시도"
            )  ## 데이터가 없기때문에 모두 create이다. 제너레이터로 bulk_create 사용하기.
            backup_file_name = "ohlcv.csv"
            DBUpdater.ohlcv_from_backupfile_to_db(backup_file_name)

        def backup_ohlcv():
            ohlcv_data = Ohlcv.objects.select_related("ticker").all()

            data = []
            for ohlcv in ohlcv_data:
                data.append(
                    {
                        "code": ohlcv.ticker.code,
                        "Date": ohlcv.Date,
                        "Open": ohlcv.Open,
                        "High": ohlcv.High,
                        "Low": ohlcv.Low,
                        "Close": ohlcv.Close,
                        "Amount": ohlcv.Amount,
                        "Volume": ohlcv.Volume,
                    }
                )

            df = pd.DataFrame(data)
            file_path = "./ohlcv_backup.csv"
            df.to_csv(file_path, index=False, encoding="utf8-sig")

        def delete_old_data():
            n = 1000
            the_date = pd.Timestamp.now().date() - pd.Timedelta(days=n)
            old_qs = Ohlcv.objects.filter(date__lt=the_date)
            delete_cnt = old_qs.count()
            if delete_cnt:
                print(f"{delete_cnt}개의 오래된 데이터가 있어 삭제합니다.")
                old_qs.delete()

        # 최근데이터 가져오기 . 랜덤으로 n개 마지막날짜 가져와서 가장 많은 날짜가 마지막인것으로 간주.
        # [ { 'ticker':'005940', 'last_date':datetime() } ....  ]
        last_dates = Ohlcv.objects.values("ticker").annotate(last_date=Max("Date"))
        # {'005930': date(), ....}
        last_dates = {item["ticker"]: item["last_date"] for item in last_dates}
        # 다운로드 받기 위한 일반적 최근 날짜 구함.
        counter = Counter(last_dates.values())
        last_exist_date = counter.most_common()[0][0]
        print(f"last date : {last_exist_date}")
        # 그날짜부터 오늘까지 date_list 생성 (비지니스데이)
        dates = pd.date_range(
            last_exist_date, pd.Timestamp.today().date(), freq="B"
        )  ## ohlcv존재하는지 아닌지 확인할때 사용하기.
        str_dates = [date.strftime("%Y%m%d") for date in dates]
        print(f"{str_dates} data downlaod....!")
        
        if (codes is not None) and (len(codes) <= 200):
            temp_today = pd.Timestamp.now().strftime('%Y-%m-%d')
            if not Ohlcv.objects.filter(Date__in=[temp_today]).exists(): ## 오늘날짜 없으면 전체 먼저 업데이트!
                today_df = DBUpdater.update_ohlcv() 
                
                '''
                ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Change','code']
                '''
            ################### fdr 방식. ########################################
            print('fdr async 작동!')
            semaphore = asyncio.Semaphore(5) 
            async def async_fdr_datareader(semaphore, code, start_date):
                async with semaphore:
                    result = await asyncio.to_thread(fdr.DataReader, code, start_date)
                    result['code'] = code
                    return result
            async def async_fdr_datareader_all(semaphore, codes, start_date):
                tasks = [asyncio.create_task(async_fdr_datareader(semaphore, code, start_date)) for code in codes]
                results = await asyncio.gather(*tasks)
                df = pd.concat(results)
                df.reset_index(inplace=True)
                return df
            concat_df = asyncio.run(async_fdr_datareader_all(semaphore, codes, str_dates[0]))  ## 장중에만 업데이트 해야함. 
            
            
        else:
            ########################### pystock #####################
            # 순환하면 데이터 가져오기.
            all_ls = [GetData.get_ohlcv_all_market(date) for date in str_dates]
            print(f"{str_dates} data downlaod complete! !")
            concat_df = pd.concat(all_ls)

        ## 새로받은데이터의 code 와 Date 정보 가져오기
        ticker_codes = concat_df["code"].unique()
        dates = concat_df["Date"].unique()
    
        
        
        ###########################################################################
        
        ## 기존 데이터에 존재하는 ohlcv객체 검색
        existing_ohlcv = Ohlcv.objects.filter(
            ticker__code__in=ticker_codes,
            Date__in=dates,
        ).select_related("ticker")

        ## (date, code) : ticker_obj  형태로 딕셔너리 생성
        existing_ticker_dict = {
            ticker.code: ticker for ticker in Ticker.objects.all()
        }  # 존재하는 ticker

        existing_ohlcv_dict = {
            (ohlcv.Date, ohlcv.ticker): ohlcv for ohlcv in existing_ohlcv
        }  # 존재하는 날짜와 ticker에 의한 ohlcv객체

        ## code 별 최근데이터가 다른 종목들은 따로 작업해주기. 할필요있나.?
        print(f"{len(concat_df)} data setting...")
        to_create = []
        to_update = []

        for i, row in concat_df.iterrows():
            code = row["code"]
            date = row["Date"].date()
            if code in existing_ticker_dict.keys():  # ticker 객체가 존재하면.
                ticker = existing_ticker_dict[code]
                key = (date, ticker)

                if key in existing_ohlcv_dict:
                    # 존재하면 update에 추가
                    ohlcv = existing_ohlcv_dict[key]
                    ohlcv.Open = row["Open"]
                    ohlcv.High = row["High"]
                    ohlcv.Low = row["Low"]
                    ohlcv.Close = row["Close"]
                    ohlcv.Volume = row["Volume"]
                    
                    if 'Change' in concat_df.columns:
                        ohlcv.Change = row["Change"]
                    if 'Amount' in concat_df.columns:
                        ohlcv.Amount = row["Amount"]

                    to_update.append(ohlcv)

                else:
                    # 존재하지 않으면 create에 추가
                    ohlcv = Ohlcv(
                        ticker=ticker,
                        Date=date,
                        Open=row["Open"],
                        High=row["High"],
                        Low=row["Low"],
                        Close=row["Close"],
                        Volume=row["Volume"],
                        Change=row["Change"],
                    )
                    if 'Amount' in concat_df.columns:
                        ohlcv.Amount = row["Amount"] 
                    to_create.append(ohlcv)

        
        update_fileds = ["Open", "High", "Low", "Close", "Change", "Volume"]
        if 'Amount' in concat_df.columns:
            update_fileds += ['Amount']

        print("bulk_job start!")
        with transaction.atomic():
            # bulk_update
            if to_update:
                Ohlcv.objects.bulk_update(to_update, update_fileds)
                print(f"{len(to_update)} 개 데이터 update")
            # bulk_create
            if to_create:
                Ohlcv.objects.bulk_create(to_create)
                print(f"{len(to_create)} 개 데이터 create")

        print("bulk_job complete!")
        asyncio.run(mydiscord.send_message(f"update_ohlcv finished!!"))

        ## QuerySet Hint

        #### 코드 날짜로 데이터 가져오기
        ## col = ['date','open','high','low','close','volume']
        # col = [field.name for field in Ohlcv._meta.fields if not field.name in ['id','ticker']]
        # data = Ohlcv.objects.select_related('ticker').filter(
        #       ticker__code='005930', date__gt=the_date
        #   ).values(*col)
        # df = pd.DataFrame(data)

        ## ticker 에서 ohlcv데이터 가져오기
        # col = [field.name for field in Ohlcv._meta.fields if not field.name in ['id','ticker']]
        # ticker = Ticker.objects.first()
        # df = pd.DataFrame(ticker.ohlcv_set.values(*col))

        #### 특정일 (오늘) 양봉데이터만 받기.
        # the_date= pd.Timestamp().now().date()
        # the_data = Ohlcv.objects.filter(date='2024-09-27').select_related('ticker')
        concat_df = concat_df[concat_df['Date'] == concat_df['Date'].max()]
        return concat_df
    
    def update_basic_info(test_cnt: int = None, update_codes=None):

        print("====================================")
        print("update_basic_info running.......")
        print("====================================")
        # test_cnt = 100

        asyncio.run(mydiscord.send_message(f"update_basic_info running......"))
        if update_codes is None:
            update_codes = []
        ticker_qs = Ticker.objects.values_list("code", "name")
        if update_codes:
            ticker_qs = ticker_qs.filter(code__in=update_codes)

        if test_cnt:
            ticker_qs = random.sample(list(ticker_qs), test_cnt)
        else:
            ticker_qs = list(ticker_qs)
        print(f"test_cnt = {test_cnt}")

        ## data download
        new_datas = asyncio.run(GetData._get_info_all_async(ticker_qs))

        # ################################################################
        # try:
        #     with open('./basic_info_pickle.pkl' , 'wb') as f:
        #         pickle.dump(new_datas, f, protocol=pickle.HIGHEST_PROTOCOL)
        #         print('./basic_info_pickle.pkl 로 임시저장완료')
        # except:
        #     pass
        # #################################################################

        # with open("./basic_info_pickle.pkl", "rb") as f:
        #     print('pickle 데이터로 작업 시작! ')
        #     new_datas = pickle.load(f)

        changedlog_models = []

        ## 새로운데이터에서 code 정보
        new_data_codes = [
            infodic.get("code") for infodic, _, _ in new_datas if infodic.get("code")
        ]

        ## 존재하는 tickers 객체들
        existing_ticker_dict = {ticker.code: ticker for ticker in Ticker.objects.all()}

        ## 존재하는 Info객체들.  #########################################################################
        existing_info_dict = {
            info.ticker.code: info
            for info in Info.objects.filter(
                ticker__code__in=new_data_codes
            ).select_related("ticker")
        }
        to_create_info = []
        to_update_info = []
        update_fileds_info = [
            field.name
            for field in Info._meta.get_fields()
            if not field.name in ["id", "ticker"]
        ]
        #############################################################################################

        ## 존재하는 Brokertrading.  #########################################################################
        existing_brokertrading_dict = {
            (broker.ticker.code, broker.date, broker.broker_name): broker
            for broker in BrokerTrading.objects.filter(
                ticker__code__in=new_data_codes
            ).select_related("ticker")
        }
        to_create_brokerinfo = []
        to_update_brokerinfo = []
        update_fileds_brokertrading = [
            field.name
            for field in BrokerTrading._meta.get_fields()
            if not field.name in ["id", "ticker", "date", "broker_name"]
        ]
        #############################################################################################

        ## 존재하는 Finstats  #########################################################################
        existing_fin_dict = {
            (fin.ticker.code, fin.fintype, fin.year, fin.quarter): fin
            for fin in Finstats.objects.filter(
                ticker__code__in=new_data_codes
            ).select_related("ticker")
        }
        to_create_fin = []
        to_update_fin = []
        update_fileds_fin = [
            field.name
            for field in Finstats._meta.get_fields()
            if not field.name in ["id", "ticker", "year", "quarter", "fintype"]
        ]
        #############################################################################################

        ## 전체데이터 순환구간.
        print("데이터베이스 작업..")

        for infodic, traderinfo, finstats in new_datas:
            code = infodic.get("code")
            if code:
                ticker = existing_ticker_dict[code]

                ## infodic 처리구간. ##############################33333333333333
                if code in existing_info_dict:
                    ## update
                    info = existing_info_dict[code]
                    for field, new_value in infodic.items():
                        if hasattr(info, field):
                            setattr(info, field, new_value)
                    to_update_info.append(info)

                    ## 변경사항 조회
                    changes = info.tracker.changed()
                    if changes:
                        for field, old_value in changes.items():
                            if isinstance(old_value, (int, float)):
                                changedlog_model = ChangeLog(
                                    ticker=ticker,
                                    change_field=field,
                                    old_value=old_value,
                                    new_value=getattr(info, field),
                                )
                                changedlog_models.append(
                                    changedlog_model
                                )  ## changedlog_models 추가

                else:
                    info = Info(
                        ticker=ticker,
                    )
                    for field, new_value in infodic.items():
                        if hasattr(info, field):
                            setattr(info, field, new_value)
                    to_create_info.append(info)

                # ### traderinfo 처리구간333333333333333333333333333333333333333
                # 구분 = infodic['구분']
                today = infodic.get("date")
                today = pd.Timestamp.now().date() if not today else today.date()
                if len(traderinfo):
                    for broker, new_values in traderinfo.items():
                        if not isinstance(
                            broker, str
                        ):  ## broker 가 없는경우 nan값으로 들어와서 패싱함.
                            continue

                        key = (code, today, broker)
                        if key in existing_brokertrading_dict:
                            brokertrading = existing_brokertrading_dict[key]
                            ## update
                            for item, value in new_values.items():
                                if hasattr(brokertrading, item):
                                    setattr(brokertrading, item, value)
                            to_update_brokerinfo.append(brokertrading)

                        else:
                            # create
                            brokertrading = BrokerTrading(
                                ticker=ticker,
                                date=today,
                                broker_name=broker,
                                sell=new_values["sell"],
                                buy=new_values["buy"],
                            )
                            to_create_brokerinfo.append(brokertrading)

                # ### finstats 처리구간
                ## 지난연도데이터를 스킵할 필요가 있음.    아니면 change 목록을 넓히고 change된것만 update로 넘기기.
                for fintype, datas1 in finstats.items():
                    for p, data in datas1.items():
                        year = p.split("/")[0]
                        quarter = p.split("/")[-1]
                        quarter = 0 if year == quarter else int(int(quarter))
                        year = int(year)

                        key = (code, fintype, year, quarter)

                        if (
                            key in existing_fin_dict
                        ):  # = {(fin.ticker.code, fin.fintype, fin.year, fin.quarter)
                            # update
                            fin = existing_fin_dict[key]
                            for field, new_value in data.items():
                                if hasattr(fin, field):
                                    setattr(fin, field, new_value)

                            ## 변경사항 체크.
                            changes = fin.tracker.changed()
                            if changes:
                                to_update_fin.append(fin)
                                for field, old_value in changes.items():
                                    if isinstance(old_value, (int, float)):
                                        gb = f"{year}{quarter}"
                                        changedlog_model = ChangeLog(
                                            ticker=ticker,
                                            change_field=field,
                                            gb=gb,
                                            old_value=old_value,
                                            new_value=getattr(fin, field),
                                        )
                                        changedlog_models.append(changedlog_model)

                        else:
                            # create
                            fin = Finstats(
                                ticker=ticker,
                                fintype=fintype,
                                year=year,
                                quarter=quarter,
                            )
                            for field, new_value in data.items():
                                if field in update_fileds_fin:
                                    if hasattr(fin, field):
                                        setattr(fin, field, new_value)
                            to_create_fin.append(fin)

        ### 저장 구간
        print("bulk job start!! ")
        with transaction.atomic():
            # bulk_update
            if to_update_info:
                Info.objects.bulk_update(
                    to_update_info, update_fileds_info, batch_size=1000
                )
                print(f"{len(to_update_info)} 개 데이터 update")
            # bulk_create
            if to_create_info:
                Info.objects.bulk_create(to_create_info, batch_size=1000)
                print(f"{len(to_create_info)} 개 데이터 create")

            # BrokerTrader
            if to_update_brokerinfo:
                BrokerTrading.objects.bulk_update(
                    to_update_brokerinfo, update_fileds_brokertrading, batch_size=1000
                )
                print(f"{len(to_update_brokerinfo)} 개 데이터 broker_trading update")
            # bulk_create
            if to_create_brokerinfo:
                BrokerTrading.objects.bulk_create(to_create_brokerinfo, batch_size=1000)
                print(f"{len(to_create_brokerinfo)} 개 데이터 broker_trading create")

            # Finstats
            if to_update_fin:
                Finstats.objects.bulk_update(
                    to_update_fin, update_fileds_fin, batch_size=1000
                )
                print(f"{len(to_update_fin)} 개 데이터 fin update")
            # bulk_create
            if to_create_fin:
                Finstats.objects.bulk_create(to_create_fin, batch_size=1000)
                print(f"{len(to_create_fin)} 개 데이터 fin create")

            # changedlog_models bulk_create 구간.
            print(f"changedlog_models count : {len(changedlog_models)}")
            if changedlog_models:
                ChangeLog.objects.bulk_create(changedlog_models)
                print("changedlog_models bulk_create succeed!! ")

        print("bulk_job complete!")
        asyncio.run(mydiscord.send_message(f"update_basic_info finished......"))

    def investor_from_file_to_db(backupfile, update_codes: List[str] = None):

        if update_codes is None:
            update_codes = []

        def csv_data_generator(file_path):
            with open(file_path, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    yield row

        def records_to_db(records: Iterable[Dict], update_codes=[]) -> None:
            """
            records : [ {'code':'', '종목명':'', '매도거래량': 33, ...}, .....   ]  []
            """
            tickers_dict = {ticker.code: ticker for ticker in Ticker.objects.all()}
            to_create_investor = []
            new_tickers = []
            for i, row in enumerate(records):
                code = row["code"]

                if update_codes and code not in update_codes:
                    continue

                if code in tickers_dict:
                    # ticker 가져오기
                    ticker = tickers_dict.get(row["code"])
                else:
                    # ticker 새로생성
                    ticker = Ticker(
                        code=code,
                        # name=codes_in_new_datas_dict[code],
                        name=row["종목명"],
                    )
                    print(f"{code}, {row['종목명']} ticker 새로 생성")
                    new_tickers.append(ticker)
                    tickers_dict[code] = (
                        ticker  # 새로만든 ticker도 tickers_dict에 넣어줘야 위에서 다시 만들지 않는다.
                    )

                investor_obj = InvestorTrading(
                    ticker=ticker,
                    날짜=pd.to_datetime(row["날짜"]).date(),
                    투자자=row["투자자"],
                    매도거래량=row["매도거래량"],
                    매수거래량=row["매수거래량"],
                    매도거래대금=row["매도거래대금"],
                    매수거래대금=row["매수거래대금"],
                )
                to_create_investor.append(investor_obj)

                # 일정 개수 이상일 때 bulk_create()로 한 번에 저장
                bulk_cnt = 10000
                if len(to_create_investor) >= bulk_cnt:
                    print(f"{i} --{bulk_cnt}개 bulk_create중....")
                    if new_tickers:
                        print(f"새로운 ticker정보 {len(new_tickers)}개 저장!")
                        Ticker.objects.bulk_create(new_tickers)
                        new_tickers = []
                    InvestorTrading.objects.bulk_create(
                        to_create_investor, batch_size=2000
                    )
                    to_create_investor = []  # 저장 후 리스트 초기화

            # 남은 객체들도 저장
            if to_create_investor:
                print("마지막데이터 bulk_create중....")
                if new_tickers:
                    print(f"새로운 ticker정보 {len(new_tickers)}개 저장!")
                    Ticker.objects.bulk_create(new_tickers)
                    new_tickers = []
                InvestorTrading.objects.bulk_create(to_create_investor)
                to_create_investor = []

        backup_file_name = "investor.csv"
        fn = Path(settings.BASE_DIR) / backup_file_name
        if os.path.exists(fn):
            data_gen = csv_data_generator(backup_file_name)
            records_to_db(data_gen, update_codes=update_codes)
            print("데이터 복원완료!")

    def update_investor():

        print("====================================")
        print("update_investor running.......")
        print("====================================")

        def csv_data_generator(file_path):
            with open(file_path, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    yield row

        def records_to_db(records: Iterable[Dict]) -> None:
            """
            records : [ {'code':'', '종목명':'', '매도거래량': 33, ...}, .....   ]  []
            """
            tickers_dict = {ticker.code: ticker for ticker in Ticker.objects.all()}
            to_create_investor = []
            new_tickers = []
            for i, row in enumerate(records):
                code = row["code"]
                if code in tickers_dict:
                    # ticker 가져오기
                    ticker = tickers_dict.get(row["code"])
                else:
                    # ticker 새로생성
                    ticker = Ticker(
                        code=code,
                        # name=codes_in_new_datas_dict[code],
                        name=row["종목명"],
                    )
                    print(f"{code}, {row['종목명']} ticker 새로 생성")
                    new_tickers.append(ticker)
                    tickers_dict[code] = (
                        ticker  # 새로만든 ticker도 tickers_dict에 넣어줘야 위에서 다시 만들지 않는다.
                    )

                investor_obj = InvestorTrading(
                    ticker=ticker,
                    날짜=pd.to_datetime(row["날짜"]).date(),
                    투자자=row["투자자"],
                    매도거래량=row["매도거래량"],
                    매수거래량=row["매수거래량"],
                    매도거래대금=row["매도거래대금"],
                    매수거래대금=row["매수거래대금"],
                )
                to_create_investor.append(investor_obj)

                # 일정 개수 이상일 때 bulk_create()로 한 번에 저장
                bulk_cnt = 10000
                if len(to_create_investor) >= bulk_cnt:
                    print(f"{i} --{bulk_cnt}개 bulk_create중....")
                    if new_tickers:
                        print(f"새로운 ticker정보 {len(new_tickers)}개 저장!")
                        Ticker.objects.bulk_create(new_tickers)
                        new_tickers = []
                    InvestorTrading.objects.bulk_create(
                        to_create_investor, batch_size=2000
                    )
                    to_create_investor = []  # 저장 후 리스트 초기화

            # 남은 객체들도 저장
            if to_create_investor:
                print("마지막데이터 bulk_create중....")
                if new_tickers:
                    print(f"새로운 ticker정보 {len(new_tickers)}개 저장!")
                    Ticker.objects.bulk_create(new_tickers)
                    new_tickers = []
                InvestorTrading.objects.bulk_create(to_create_investor)
                to_create_investor = []

        asyncio.run(mydiscord.send_message(f"update_investor start!......"))

        data = InvestorTrading.objects.last()
        if not data:
            print(
                "데이터가 없어 백업파일 가져오기만 시도합니다."
            )  ## 데이터가 없기때문에 모두 create이다. 제너레이터로 bulk_create 사용하기.
            backup_file_name = "investor.csv"
            fn = Path(settings.BASE_DIR) / backup_file_name
            if os.path.exists(fn):
                data_gen = csv_data_generator(backup_file_name)
                records_to_db(data_gen)
                print("데이터 복원완료!")
            return

        # update 하기
        latest_dates = (
            InvestorTrading.objects.values("ticker_id")
            .annotate(latest_date=Max("날짜"))
            .order_by("?")[:10]
        )
        latest_dates_list = list(latest_dates.values_list("latest_date", flat=True))
        counter = Counter(latest_dates_list)
        last_exist_date = counter.most_common()[0][0]
        print(f"last date : {last_exist_date}")

        # 그날짜부터 오늘까지 date_list 생성 (비지니스데이)
        dates = pd.date_range(last_exist_date, pd.Timestamp.today().date(), freq="B")
        dates = dates[1:]  # 마지막일 제외. 어차피 확정인 자료임. 업데이트는 의미없다.

        if len(dates):
            # 데이터 받기
            str_dates = [date.strftime("%Y%m%d") for date in dates]
            result = asyncio.run(GetData._get_investor_all_async(str_dates))
            dates_downloaded = result["날짜"].unique()

            records = result.to_dict("records")
            print(f"dates downloaded {dates_downloaded}")
            # 저장하기.
            records_to_db(records=records)

        # ## 최종적으로 특정날짜 이전 데이터 제거하기.
        n = 365 * 2
        the_date = pd.Timestamp.now().date() - pd.Timedelta(days=n)
        qs = InvestorTrading.objects.filter(날짜__lt=the_date)
        # Ohlcv.objects.filter(date__lt=the_date).delete()

        asyncio.run(mydiscord.send_message(f"update_investor finished......"))

        #### 코드 날짜로 데이터 가져오기
        # col = ['date','open','high','low','close','volume']
        # data = Ohlcv.objects.select_related('ticker').filter(
        #       ticker__code='005930', date__gt=the_date
        #   ).values(*col)
        # df = pd.DataFrame(data)

        #### 특정일 (오늘) 양봉데이터만 받기.
        # the_date= pd.Timestamp().now().date()
        # the_data = Ohlcv.objects.filter(date='2024-09-27').select_related('ticker')

    def update_issue(date_cnt=1):
        """
        1시간마다 실행. !
        date_cnt=1 그날 데이터만 취급
        가져온 데이터의 맨 위. 가장 최근일.
        """
        asyncio.run(mydiscord.send_message(f"update_issue start......"))
        print("====================================")
        print("update_issue running.......")
        print("====================================")

        iss_df = GetData.get_iss_list()  # 전체 데이터 받기.

        valid_dates = iss_df["regdate"].unique()[
            :date_cnt
        ]  # 가져올 날짜 리스트( 최근일 또는 오늘)

        latest_df = iss_df.loc[
            iss_df["regdate"].isin(valid_dates)
        ]  # 최근 데이터만 추출

        latest_dict_list = latest_df.to_dict("records")

        print(f"{len(latest_dict_list)} 개 데이터 받음.")

        # 기존데이터가 있는지 확인하기. 없는 데이터만 작업하기.
        new_text = [item["hl_str"] for item in latest_dict_list]
        existing_hl_str = Iss.objects.filter(hl_str__in=new_text).values_list(
            "hl_str", flat=True
        )
        duplicate_urls = set(existing_hl_str) & set(new_text)
        new_unique_urls = set(new_text) - duplicate_urls

        new_dict_list = [
            item for item in latest_dict_list if item["hl_str"] in new_unique_urls
        ]

        if not new_dict_list:
            print("새로운 데이터가 없습니다.")
            return None
        print(f"{len(new_dict_list)}개의 새로운 데이터가 있습니다.")
        # # 데이터 업데이트

        for dic in new_dict_list:
            print(dic["hl_str"])
            new_dict = GetData.get_iss_from_number(dic["issn"])
            related_df = GetData.get_iss_related(dic["issn"])
            dic.update(new_dict)
            dic["ralated_codes"] = list(related_df["code"])
            time.sleep(1)

        # new_dict_list 데이터 저장하기.
        # related_codes 는 tickers.add()처리하고 나머지 데이터만 저장하기.
        for dic in new_dict_list:
            related = dic.pop("ralated_codes", [])
            # iss = Iss(**dic)
            iss = Iss(
                issn=dic["issn"],
                hl_str=dic["hl_str"],
                regdate=dic["regdate"],
                ralated_code_names=dic["ralated_code_names"],
                hl_cont_text=dic["hl_cont_text"],
                hl_cont_url=dic["hl_cont_url"],
            )
            try:
                iss.save()
                print("saving..", dic["hl_str"][:10])
                if related:
                    # filter 로 ticker object 가져오기
                    iss.tickers.set(related)
                    print("tickers set ok!")
                    # tickers = Ticker.objects.filter(code__in=related)
                    # if len(tickers):
                    #     for ticker in tickers:
                    #         # if not iss.tickers.filter(ticker=ticker.code).exists():
                    #         iss.tickers.add(tickers)  ## 새로운이슈니까 그냥 add 나 셋하면 됨.
            except Exception as e:
                print(e, dic)
        asyncio.run(mydiscord.send_message(f"update_issue finished......"))
        return latest_dict_list

    def update_theme_upjong():
        """
        데이터 가져와서 저장하기.
        """
        asyncio.run(mydiscord.send_message(f"update_upjong start......"))
        print("====================================")
        print("update_theme_upjong running.......")
        print("====================================")
        ## 실제데이터 다운로드
        theme_data, upjong_data = asyncio.run(GetData.get_all_upjong_theme())

        # 존재하는 ticker 객체 가져오기
        existing_tickers_dict = {ticker.code: ticker for ticker in Ticker.objects.all()}
        # 존재하는 theme 객체 가져오기.
        existing_theme_dict = {theme.name: theme for theme in Theme.objects.all()}

        theme_df = pd.DataFrame(theme_data)
        ## 새로운 테마 있으면 저장.
        new_themes = [
            Theme(name=name)
            for name in theme_df["name"].unique()
            if name not in existing_theme_dict
        ]
        if new_themes:
            Theme.objects.bulk_create(new_themes)

        ## 관계설정.
        existing_theme_dict = {
            theme.name: theme
            for theme in Theme.objects.prefetch_related("tickers").all()
        }
        codes_by_name = (
            theme_df.groupby("name")["code"]
            .apply(list)
            .reset_index()
            .to_dict("records")
        )
        for dic in codes_by_name:
            theme_name = dic["name"]
            theme_codes = dic["code"]
            theme = existing_theme_dict[theme_name]
            theme_code_obj_set = {
                existing_tickers_dict[code]
                for code in theme_codes
                if code in existing_tickers_dict
            }
            ## 변경사항 추적
            pre_tickers_obj = set(theme.tickers.all())
            add_obj_set = theme_code_obj_set - pre_tickers_obj
            remove_obj_set = pre_tickers_obj - theme_code_obj_set
            if add_obj_set or remove_obj_set:
                print("=========== 변경사항 발생 ==================")
                print(f"{add_obj_set} 추가")
                print(f"{remove_obj_set} 추가")
                print("=========================================")
                theme.tickers.set(theme_code_obj_set)

        ## ThemeDetail 저장.
        # 전체 데이터 순환하면서 존재하는 데이터 모두 업데이트하기.
        existing_details = {
            f"{detail.ticker.code}_{detail.theme.name}": detail
            for detail in ThemeDetail.objects.prefetch_related("ticker")
            .prefetch_related("theme")
            .all()
        }
        existing_theme_dict = {theme.name: theme for theme in Theme.objects.all()}

        update_theme_details = []
        create_theme_details = []
        for theme_item in theme_data:
            name = theme_item["name"]
            code = theme_item["code"]

            key_name = f"{code}_{name}"
            if key_name in existing_details:
                # update
                detail = existing_details.get(key_name)
                if detail.description != theme_item["theme_text"]:
                    detail.description = theme_item["theme_text"]
                    update_theme_details.append(detail)
            else:
                if (
                    code in existing_tickers_dict
                ):  # 기본티커 정보가 잇어야 저장할수 있음.
                    ticker = existing_tickers_dict.get(code)
                    ## theme 가 없는 상황이라 만들어야함. ?

                    theme = Theme.objects.create(ticker=ticker, name=name)
                    detail = ThemeDetail(
                        ticker=ticker, theme=theme, description=theme["theme_text"]
                    )
                    create_theme_details.append(detail)

        # 지우고 그냥 새로 저장
        if create_theme_details:
            print(f"{len(create_theme_details)}개 create 저장")
            ThemeDetail.objects.bulk_create(create_theme_details)
        if update_theme_details:
            print(f"{len(update_theme_details)}개 update 저장")
            ThemeDetail.objects.bulk_update(update_theme_details, ["description"])

        ## 업종
        # 존재하는 ticker 객체 가져오기
        existing_tickers_dict = {ticker.code: ticker for ticker in Ticker.objects.all()}
        # 존재하는 theme 객체 가져오기.
        existing_upjong_dict = {upjong.name: upjong for upjong in Upjong.objects.all()}

        upjong_df = pd.DataFrame(upjong_data)
        ## 새로운 테마 있으면 저장.
        new_upjongs = [
            Upjong(name=name)
            for name in upjong_df["name"].unique()
            if name not in existing_upjong_dict
        ]
        if new_upjongs:
            Upjong.objects.bulk_create(new_upjongs)

        ## upjong에 속한 종목들 지정하기.
        ## 관계설정.
        existing_upjong_dict = {
            upjong.name: upjong
            for upjong in Upjong.objects.prefetch_related("tickers").all()
        }
        codes_by_name = (
            upjong_df.groupby("name")["code"]
            .apply(list)
            .reset_index()
            .to_dict("records")
        )
        for dic in codes_by_name:
            upjong_name = dic["name"]
            upjong_codes = dic["code"]
            upjong = existing_upjong_dict[upjong_name]
            upjong_code_obj_set = {
                existing_tickers_dict[code]
                for code in upjong_codes
                if code in existing_tickers_dict
            }
            ## 변경사항 추적
            pre_tickers_obj = set(upjong.tickers.all())
            add_obj_set = upjong_code_obj_set - pre_tickers_obj
            remove_obj_set = pre_tickers_obj - upjong_code_obj_set
            if add_obj_set or remove_obj_set:
                print("=========== 변경사항 발생 ==================")
                print(f"{add_obj_set} 추가")
                print(f"{remove_obj_set} 추가")
                print("=========================================")
                upjong.tickers.set(upjong_code_obj_set)
        asyncio.run(mydiscord.send_message(f"update_issue finished......"))

    def update_stockplus_news():

        print("====================================")
        print("update_stockplus running.......")
        print("====================================")
        asyncio.run(mydiscord.send_message(f"update_stockplus_news start......"))
        datas = asyncio.run(GetData._get_news_from_stockplus_today())

        ## test
        # datas= datas[:10]

        if not datas:
            print("데이터 크롤링 실패")
            return {}

        to_create = []
        ralated_list_data = []
        qs = News.objects.prefetch_related("ticker").all()
        existing_news_no = qs.values_list("no", flat=True)

        existing_ticker_dict = {ticker.code: ticker for ticker in Ticker.objects.all()}

        ## 또는 그냥 exists() 사용하기.
        for data in datas:
            if not data["no"] in existing_news_no:
                # if not News.objects.filter(no=data['no']).exists():
                news = News(
                    no=data["no"],
                    title=data["title"],
                    createdAt=data["createdAt"],
                    writerName=data["writerName"],
                )
                try:
                    to_create.append(news)
                    news.save()  # 저장 후
                    print("save succeed!")
                except Exception as e:
                    print(e, data)

                try:
                    if data["relatedStocks"]:
                        news.tickers.set(data["relatedStocks"])
                        print("related code setting !")
                except Exception as e:
                    print(e, data["relatedStocks"])

        print(f"{len(datas)} 개 중 {len(to_create)} 개 데이터 저장!")
        asyncio.run(mydiscord.send_message(f"update_stockplus_news finished......"))
        ## to_create 자료가지고 데이터 만들어 메세지 보내기

    
    def anal_all_stock(anal=True):
        
        
        
        def _create_and_update(to_create, to_update, update_fields):
            with transaction.atomic():
                if to_update:
                    ChartValue.objects.bulk_update(to_update, update_fields)
                    print(f"updated 완료 {len(to_update)} ")
                    print(to_update)

                if to_create:
                    ChartValue.objects.bulk_create(to_create)
                    print(f"created 완료 {len(to_create)} ")
                    print(to_create)
            print(f"updated : {len(to_update)} created : {len(to_create)}")
        
        # 전체 분석해서 저장하기. Chartvalues()
        '''codes ['code','code',...]'''
        from dashboard.utils.chart import Chart
        today_df = DBUpdater.update_ohlcv()
        
        check_y1, check_y2 = ElseInfo.check_y_future
        check_q = ElseInfo.check_q_current[-1]
        all_cnt = 0
        exist_qs_dict = {item.ticker.code : item for item in ChartValue.objects.all()}
        to_create=[]
        to_update=[]

        update_fields = [field.name for field in ChartValue._meta.get_fields() if not isinstance(field, models.OneToOneField) ]
        update_fields = [field for field in update_fields if field !='id']
        
        codes = DBUpdater.update_ticker()
        
        for item in codes:
        
            ## 임시로 없는 데이터들만 작업.
            print(item['name'], end=',')
            if item['code'] in exist_qs_dict:
                continue

            stock = Stock(item['code'], anal=True)
            info_dic = {}
            info_dic['ticker'] = stock.ticker
            info_dic['cur_price'] = stock.chart_d.df.Close.iloc[-1]
            if isinstance(stock.fin_df, pd.DataFrame):
                df_y = stock.fin_df.set_index('year')
                info_dic["growth_y1"] = df_y.loc[int(check_y1), 'growth'] if int(check_y1) in df_y.index else None 
                info_dic['growth_y2'] = df_y.loc[int(check_y2), 'growth'] if int(check_y2) in df_y.index else None 
            if isinstance(stock.fin_df_q, pd.DataFrame):
                df_q = stock.fin_df_q
                info_dic['growth_q'] = df_q.loc[check_q, 'yoy'] if check_q in df_q.index else None 

            bb_texts = ['bb60','bb240']
            for chart_name in ['chart_d','chart_30','chart_5']:
                if hasattr(stock, chart_name):
                    chart : Chart = getattr(stock, chart_name)
                    for bb_text in bb_texts:
                        if hasattr(chart, bb_text):
                            bb = getattr(chart, bb_text)
                            info_dic[f"{chart_name}_{bb_text}_upper20"] = bb.upper_inclination20 if hasattr(bb, "upper_inclination20") else None
                            info_dic[f"{chart_name}_{bb_text}_upper10"] = bb.upper_inclination10 if hasattr(bb, "upper_inclination10") else None
                            info_dic[f"{chart_name}_{bb_text}_upper"] = bb.cur_upper_value if hasattr(bb, "cur_upper_value") else None
                            info_dic[f"{chart_name}_{bb_text}_width"] = bb.cur_width if hasattr(bb, "cur_width") else None

                    if hasattr(chart, 'sun'):
                        sun = getattr(chart, 'sun')
                        info_dic[f"{chart_name}_sun_width"] = chart.sun.width if hasattr(sun, 'width') else None
                    info_dic[f"{chart_name}_new_phase"] = chart.is_new_phase()
                    info_dic[f"{chart_name}_ab"] = chart.is_ab(ma=20) if hasattr(chart, f'ma{20}') else None
                    info_dic[f"{chart_name}_ab_v"] = chart.is_ab_volume()
                    info_dic[f"{chart_name}_good_array"] = chart.is_good_array()
            
                info_dic['reasons'] = ""
                info_dic['reasons_30'] = ""
                
                if chart_name=='chart_d':
                    info_dic['reasons'] += 'is_w20_3w ' if chart.is_w20_3w() else ''
                    info_dic['reasons'] += 'is_w3_ac ' if chart.is_w3_ac() else ''
                    try:
                        if chart.is_sun_ac(n봉전이내=4):
                            info_dic['reasons'] += 'is_sun_ac '
                    except:
                        pass
                    try:
                        if chart.is_coke_ac(n봉전이내=4):
                            info_dic['reasons'] += 'is_coke_ac '
                    except:
                        pass
                    try:
                        if chart.is_multi_through(n봉전이내=4):
                            info_dic['reasons'] += 'is_multi_through ' 
                    except:
                        pass
                    try:
                        if chart.is_abc():
                            info_dic['reasons'] += 'is_abc ' 
                    except:
                        pass
                    try:
                        if chart.is_coke_gcv(bb_width=60):
                            info_dic['reasons'] += 'is_coke_gcv ' 
                    except:
                        pass
                    try:
                        if chart.is_sun_gcv():
                            info_dic['reasons'] += 'is_sun_gcv ' 
                    except:
                        pass
                    try:
                        if chart.is_rsi():
                            info_dic['reasons'] += 'is_rsi ' 
                    except:
                        pass
                    try:
                        if chart.is_new_phase():
                            info_dic['reasons'] += 'is_new_phase ' 
                    except:
                        pass

                if chart_name=='chart_30':
                    try:
                        info_dic['reasons_30'] += 'is_w20_3w ' if chart.is_w20_3w() else ''
                    except:
                        pass
                    
                    try:
                        info_dic['reasons_30'] += 'is_sun_ac ' if chart.is_sun_ac(n봉전이내=10) else ''
                    except:
                        pass
                    try:
                        info_dic['reasons_30'] += 'is_coke_ac ' if chart.is_coke_ac(n봉전이내=10) else ''
                    except:
                        pass
                    try:
                        info_dic['reasons_30'] += 'is_multi_through ' if chart.is_multi_through(n봉전이내=10) else ''
                    except:
                        pass
                    try:
                        info_dic['reasons_30'] += 'is_abc ' if chart.is_abc() else ''
                    except:
                        pass
                    try:
                        info_dic['reasons_30'] += 'is_coke_gcv ' if chart.is_coke_gcv(ma=10, bb_width=30) else ''
                    except:
                        pass
                    try:
                        info_dic['reasons_30'] += 'is_sun_gcv ' if chart.is_sun_gcv(ma=10) else ''
                    except:
                        pass
                    try:
                        info_dic['reasons_30'] += 'is_rsi ' if chart.is_rsi(short_ma=10) else ''
                    except:
                        pass
                    try:
                        info_dic['reasons_30'] += 'is_new_phase ' if chart.is_new_phase(short_ma=10) else ''
                    except:
                        pass

            if item['code'] in exist_qs_dict:
                chartvalue = exist_qs_dict.get(item['code'])
                for field in update_fields:
                    setattr(chartvalue, f"{field}", info_dic.get(f"{field}"))
                to_update.append(chartvalue)
            else:
                chartvalue = ChartValue(**info_dic)
                to_create.append(chartvalue)


            if (len(to_create) + len(to_update)) > 100:
                _create_and_update(to_create, to_update, update_fields)
                to_create=[]
                to_update=[]
                
        if (len(to_create) + len(to_update)) > 0:
            _create_and_update(to_create, to_update, update_fields)
                

  

            
        
    def choice_stock():
        
        # option 장중: 장후:
        # 0~6프로 종목 선정
        codes_6 = []
        for _ in range(5):
            try:
                today_df = DBUpdater.update_ohlcv()
                break
            except:
                print('DBUpdater.update_ohlcv() 재시도.')
                time.sleep(5)
        today_df  = today_df.loc[(today_df['Change'] > 0)  & (today_df['Change'] >= 6) ]
        if len(today_df):
            codes_6 = list(today_df['code'])
        # Chartvalue 에서 데이터 정제해서 가져오기. 
        codes_my_cond = []
        
        # codes_6 와 codes_my_cond 로 조합해야함. 
        codes = []
        
        # 장중에서는 어떻게든 codes list 만들어서 전달. 
        for _ in range(5):
            try:
                df = DBUpdater.update_ohlcv(codes=codes)
                break
            except:
                print('DBUpdater.update_ohlcv(codes) 재시도 ')
                time.sleep(5)
        
        codes = list(df['code'])
        ## 1. 어제분석한 내용 바탕. ( fdr 실시간 데이터.)
        for code in codes_my_cond:
            stock=Stock(code)
            # 기존데이터 바탕으로 분석 시작. ex upper 를 뚫었다던지. 
                
        ## 2. 오늘 등락율 바탕. (pystock 지연데이터 )
        ## 3. 조건검색 바탕. (kis 필요)
        # update ohlcv 하고. 
        
        
        # Stock 객체 만들고. 
        
        ## 특정조건이면 추출하기. 
        
    
        # 
        
        ## 옵션에 따라 메세지 보내고. 
        
        
        pass
    

class GetData:

    async def get_code_info_df_async():
        """
        code_df 가져오기
        """
        all_ls = []

        async def _fetch(url):
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url) as response:
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if "application/json" in content_type:
                            data = await response.json()
                        else:
                            data = await response.text()
            return data

        # ## 레버리지, 인버스 추가.
        # dic = {
        #     "cd": ["A122630", "A252670"],
        #     "nm": ["KODEX 레버리지", "KODEX 200선물인버스2X"],
        #     "gb": ["ETF", "ETF"],
        # }
        # all_ls.append(pd.DataFrame(dic))

        urls = [
            f"http://comp.fnguide.com/SVO2/common/lookup_data.asp?mkt_gb={mkt_gb}&comp_gb=1"
            for mkt_gb in [2, 3]
        ]
        tasks = [_fetch(url) for url in urls]
        datas = await asyncio.gather(*tasks)
        datas = [json.loads(data) for data in datas]  ##  text to json
        datas = sum(datas, [])  # 평탄화. 2차원 리스트 -> 1차원
        all_ls.append(pd.DataFrame(datas))

        df = pd.concat(all_ls)
        df = df.reset_index(drop=True)
        # df = df[df["nm"].str.contains("스팩") == False]  # 스팩 제외
        df = df[~df["nm"].str.contains("스팩")]  # 스팩 제외

        ## 관리종목 거래정지종목 제외하기
        try:
            urls1 = [
                "https://finance.naver.com/sise/trading_halt.naver",  # 거래정지
                "https://finance.naver.com/sise/management.naver",  # 관리종목
            ]
            tasks1 = [_fetch(url) for url in urls1]
            datas1 = await asyncio.gather(*tasks1)
            거래정지_resp, 관리종목_resp = datas1

            거래정지 = pd.read_html(StringIO(거래정지_resp), encoding="cp949")[
                0
            ].dropna()
            거래정지 = 거래정지.filter(regex=r"^(?!.*Unname.*)")

            관리종목 = pd.read_html(StringIO(관리종목_resp), encoding="cp949")[
                0
            ].dropna()
            관리종목 = 관리종목.filter(regex=r"^(?!.*Unname.*)")

            stop_ls = list(관리종목["종목명"]) + list(
                거래정지["종목명"]
            )  # 관리종목 정지종목 리스트

            df = df[~df["nm"].isin(stop_ls)]  ## 제외하기.
        except Exception as e:
            print(f"err {e}")
        df = df.reset_index(drop=True)

        df["cd"] = df["cd"].apply(lambda x: x[1:])
        df = df.filter(regex="cd|nm|^gb")
        df = df.rename(columns={"cd": "code", "nm": "name"})
        return df

    def _get_info_all(code_list: List[Tuple], temp_cnt=None) -> List[Dict]:
        code_list = list(code_list)
        return asyncio.run(GetData._get_info_all_async(code_list))

    async def _get_info_all_async(code_list: List[Tuple], temp_cnt=None) -> List[Dict]:
        """ """

        async def fetch_with_semaphore(
            code, name, semaphore: asyncio.Semaphore, session: aiohttp.ClientSession
        ):
            async with semaphore:
                dic, traderinfo, finstats = await GetData._get_info_async(
                    code, name, session
                )
                dic["name"] = name
                print(f"{name}({code})")
                return dic, traderinfo, finstats

        semaphore = asyncio.Semaphore(5)  # 동시에 최대 10개의 요청을 처리하도록 제한

        if temp_cnt:
            code_list = random.sample(code_list, temp_cnt)

        async with aiohttp.ClientSession() as session:
            tasks = []
            # for idx, row in code_df.iterrows():
            for code, name in code_list:
                tasks.append(
                    asyncio.create_task(
                        fetch_with_semaphore(code, name, semaphore, session)
                    )
                )

            responses = await asyncio.gather(*tasks)

            return responses

    async def _get_info_async(
        code, name, session: aiohttp.ClientSession = None
    ) -> Tuple[Dict]:
        """
        한종목데이터 받기
        """
        if session:
            tasks = [
                GetData._get_naver_info_async(code, name, session),
                GetData._get_fnguide_info_async(code, name, session),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            print("session 생성함 _get_info_async")
            async with aiohttp.ClientSession() as session:
                tasks = [
                    GetData._get_naver_info_async(code, name, session),
                    GetData._get_fnguide_info_async(code, name, session),
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

        dic = {}
        for result in results:
            if isinstance(result, dict):
                dic.update(result)
        dic = {
            k: v if not (type(v) == float and pd.isna(v)) else None
            for k, v in dic.items()
        }  ## np.nan 값이 있다면 None으로 대체하기.
        dic["code"] = code
        dic["name"] = name
        traderinfo = dic.pop("traderinfo") if "traderinfo" in dic.keys() else {}
        finstats = dic.pop("finstats") if "finstats" in dic.keys() else {}

        return dic, traderinfo, finstats

    async def _get_naver_info_async(
        code: str,
        name: str,
        session: aiohttp.ClientSession = None,
    ):
        """
        basic info 가져오기
        data_base_name = 'naver'
        table_name = "basic1"  03.collection 에서 처리.
        """
        code_url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {
            "user_agent": ua.random,
            "referer": "https://finance.naver.com",
        }
        # async with aiohttp.ClientSession() as session:
        if session:
            async with session.get(url=code_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                else:
                    print("response.status: ", response.status)
                    return {}
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url=code_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                    else:
                        print("response.status: ", response.status)
                        return {}

        soup = BeautifulSoup(html, "html.parser")
        dfs = pd.read_html(StringIO(str(soup)))

        ##################################################################################

        selector = "#time > em"
        date_text = soup.select_one(selector).text
        # print(date_text) ## (장중)

        extract_date_text = re.findall(r"[0-9.:]+", date_text)
        # print(extract_date_text) ## (장중)   기대.

        today = pd.to_datetime(extract_date_text[0])
        # print(f'date: {today}')
        # now = pd.to_datetime(' '.join(extract_date_text))

        ################################################################################

        all_dic = {}

        for df in dfs:
            # 시가총액 시가총액순위 상장주식수 액면가
            if Text_mining._contains_text(
                df.to_string(), "+시가총액 +시가총액순위 +상장주식수 +액면가"
            ):
                x = StockFunc.remove_nomean_index_col(df)
                x.columns = [col.split("l")[0] for col in x.columns]
                dic = x.to_dict("records")[0]
                for k, v in dic.items():
                    dic[k] = StockFunc.to_number(v)
                all_dic.update(dic)

            ## 외국인한도주식수 외국인소진율
            elif Text_mining._contains_text(
                df.to_string(), "+외국인한도주식수 +외국인소진율"
            ):
                x = StockFunc.remove_nomean_index_col(df)
                sub_pattern = re.compile("\(.+\)")
                x.columns = [sub_pattern.sub("", col) for col in x.columns]
                dic = x.to_dict("records")[0]
                for k, v in dic.items():
                    dic[k] = StockFunc.to_number(v)
                all_dic.update(dic)

            ## 배당수익율 추정PER
            elif Text_mining._contains_text(df.to_string(), "+배당수익 +추정PER"):
                x = df.transpose()
                x.columns = x.iloc[0]
                x = x.drop(x.index[0])
                dic = {
                    "배당수익율": StockFunc.to_number(
                        x.filter(regex="배당수익").iloc[0, 0]
                    )
                }
                all_dic.update(dic)

            # 동일업종 종목명 -> roe, per pbr ep(주당순이익) - > 동일업종 저per주 정보
            elif Text_mining._contains_text(
                df.to_string(), f"+시가총액 +종목명 +당기순이익 +매출액 +{code}"
            ):
                x = df.set_index(df.columns[0])
                x = x.transpose()
                x = x.filter(regex="ROE|PER|PBR|주당순이익")
                x = x.apply(pd.to_numeric, errors="coerce")
                col_pattern = re.compile(r"\(.+\)")
                x.columns = [col_pattern.sub("", col) for col in x.columns]
                x = x.rename(columns={"주당순이익": "EPS"})
                # 동종업계 저per 주 찾기.
                idx = x["PER"].idxmin()
                pattern = r"(?<=.)\d+$"
                m = re.search(pattern, idx)
                if m:
                    low_per_code = m.group().strip()
                    low_per_name = re.sub(f"{low_per_code}|\*", "", idx).strip()
                # low_per_name, low_per_code = [item.strip() for item in idx.split('*')]
                else:
                    low_per_name, low_per_code = "", ""
                # low_per_name, low_per_code = [item.strip() for item in idx.split('*')]

                # 정보가져오기
                x = x.loc[x.index.str.contains(f"{code}")]
                dic = x.to_dict("records")[0]
                dic["동일업종저per_name"] = low_per_name
                dic["동일업종저per_code"] = low_per_code
                all_dic.update(dic)

            elif Text_mining._contains_text(df.to_string(), "+매도상위 +매수상위"):
                ## 데이터 처리하기.
                df = df.iloc[1:]
                df1 = df.iloc[:, :2].copy()
                df2 = df.iloc[:, 2:].copy()
                df1.columns = ["매도상위", "거래량"]
                df2.columns = ["매수상위", "거래량"]

                temp_text = df1["매도상위"].iat[-1]
                df2["매수상위"].iat[-1] = temp_text
                df1.columns = ["거래원", "매도거래량"]
                df2.columns = ["거래원", "매수거래량"]
                df1 = df1.set_index("거래원")
                df2 = df2.set_index("거래원")

                result_df = pd.concat([df1, df2], axis=1, join="outer")
                result_df = result_df.rename(
                    columns={
                        "매수거래량": "buy",
                        "매도거래량": "sell",
                    }
                )
                result_df = result_df.replace({np.nan: None})

                trader_infodict = {}
                trader_infodict["date"] = today
                trader_infodict["traderinfo"] = result_df.to_dict("index")
                all_dic.update(trader_infodict)

        return all_dic

    async def _get_fnguide_info_async(
        code: str, name: str, session: aiohttp.ClientSession = None
    ):
        """
        return : dict
        """
        url = f"https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A{code}"
        headers = {
            "user_agent": ua.random,
        }
        if session:
            async with session.get(url=url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                else:
                    return
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                    else:
                        return

        soup = BeautifulSoup(html, "html.parser")
        dfs = pd.read_html(StringIO(str(soup)))
        ########################################################################

        all_dic = {}
        all_dic["code"] = code
        all_dic["name"] = name

        finstats_dic = {}

        # 상단 선행per 저보 가져오기.
        selector = "#corp_group2 > dl > dd"
        tags = soup.select(selector)
        tags = [StockFunc.to_number(tag.text) for tag in tags]
        all_dic["PER"], all_dic["PER_12M"], _, all_dic["PBR"], all_dic["배당수익률"] = (
            tags
        )

        selector = "#compBody > div.section.ul_corpinfo > div.corp_group1 > p > span"
        tags = soup.select(selector)
        tags = [tag.text for tag in tags]

        try:
            all_dic["구분"] = tags[1].split(" ")[0]
        except:
            all_dic["구분"] = ""
        try:
            all_dic["업종"] = tags[1].split(" ")[1]
        except:
            all_dic["업종"] = ""
        try:
            all_dic["FICS"] = tags[3].split(" ")[2]
        except:
            all_dic["FICS"] = ""

        #####################################################################
        def modify_finstats_df(df):
            renamed_index_name = "항목"
            x = df.copy()
            if "Annual" in x.to_string():  # 연도데이터이면
                sub_pattern = re.compile(r"\(.+\)")
                x.columns = [sub_pattern.sub("", col[1]) for col in x.columns]
                x.columns = [col.split("/")[0].strip() for col in x.columns]
            elif "Quarter" in x.to_string():  # 분기데이터이면
                sub_pattern = re.compile(r"\(.+\)")
                x.columns = [sub_pattern.sub("", col[1]) for col in x.columns]
            x = x.rename(columns={"IFRS": renamed_index_name})
            x = x.set_index(renamed_index_name)
            x.index = [re.sub(r"\(원\)|\(|\)", "", idx) for idx in x.index]
            x = x.dropna(axis=1, how="all")
            # x = x.fillna(value=None)  ## nan 값을 None으로 ( 데이터베이스 저장시 필요함.)
            # x = x.where(pd.notna(x), None)
            x = x.loc[:, ~x.columns.duplicated(keep='last')]  ## 2023/06 과 2023/12 의 데이터 있을때 연도경우 2023 데이터가 2개 생성되서 중복있다면 마지막데이터만 남기기. 
            for col in x.columns:
                x[col] = pd.to_numeric(x[col], errors="coerce")

            x = x.replace({np.nan: None})
            return x

        ######################################################################

        query_text_dict = {
            "연결연도": "+연결 +Annual -Quarter",
            "연결분기": "+연결 -Annual +Quarter",
            "별도연도": "+별도 +Annual -Quarter",
            "별도분기": "+별도 -Annual +Quarter",
        }

        for df in dfs:
            query_text = "+액면가 +유동주식수 +시가총액 +발행주식수"
            temp_io = StringIO(str(soup))
            if Text_mining._contains_text(df.to_string(), query_text):
                string = Text_mining._extract_table(
                    temp_io,
                    query_text,
                    "발행주식수",
                    col_match=-3,
                )
                all_dic["보통발행주식수"], all_dic["우선발행주식수"] = [
                    StockFunc.to_number(s.strip()) for s in string.split("/")
                ]

                ##################################################
                string = Text_mining._extract_table(
                    temp_io,
                    query_text,
                    "외국인 보유비중",
                    col_match=-1,
                )
                all_dic["외국인보유비중"] = StockFunc.to_number(str(string).strip())

                ####################################################
                string = Text_mining._extract_table(
                    temp_io,
                    query_text,
                    "액면가",
                    col_match=-1,
                )
                all_dic["액면가"] = StockFunc.to_number(str(string).strip())

                ####################################################
                string = Text_mining._extract_table(
                    temp_io,
                    query_text,
                    "유동주식수",
                    col_match=-1,
                )
                all_dic["유동주식수"], all_dic["유동비율"] = [
                    StockFunc.to_number(s.strip()) for s in string.split("/")
                ]
                ####################################################

            ####################################### 재무제표 #################################

            if Text_mining._contains_text(df.to_string(), query_text_dict["연결연도"]):
                x = modify_finstats_df(df)
                finstats_dic["연결연도"] = x.to_dict()

            if Text_mining._contains_text(df.to_string(), query_text_dict["연결분기"]):
                x = modify_finstats_df(df)
                finstats_dic["연결분기"] = x.to_dict()

            if Text_mining._contains_text(df.to_string(), query_text_dict["별도연도"]):
                x = modify_finstats_df(df)
                finstats_dic["별도연도"] = x.to_dict()

            if Text_mining._contains_text(df.to_string(), query_text_dict["별도분기"]):
                x = modify_finstats_df(df)
                finstats_dic["별도분기"] = x.to_dict()

        if finstats_dic:
            all_dic["finstats"] = finstats_dic
        return all_dic

    async def _get_investor_async(
        semaphore: asyncio.Semaphore, investor, str_date=None
    ):
        """
        investor : '외국인'
        개별데이터 받기
        """

        if str_date == None:
            str_date = pd.Timestamp.now().date()
            str_date = str_date.strftime("%Y%m%d")
        else:
            str_date = pd.to_datetime(str_date).strftime("%Y%m%d")

        async with semaphore:
            # logger.info(f'{str_date} {investor} download.... ' )
            result_df = await asyncio.to_thread(
                functools.partial(
                    pystock.get_market_net_purchases_of_equities,
                    str_date,
                    str_date,
                    "ALL",
                    investor,
                )
            )
            result_df["투자자"] = investor
            result_df["날짜"] = str_date
            result_df = result_df.reset_index()
        return result_df

    async def _get_investor_all_async(date: List = None):
        """
        date 의 투자자 전체 데이터.
        """

        if date is None:
            date = pd.Timestamp.now().date()
        dates = [date] if not isinstance(date, list) else date
        str_dates = [pd.to_datetime(date).strftime("%Y%m%d") for date in dates]

        text = "개인/외국인/기관합계/금융투자/투신/연기금/보험/사모/은행/기타금융/기타법인/기타외국인"

        semaphore = asyncio.Semaphore(5)
        try:
            investor_ls = text.split("/")
            tasks = [
                asyncio.create_task(
                    GetData._get_investor_async(
                        semaphore=semaphore, investor=investor, str_date=str_date
                    )
                )
                for investor in investor_ls
                for str_date in str_dates
            ]
            result = await asyncio.gather(*tasks)
            result_df = pd.concat(result)
            result_df = result_df.reset_index(drop=True)
            if len(result_df):
                result_df = result_df.rename(columns={"티커": "code"})
                result_df["날짜"] = pd.to_datetime(result_df["날짜"])
            else:
                pass
        except:
            # logger.error(f"{date} 데이터가 존재하지 않습니다.")
            return pd.DataFrame()
        return result_df

    ## ISSUE
    def get_iss_list():
        # 최근이슈리스트 가져오기.
        url = "https://api.thinkpool.com/analysis/issue/recentIssueList"
        params = {
            "user_agent": ua.random,
            "referer": "https://www.thinkpool.com/",
        }
        resp = requests.get(url, params=params)
        js = resp.json()

        ## 데이터 정리
        all_ls = []
        for item in js:
            temp_dic = {}
            temp_dic["issn"] = item["issn"]
            temp_dic["iss_str"] = item["is_str"]
            temp_dic["hl_str"] = item["hl_str"]
            temp_dic["regdate"] = item["regdate"]
            temp_dic["ralated_codes"] = ",".join(
                [dic["code"] for dic in item["ralatedItemList"]]
            )
            temp_dic["ralated_code_names"] = ",".join(
                [dic["codeName"] for dic in item["ralatedItemList"]]
            )
            all_ls.append(temp_dic)

        ## 데이터가공
        iss_df = pd.DataFrame(all_ls)
        iss_df["regdate"] = iss_df["regdate"].str.split(" ", expand=True)[0]
        # pd.to_datetime(iss_df['regdate1'])
        iss_df["regdate"] = iss_df["regdate"].str.replace("/", "")
        return iss_df

    def get_iss_from_number(issn):
        """
        이슈넘버로 이슈헤드라인 가져오기.
        """
        url = f"https://api.thinkpool.com/analysis/issue/headline?issn={issn}"
        params = {
            "user_agent": ua.random,
            "referer": "https://www.thinkpool.com/",
        }
        resp = requests.get(url, params=params)
        js = resp.json()

        try:
            js["regdate"] = pd.to_datetime(js["hl_date"]).date()
        except:
            js["regdate"] = js["hl_date"]
        try:
            js["hl_cont_text"] = re.findall(".+(?=<[aA] href=)", js["hl_cont"])[0]
        except:
            js["hl_cont_text"] = js["hl_cont"]
        try:
            js["hl_cont_url"] = re.findall(
                '(?<=<[aA] href=").+(?=" *target)', js["hl_cont"]
            )[0]
        except:
            js["hl_cont_url"] = ""

        # 필요없는 데이터 제거
        del_result1 = js.pop(
            "hl_cont", "not_found"
        )  # 'country' 키가 없으면 'Not Found' 반환
        del_result2 = js.pop(
            "hl_date", "not_found"
        )  # 'country' 키가 없으면 'Not Found' 반환

        return js

    # 이슈연관 종목정보.
    def get_iss_related(issn):
        """
        이슈의 관련주정보 가져오기.
        """
        all_ls = []
        params = {
            "user_agent": ua.random,
            "referer": "https://www.thinkpool.com/",
        }
        # issn = 207
        url = f"https://api.thinkpool.com/analysis/issue/ralatedItemSummaryList?issn={issn}&pno=1"
        resp = requests.get(url, params=params)
        js = resp.json()

        totalcnt = js["totalCount"]
        ls = js["list"]  ## 최초자료.
        all_ls += ls

        try:
            loop_cnt = (
                ((totalcnt - 1) - 10) // 10
            ) + 1  ## 최초를 제외하고 몇번을 더 받아야하믐지 계산.
            if totalcnt > len(ls):
                for pno in range(2, 2 + loop_cnt):
                    url = f"https://api.thinkpool.com/analysis/issue/ralatedItemSummaryList?issn={issn}&pno={pno}"
                    resp = requests.get(url, params=params)
                    js = resp.json()
                    ls = js["list"]
                    all_ls += ls
        except Exception as e:
            pass
        new_all_ls = []
        for dic in all_ls:
            dic["otherIssueListName"] = ",".join(
                [dic1["is_str"] for dic1 in dic["otherIssueList"]]
            )
            dic["otherIssueList"] = ",".join(
                [str(dic1["issn"]) for dic1 in dic["otherIssueList"]]
            )
            new_all_ls.append(dic)
        result = pd.DataFrame(new_all_ls)
        return result

    async def _get_group_list_acync(group="theme"):
        """
        theme 또는 upjong 별로 관련 url 가져오기
        """
        url = f"https://finance.naver.com/sise/sise_group.naver?type={group}"
        r = await asyncio.to_thread(functools.partial(requests.get, url))

        if r.status_code == 200:
            try:
                soup = BeautifulSoup(r.text, "html5lib")
            except:
                soup = BeautifulSoup(r.text, "html.parser")

            selector = "#contentarea_left > table >  tr > td>  a"  ### 변경 주의.
            tags = soup.select(selector)
            if not len(tags):
                selector = "#contentarea_left > table > tbody >  tr > td>  a"
                tags = soup.select(selector)

            if not len(tags):
                return []

            basic_url = "https://finance.naver.com"
            ls = []
            for tag in tags:
                detail_url = basic_url + tag["href"]
                ls.append((tag.text, detail_url))
            return ls
        else:
            return []

    async def _get_theme_codelist_from_theme_async(name, url_theme):
        """
        input : theme(upjong), url
        return : list (dict) theme(upjong)name , code, code_name
        """
        r = await asyncio.to_thread(functools.partial(requests.get, url_theme))
        # r = requests.get(url_theme)
        if r.status_code == 200:
            print(f"{name}_succeed!")
        try:
            soup = BeautifulSoup(r.text, "html5lib")
        except:
            soup = BeautifulSoup(r.text, "html.parser")

        selector = "#contentarea > div:nth-child(5) > table > tbody > tr"
        table_tag = soup.select(selector)

        ls = []
        for tag in table_tag:
            dic = {}
            try:
                code_name = tag.select("td.name > div > a")[0].text
                code = tag.select("td.name > div > a")[0]["href"].split("=")[-1]
                try:
                    theme_text = tag.select("p.info_txt")[0].text
                except:
                    pass
                dic["name"] = name
                dic["code"] = code
                dic["code_name"] = code_name
                try:
                    dic["theme_text"] = theme_text
                except:
                    pass
                ls.append(dic)
            except:
                pass
        return ls

    async def get_all_upjong_theme(temp_cnt: int = 0):
        """
        네이버 theme upjong 전체데이터 가져오기
        return : theme_data, upjong_data
        """

        tasks1 = [
            GetData._get_group_list_acync("theme"),
            GetData._get_group_list_acync("upjong"),
        ]
        result1 = await asyncio.gather(*tasks1)
        theme_ls, upjong_ls = result1

        if temp_cnt:
            theme_ls = theme_ls[:temp_cnt]
            upjong_ls = upjong_ls[:temp_cnt]

        # #theme_ls 작업
        tasks_ls = []
        n = 20
        # task 분할.
        for i in range(0, len(theme_ls), n):
            tasks = [
                GetData._get_theme_codelist_from_theme_async(name, url)
                for name, url in theme_ls[i : i + n]
            ]
            tasks_ls.append(tasks)
        # 분할된 task 작업
        result_task = []
        for task in tasks_ls:
            result = await asyncio.gather(*task)
            result_task.append(result)
        # # 결과 취합.
        # theme_result_df = pd.DataFrame(
        #     [data for result in result_task for datas in result for data in datas]
        # )
        theme_data = [
            data for result in result_task for datas in result for data in datas
        ]

        # #upjong_ls 작업
        tasks_ls = []
        # task 분할.
        for i in range(0, len(upjong_ls), n):
            tasks = [
                GetData._get_theme_codelist_from_theme_async(name, url)
                for name, url in upjong_ls[i : i + n]
            ]
            tasks_ls.append(tasks)
        # 분할된 task 작업
        result_task = []
        for task in tasks_ls:
            result = await asyncio.gather(*task)
            result_task.append(result)
        # 결과 취합.
        # upjong_result_df = pd.DataFrame(
        #     [data for result in result_task for datas in result for data in datas]
        # )
        upjong_data = [
            data for result in result_task for datas in result for data in datas
        ]

        return theme_data, upjong_data

    def get_ohlcv_all_market(date):

        try:
            date = pd.to_datetime(date).strftime("%Y%m%d")
        except Exception as e:
            return pd.DataFrame()

        # df = pystock.get_market_ohlcv(date, market="ALL")  ##이 데이터는  konex 포함되어있다.
        try:
            all_data = [
                pystock.get_market_ohlcv(date, market=market)
                for market in ["KOSPI", "KOSDAQ"]
            ]
            df = pd.concat(all_data)
            rename_col = {
                "티커": "code",
                "시가": "Open",
                "고가": "High",
                "저가": "Low",
                "종가": "Close",
                "거래량": "Volume",
                "거래대금": "Amount",
                "등락률": "Change",
            }
            df1 = df.reset_index()
            df1["Date"] = date

            df1 = df1.rename(columns=rename_col)
            df1["Date"] = pd.to_datetime(df1["Date"])

            ## 전처리
            df1 = df1.loc[df1["Volume"] != 0]
            col = [
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Amount",
                "Change",
                "code",
            ]
            df1 = df1[col]
            return df1
        except Exception as e:
            return pd.DataFrame()

    def get_ohlcv_all_market_from_fdr(codes):
        
        semaphore = asyncio.Semaphore(5) 
        async def async_fdr_datareader(semaphore, code, today):
            async with semaphore:
                result = await asyncio.to_thread(fdr.DataReader, code, today)
                result['code'] = code
                return result
            
        async def async_fdr_datareader_all(semaphore, codes):
            today = pd.Timestamp.now().date()
            tasks = [asyncio.create_task(async_fdr_datareader(semaphore, code, today)) for code in codes]
            results = await asyncio.gather(*tasks)
            df = pd.concat(results)
            df.reset_index(inplace=True)
            return df            
        
        result_df = asyncio.run(async_fdr_datareader_all(semaphore, codes))
        return result_df
        
        
    async def _get_news_from_stockplus_today():
        """
        news
        """
        url = "https://mweb-api.stockplus.com/api/news_items/all_news.json?scope=popular&limit=1000"
        params = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession() as session:
            # async with session.get(url=url, headers=headers, params=params) as response:
            async with session.get(url=url, params=params) as response:
                if response.status == 200:
                    # js = await response.json(content_type='text/html') # 이건 실행안됨.
                    js = await response.json()
                else:
                    return

        datas = js["newsItems"]
        for data in datas:
            data["relatedStocks"] = [
                item["shortCode"][1:] for item in data["relatedStocks"]
            ]

        ## 시간 처리 field 처리위해 df 변환
        df = pd.DataFrame(datas)
        df["createdAt"] = pd.to_datetime(df["createdAt"]).dt.tz_convert("Asia/Seoul")
        df = df.sort_values(by="createdAt")

        col = ["id", "title", "createdAt", "writerName", "relatedStocks"]
        df = df[col]
        df = df.rename(columns={"id": "no"})

        # url = 'https://news.stockplus.com/m?news_id={id}'  #  url은 생성하면 된다. 저장해야하나.?

        df["createdAt"] = pd.to_datetime(df["createdAt"]).dt.tz_convert("Asia/Seoul")
        # df["createdAt"] = df["createdAt"].apply(lambda x: x.tz_localize(None))
        df = df.sort_values(by="createdAt")

        return df.to_dict("records")

    def get_ohlcv_min(code, data_type, limit=480):
        option_dic = {
            "월봉": "months",
            "주봉": "weeks",
            "일봉": "days",
            "60분봉": "60/minutes",
            "30분봉": "30/minutes",
            "15분봉": "15/minutes",
            "5분봉": "5/minutes",
        }
        acode = "A" + code
        str_option = option_dic[data_type]
        url = f"http://finance.daum.net/api/charts/{acode}/{str_option}"
        params = {"limit": f"{limit}", "adjusted": "true"}
        headers = {
            "referer": "https://finance.daum.net/chart/",
            "user-agent": "Mozilla/5.0",
        }

        # async with aiohttp.ClientSession() as session:
        #     async with session.get(url=url, headers=headers, params=params) as response:
        #         if response.status == 200:
        #             data = await response.json()
        #         else:
        #             return pd.DataFrame()

        data = requests.get(url=url, headers=headers, params=params)
        if data.status_code == 200:
            data = data.json()
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


if __name__ == "__main__":
    DBUpdater.update_ticker()
