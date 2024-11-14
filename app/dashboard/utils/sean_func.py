from typing import Optional
import re
import glob
import os
import asyncio
import concurrent.futures
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
# import aiofiles
from IPython.display import display, HTML
from datetime import datetime
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from pykrx import stock as pystock

CURRENT_DIR = Path(__file__).resolve().parent


def setup_logger(
    name: str,
    level=logging.INFO,
    log_file=None,
    max_bytes=5 * 1024 * 1024,
    backup_count=3,
):
    """
    로거를 설정하는 함수

    Parameters:
    - name (str): 로거의 이름
    - log_file (str): 로그 파일 경로
    - level (logging level): 로그 레벨 (디폴트: logging.INFO)
    - max_bytes (int): 로그 파일의 최대 크기 (디폴트: 5MB)
    - backup_count (int): 로그 파일의 백업 개수 (디폴트: 3)

    Returns:
    - logger: 설정된 로거 객체

    == level ==
    logging.DEBUG: 10
    logging.INFO: 20
    logging.WARNING: 30
    logging.ERROR: 40
    logging.CRITICAL: 50

    DEBUG: 상세한 정보, 주로 진단을 위해 사용됩니다.
    INFO: 일반적인 정보 메시지입니다.
    WARNING: 경고 메시지, 잠재적인 문제를 나타냅니다.
    ERROR: 오류 메시지, 실패한 작업을 나타냅니다.
    CRITICAL: 심각한 오류 메시지, 프로그램이 실행을 계속할 수 없을 정도로 심각한 문제를 나타냅니다.
    """
    
    # 로그파일경로 없으면 만들기
    # "/Users/sean/class/django_lee/1/mystock/utils/log/_get_investor_all_async.txt"
    
    folder_path_name = Path(CURRENT_DIR / "log")
    if not os.path.exists(folder_path_name):
        os.makedirs(folder_path_name)

    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 포맷터 생성
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 콘솔 핸들러 생성 및 설정
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    # 로거에 핸들러 추가
    logger.addHandler(console_handler)

    # 파일 핸들러 생성 및 설정 (로테이팅 파일 핸들러)
    if log_file is not None:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        # 로거에 핸들러 추가
        logger.addHandler(file_handler)

    return logger


def is_business_day():
    result = True
    today = pd.Timestamp.today().date()
    business_days = [
        item.date()
        for item in pystock.get_previous_business_days(
            year=today.year, month=today.month
        )
    ]
    if not today in business_days:
        result = False
    return result


def to_async(sync_func):
    @wraps(sync_func)
    async def async_func(*args, **kwargs):
        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor()
        asyncio.to_thread(sync_func)
        return await loop.run_in_executor(executor, sync_func, *args, **kwargs)

    return async_func


# # 동기 함수 예시 --> 아래와같은동기함수가 있다면
# def sync_function(i : int):
#     result = i+i
#     print(result)
#     return i+i

# @to_async   ## --> 이렇게 데코레이션을 붙이면 비동기함수가 됨. -- > 주의해야할점은 데코레이션이 붙는 함수는 def 로 한다. (async def 아님.)
# def async_function(i : int):
#     result= sync_function(i)
#     return result


class Text_mining:

    def _contains_text(io, expr):
        """
        text: 대상 텍스트 (혹은 문자열 리스트)
        expr: 문자열 (단어의 포함 여부 표현식: "내재 +포함 -제외")
        """
        # expr 문자열 파싱 ("내재 +포함 -제외")
        tokens = expr.split()

        includes, excludes, contains = [], [], []
        for t in tokens:
            if t.startswith("+"):
                includes.append(t[1:])
            elif t.startswith("-"):
                excludes.append(t[1:])
            else:
                contains.append(t)

        # 내재(contain), 포함(include), 제외(exclude) 정규식 연산
        re_con = re.compile("|".join([c for c in contains]))
        re_exc = re.compile(
            "^(" + "".join(["(?!%s)" % e for e in excludes]) + ".)*$"
            if excludes
            else ""
        )
        re_inc = re.compile("".join(["(?=.*%s)" % i for i in includes]))

        if type(io) is str:
            text = io
            text = re.sub("\n|\r", " ", text)
            b_con = bool(re_con.search(text))
            b_exc = bool(re_exc.search(text))
            b_inc = bool(re_inc.search(text))
            return b_con and b_exc and b_inc
        elif type(io) is list:
            result = []
            for text in io:
                b_con = bool(re_con.search(text))
                b_exc = bool(re_exc.search(text))
                b_inc = bool(re_inc.search(text))
                result.append(b_con and b_exc and b_inc)
            return result
        return False

    def _extract_table(
        io, tab_match, row_match=0, col_match=-1, encoding=None, verbose=False
    ):
        """
        * io: 대상 페이지 URL, 혹은 HTML 텍스트 문자열
        * tab_match: 테이블 매칭 문자열
        * row_match: 로우 매칭 문자열 (기본값: 0, 첫 행)
        * col_match: 컬럼 매칭 문자열 (기본값: -1, 가장 오른쪽 컬럼)
        * verbose: 과정 상세 출력 (기본값:False)
        """
        result = ""

        # 1) 테이블(table) 식별하기
        the_table = None
        for df in pd.read_html(io, encoding=encoding):
            if Text_mining._contains_text("".join(df.to_string().split()), tab_match):
                the_table = df
                break
        if the_table is None:
            display(HTML(f"table not found for `{tab_match}`")) if verbose else ""
            return ""

        (
            display(HTML(f"<h2>Table found</h2>{the_table.to_html()}<hr>"))
            if verbose
            else ""
        )

        # 2) 로우(row) 식별하기 (ix: int, row: pandas.Series)
        the_row = None
        if type(row_match) is int:  # 정수를 지정하면, 지정한 행
            the_row = the_table.iloc[row_match] if len(the_table) > row_match else None
        elif type(row_match) is str:  # 문자열을 지정하면 매칭된 행
            for ix, row in the_table.iterrows():
                if Text_mining._contains_text("".join(str(row).split()), row_match):
                    the_row = row
                    break
        if the_row is None:
            display(HTML(f"Unsupprted `row_match`")) if verbose else ""
            return ""
        else:
            display(HTML(f"<h2>Row found</h2>{the_row.values}<hr>")) if verbose else ""

        # 3) 컬럼(column) 식별하기
        result = ""
        if type(col_match) is int:  # 정수를 지정하면, 지정한 컬럼값
            result = the_row.iloc[col_match] if the_row is not None else ""
        elif type(col_match) is str:  # 문자열을 지정하면 베스트 매칭된 컬럼값
            for col_key in the_row.keys():
                if Text_mining._contains_text("".join(str(col_key).split()), col_match):
                    the_col = col_key
                    break
            result = the_row[the_col]
            # display(HTML(f'<h2>Column found</h2><b>key=</b>{found},<b>value=</b>{result}({str(type(result))})<hr>')) if verbose else ''
            (
                display(
                    HTML(
                        f"<h2>Column found</h2><b>key=</b>found,<b>value=</b>{result}({str(type(result))})<hr>"
                    )
                )
                if verbose
                else ""
            )
        else:
            display(HTML(f"Unsupprted `col_match`")) if verbose else ""

        return int(result) if type(result) is str and result.isdigit() else result


class Sean_func:
    """
    기능
    여러가지 간단 계산 기능 넣기.
    자주쓰는 날짜계산.
    실적분기계산.
    과거거래날짜로 n봉 날짜지정.
    휴장일 체크
    """

    def setup_logger(
        name, log_file, level=logging.INFO, max_bytes=5 * 1024 * 1024, backup_count=3
    ):
        """
        로거를 설정하는 함수

        Parameters:
        - name (str): 로거의 이름
        - log_file (str): 로그 파일 경로
        - level (logging level): 로그 레벨 (디폴트: logging.INFO)
        - max_bytes (int): 로그 파일의 최대 크기 (디폴트: 5MB)
        - backup_count (int): 로그 파일의 백업 개수 (디폴트: 3)

        Returns:
        - logger: 설정된 로거 객체
        """

        # 로거 생성
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 포맷터 생성
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 콘솔 핸들러 생성 및 설정
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # 파일 핸들러 생성 및 설정 (로테이팅 파일 핸들러)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)

        # 로거에 핸들러 추가
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

        # # 사용 예시
        # if __name__ == "__main__":
        #     logger = setup_logger('my_logger', 'my_log.log', level=logging.DEBUG)

        #     logger.debug("This is a debug message")
        #     logger.info("This is an info message")
        #     logger.warning("This is a warning message")
        #     logger.error("This is an error message")
        #     logger.critical("This is a critical message")

    def get_text_between_words(start_marker, end_marker, text):
        pattern = re.escape(start_marker) + r"(.*?)" + re.escape(end_marker)
        match = re.search(pattern, text)
        if match:
            extracted_text = match.group(1)
        else:
            extracted_text = ""
        return extracted_text

    # async def aread(file_name, mode="r"):
    #     """
    #     단순 파일 비동기 read하기
    #     """
    #     async with aiofiles.open(file_name, mode=mode) as f:
    #         read_data = await f.read()
    #     return read_data

    # async def areads(file_names, mode="r"):
    #     """
    #     여러파일 비동기 파일 읽기.
    #     return dict {파일명 : 데이터, 파일명 : 데이터 ....},
    #     """
    #     tasks = [
    #         asyncio.create_task(Sean_func.aread(file_name, mode=mode))
    #         for file_name in file_names
    #     ]
    #     results = await asyncio.gather(*tasks)
    #     only_file_names = [file.split("/")[-1].split(".")[0] for file in file_names]
    #     result_dic = dict(zip(only_file_names, results))

    #     # 데이터를 받고 데이터에 따라 dict comprehenshion으로 데이터 처리해야함.
    #     # result = {name: pickle.loads(content) for name, content in result_contents.items()}

    #     return result_dic

    # def corr_text(text1, text2, exception= None):
    #     '''
    #     exception : list or tuple text
    #     '''
    #     ## 코사인 유사도
    #     if exception != None:
    #         for ex_t in exception:
    #             text1 = text1.replace(ex_t,"")
    #             text2 = text2.replace(ex_t,"")
    #         text1 = text1.strip()
    #         text2 = text2.strip()

    #     answer_string = text1
    #     input_string = text2

    #     sentences = (answer_string, input_string)

    #     tfidf_vectorizer = TfidfVectorizer()
    #     tfidf_matrix = tfidf_vectorizer.fit_transform(sentences)
    #     cos_similar = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    #     # print("코사인 유사도 측정")
    #     # print('코사인유사도', cos_similar[0][0])
    #     코사인유사도 = cos_similar[0][0]

    #     ## 자카드 유사도
    #     intersection_cardinality = len(set.intersection(*[set(answer_string), set(input_string)]))
    #     union_cardinality = len(set.union(*[set(answer_string), set(input_string)]))
    #     similar = intersection_cardinality / float(union_cardinality)

    #     # print('자카도유사도:' , similar)
    #     자카도유사도 = similar

    #     ### 시퀀스
    #     answer_bytes = bytes(answer_string, 'utf-8')
    #     input_bytes = bytes(input_string, 'utf-8')
    #     answer_bytes_list = list(answer_bytes)
    #     input_bytes_list = list(input_bytes)

    #     sm = difflib.SequenceMatcher(None, answer_bytes_list, input_bytes_list)
    #     similar = sm.ratio()

    #     # print('시퀀스유사도', similar)
    #     시퀀스유사도 = similar

    #     # ##max 0.5이상 min_ 0.2 이상
    #     # if max(코사인유사도, 자카도유사도, 시퀀스유사도) >= 0.5 :
    #     #     if min(코사인유사도, 자카도유사도, 시퀀스유사도) >= 0.2:
    #     #         return True
    #     # return False
    #     코사인유사도 = round(코사인유사도,3)
    #     자카도유사도 = round(자카도유사도,3)
    #     시퀀스유사도 = round(시퀀스유사도,3)
    #     # return (코사인유사도, 자카도유사도, 시퀀스유사도),max(코사인유사도, 자카도유사도, 시퀀스유사도)
    #     return 코사인유사도, 자카도유사도, 시퀀스유사도

    # def remove_duplicate_sequences(row_df,compair_col_name,ignore_words=[],except_words=[]):
    #     '''
    #     # 중복 데이터 중 하나를 남기고 제거하는 함수
    #     ignore_words : 중복 비교할때 무시할 문자 ( 보통 종목명, )
    #     except_words : 특정문자 포함시 행을 아예 제외함.
    #     '''
    #     if not len(row_df):
    #         return row_df
    #     if len(ignore_words):
    #         df = row_df.copy()
    #         for word in ignore_words:
    #             df[compair_col_name]= df[compair_col_name].str.replace(word,"", regex=True)
    #     else:
    #         df = row_df.copy()
    #     df[compair_col_name] = df[compair_col_name].str.replace(r'\[.*?\]', '', regex=True) # []포함  문자 제거하기
    #     df[compair_col_name] = df[compair_col_name].str.replace(r'\(.*?\)', '', regex=True) # []포함  문자 제거하기

    #     unique_sequences = []
    #     similar_rows = []

    #     for index, row in df.iterrows():
    #         sequence = row[compair_col_name]
    #         is_similar = False

    #         for unique_seq in unique_sequences:
    #             similarity_ratio = difflib.SequenceMatcher(None, sequence, unique_seq).ratio()
    #             if (similarity_ratio >= 0.7) | (len(sequence) <= 4):
    #                 # print(sequence, "|||||", unique_seq)
    #                 similar_rows.append(index)
    #                 is_similar = True
    #                 break

    #         if not is_similar:
    #             unique_sequences.append(sequence)
    #         else:
    #             pass
    #             # print("제외되는 문장:", sequence)

    #     df_unique = row_df.drop(similar_rows)
    #     # print('제거되는 데이터',similar_rows)

    #     ## 특정문자포함 기사 제거
    #     if len(except_words):
    #         string =""
    #         for x in except_words:
    #             string += f"{x}|"
    #         string = string[:-1]
    #         # print('except string:',string)
    #         df_unique = df_unique.loc[~df_unique[compair_col_name].str.contains(f'{string}')]

    #     # 짧은기사 제거
    #     df_unique = df_unique.loc[~df_unique[compair_col_name].str.len()<=11]
    #     # print(df_unique[compair_col_name])
    #     return df_unique

    def split_text(text, n=80):
        """
        긴 text 를 n개로 줄바꿈해줌.
        """
        ls = []
        if len(text) > n:
            for i in range(0, len(text), n):
                ls.append(text[i : i + 30])
            text = "\n".join(ls)
            text = text.strip()
            return text
        else:
            return text

    # def _get_휴장일():
    #     """
    #     return : DataFrame
    #     date_columns:"calnd_dd_dy"
    #     매달 1일 실행.
    #     ##### 일단 크롤링이 안됨. 그냥 일단 데이터 받아놓고 사용하자.!   수정필요!!!1
    #     """
    #     try:
    #         # this_year = datetime.today().year
    #         this_year = pd.Timestamp.now().year

    #         url = "http://open.krx.co.kr/contents/COM/GenerateOTP.jspx?bld=MKD%2F01%2F0110%2F01100305%2Fmkd01100305_01&name=form&_=1678631887496"
    #         params = {
    #             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    #         }
    #         resp = requests.get(url, headers=params)
    #         r_code = resp.text

    #         url = "http://open.krx.co.kr/contents/OPN/99/OPN99000001.jspx"
    #         params = {
    #             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36X-Requested-With: XMLHttpRequest"
    #         }

    #         data = {
    #             "search_bas_yy": this_year,
    #             "gridTp": "KRX",
    #             "pagePath": "/contents/MKD/01/0110/01100305/MKD01100305.jsp",
    #             "code": r_code,
    #         }

    #         rep = requests.post(url, headers=params, data=data)

    #         js = rep.json()["block1"]

    #         # save data
    #         if len(js):
    #             result = pd.DataFrame(js)

    #             try:
    #                 data_path = os.path.dirname(os.path.realpath(__file__))
    #                 file_name = f"{data_path}/datas/not_business_day.csv"
    #                 result.to_csv(file_name, index=False)
    #                 print(f"{file_name} 저장성공")
    #             except Exception:
    #                 print(f"{file_name} 저장실패")
    #             result["calnd_dd_dy"] = pd.to_datetime(result["calnd_dd_dy"])

    #     except Exception as e:
    #         result = pd.DataFrame()
    #         print(e)
    #     return result

    # def _is_휴장일(date=None):
    #     """
    #     휴장일 체크
    #     """
    #     result = False
    #     data_path = os.path.dirname(os.path.realpath(__file__))
    #     file_name = f"{data_path}/datas/not_business_day.csv"
    #     try:
    #         data = pd.read_csv(file_name)
    #         data["calnd_dd_dy"] = pd.to_datetime(data["calnd_dd_dy"])
    #     except:
    #         try:
    #             Sean_func._get_휴장일()
    #             data = pd.read_csv(file_name)
    #             data["calnd_dd_dy"] = pd.to_datetime(data["calnd_dd_dy"])
    #             print('데이터 새로저장됨.')
    #         except:
    #             return False
    #     if date != None:
    #         today = pd.to_datetime(date)
    #     else:
    #         today = pd.to_datetime(datetime.today().date())

    #     if today in list(data["calnd_dd_dy"]):
    #         print("휴장일입니다.")
    #         result = True
    #     if (today.weekday() == 5) | (today.weekday() == 6):
    #         print("주말입니다.")
    #         result = True
    #     return result

    def _split_data(split_able_data, division_n):
        """
        data를 n 개만큼 나눠주는 함수.
        indexing 가능한 list , df 등에 사용가능.

        """
        ls = []
        try:
            if len(split_able_data) < division_n:
                ls.append(split_able_data)
            else:
                boundary_int = [
                    int(len(split_able_data) * i / division_n)
                    for i in range(division_n + 1)
                ]
                #         print('boundara_int',boundary_int)
                for i in range(division_n):
                    split_data = split_able_data[boundary_int[i] : boundary_int[i + 1]]
                    ls.append(split_data)
            return ls
        except:
            print("데이터를 나눌 수가 없습니다. 원본을 반환합니다.")
            return split_able_data

    # def _get_time_KST():
    #     KST = pytz.timezone("Asia/Seoul")
    #     return datetime.now(KST)

    def _find_current_os():
        """
        return : macos, windows, linux
        """

        import platform

        system_name = platform.system()

        if system_name == "Darwin":
            return "macos"
        elif system_name == "Windows":
            return "windows"
        else:
            return "linux"

    def _find_difference_two_df(a_df, b_df, **cols):
        """
        a_df : 이전 df  숫자만.
        b_df : 최근 df
        **cols : return되는 df 에 columns 추가할시 dict형태로 임의 임력. ex) 구분 = '분기', 날짜 = '20200101'
        prepare_idx :  비교할 인덱스 입력,
        """
        if len(cols):
            keys = list(cols.keys())
            values = list(cols.values())
        else:
            keys = []
            values = []

        if list(a_df.index) != list(b_df.index) or list(a_df.columns) != list(
            b_df.columns
        ):
            print("데이터가 같지 않아 비교할수 있는데이터만 비교합니다. ")

        ## 공통인덱스, 컬럼
        common_index = list(set(a_df.index) & set(b_df.index))
        common_columns = list(set(a_df.columns) & set(b_df.columns))
        common_index.sort()
        common_columns.sort()

        a_df = a_df.loc[common_index, common_columns]
        b_df = b_df.loc[common_index, common_columns]

        a_df.replace(np.nan, 0, inplace=True)
        b_df.replace(np.nan, 0, inplace=True)

        c_df = b_df != a_df

        ## 변화값행렬만 남기기 위해 필요없는 행렬 제거
        c_df = c_df.replace(False, np.nan)
        c_df.dropna(axis=1, how="all", inplace=True)
        c_df.dropna(axis=0, how="all", inplace=True)

        ## 변화값 저장.
        result_ls = []
        for idx in c_df.index:
            for col in c_df.columns:
                value = c_df.loc[idx, col]
                if value == True:
                    before_value = a_df.loc[idx, col]
                    after_value = b_df.loc[idx, col]
                    try:
                        변화량 = after_value - before_value
                    except:
                        변화량 = 0

                    result_ls.append(
                        values + [idx, col, before_value, after_value, 변화량]
                    )

        ## 날짜시간 추가. 필요.
        if len(result_ls):
            result_df = pd.DataFrame(
                result_ls, columns=keys + ["row", "col", "이전값", "최근값", "변화량"]
            )
        else:
            result_df = pd.DataFrame()
        return result_df

    def _last_xlfile_to_df(path, part_of_filename):
        """
        폴더(path)내 특정이름이 포함된파일 중 가장최근 엑셀파일을 dataframe으로 반환
        """
        if path[-1] != "/":
            path = path + "/"
        path = path
        # last_file_name = '파일이름.확장자
        temp_file_name = (
            "*" + part_of_filename.split(".")[0] + "*." + part_of_filename.split(".")[1]
        )
        temp_file_name = path + temp_file_name

        file_name_list = glob.glob(temp_file_name)
        last_file_name = max(file_name_list, key=os.path.getctime)
        # code_df = pd.read_excel(last_file_name).set_index('code')
        code_df = pd.read_excel(last_file_name, index_col=0)

        return code_df

    def _실적기준구하기(YorQ="y"):
        """
        -1 은 과거. 0번째는 현재, 1번째는 다음
        선행주가월수 수정해서사용가능.
        return :  ('2020','2020')  or ('2020/06', '2021/03', '2021/06')
        """
        if YorQ in ["Y", "y", "연도", "년"]:
            YorQ = "y"
        elif YorQ in ["Q", "q", "분기"]:
            YorQ = "q"
        else:
            print("YorQ 값을 잘못입력하였습니다.")

        def make_Q(day):
            if day.month in [1, 2, 3]:
                ret = str(day.year) + "/03"
            elif day.month in [4, 5, 6]:
                ret = str(day.year) + "/06"
            elif day.month in [7, 8, 9]:
                ret = str(day.year) + "/09"
            elif day.month in [10, 11, 12]:
                ret = str(day.year) + "/12"
            else:
                ret = None
            return ret

        # today = datetime.today()
        today = pd.Timestamp.now().today()

        if YorQ == "y":
            분류기준월 = 6
            if today.month < 분류기준월:
                cur_year = today.year
            else:
                cur_year = today.year + 1
            return (
                [str(cur_year - 2), str(cur_year - 1)],
                [str(cur_year - 1), str(cur_year)],
                [str(cur_year), str(cur_year + 1)],
            )

        elif YorQ == "q":
            선행개월 = 2
            delta_1month = relativedelta(months=1)
            day = today + delta_1month * 선행개월
            이전 = [
                make_Q(day - delta_1month * 15),
                make_Q(day - delta_1month * 6),
                make_Q(day - delta_1month * 3),
            ]

            이번 = [
                make_Q(day - delta_1month * 12),
                make_Q(day - delta_1month * 3),
                make_Q(day),
            ]
            다음 = [
                make_Q(day - delta_1month * 9),
                make_Q(day),
                make_Q(day + delta_1month * 3),
            ]
            return 이전, 이번, 다음

    # def _candle_status(o, h, l, c):
    #     # ddic = defaultdict(lambda :-1)
    #     ddic = SerializableDefaultDict(partial(AnalTech.return_value_for_defaultdict,None))
    #     if o < c:
    #         candle_status = "양봉"
    #     elif o == c:
    #         candle_status = "도지"
    #     else:
    #         candle_status = "음봉"

    #     all_len = h - l
    #     head_len = h - max(o, c)
    #     body_len = max(o, c) - min(o, c)
    #     tail_len = min(o, c) - l
    #     ddic["상태"] = candle_status
    #     try:
    #         start_rate = round(body_len / min(o, c) * 100 , 3)  # 1.5 이하 상승하락 종목은 도지로 취급.
    #         ddic['시가대비등락율'] = start_rate
    #         if -1.5 < start_rate < 1.5:
    #             ddic["상태"] = "도지"
    #     except:
    #         pass

    #     try:
    #         all_rate = round(((h - l) / l) * 100 , 3) ## 저점대비고점 (캔들전체크기) (오늘종가 – 어제종가) / 어제종가 * 100
    #         ddic["전체등락율"] = all_rate
    #     except:
    #         pass

    #     try:
    #         head_rate = round(head_len / all_len * 100, 0) # 윗꼬리비율
    #         ddic["위꼬리비율"] = head_rate
    #     except:
    #         pass

    #     try:
    #         body_rate = round(body_len / all_len * 100, 0) # 몸통비율
    #         ddic["몸통비율"] = body_rate
    #     except:
    #         pass

    #     try:
    #         tail_rate = round(tail_len / all_len * 100, 0) # 아래꼬리비율
    #         ddic["아래꼬리비율"] = tail_rate
    #     except:
    #         pass

    #     return ddic

    # def _candle_status_by_df(df):
    #     result_apply = df.apply(lambda x : (Sean_func._candle_status(x['Open'], x['High'], x['Low'], x['Close'])), axis=1)
    #     result_df = pd.DataFrame(result_apply.to_list(), index=df.index)
    #     return result_df

    def _nomalize(s, min_value=0, max_value=1):
        """
        Series를 입력받아. nomalize정규화하여 Series형태로 반환.
        input : Series, min_value, max_value
        return: Series
        """
        i_min = s.min()
        i_max = s.max()
        i_diff = i_max - i_min
        first_nomalize = (s - i_min) / i_diff
        out_diff = max_value - min_value
        result = (first_nomalize * out_diff) + min_value
        return result

    def _get_all_current_price(str_today=None):
        """
        모든종목 등락율 가져오기.
        """
        if str_today == None:
            # date = datetime.today().date()
            date = pd.Timestamp.now().date()
            str_today = date.strftime("%Y%m%d")

        else:
            date = pd.to_datetime(str_today)
            str_today = date.strftime("%Y%m%d")

        df_all = pystock.get_market_ohlcv_by_ticker(str_today, market="ALL")
        if sum(df_all["거래량"]) != 0:
            df_all = df_all.loc[df_all["시가"] != 0]
            df_all["Date"] = date
            # df_all.index  = "A" + df_all.index
            df_all.rename(
                columns={
                    "시가": "Open",
                    "고가": "High",
                    "저가": "Low",
                    "종가": "Close",
                    "거래량": "Volume",
                    "거래대금": "Amount",
                    "등락률": "Change",
                },
                inplace=True,
            )
            df_all.index.name = "Code"
            df_all = df_all.reset_index()  ##
            ##
            df_all["code"] = df_all["Code"]
            df_all = df_all.set_index("code", drop=True)

            new_df = pd.DataFrame(
                list(
                    df_all.apply(
                        lambda row: Sean_func._candle_status(
                            row["Open"], row["High"], row["Low"], row["Close"]
                        ),
                        axis=1,
                    )
                )
            )
            new_df.index = df_all.index
            concat_df = pd.concat([df_all, new_df], axis=1)
        else:
            concat_df = df_all

        return concat_df

    # def fig_to_byteIO(fig):
    #     '''
    #     byteIO 사용시 필요하면 만들어쓰기.
    #     '''
    #     buffer = io.BytesIO()
    #     fig.savefig(buffer, format='png')
    #     buffer.seek(0)
    #     return buffer

    # def 누적수익율(s):
    #     '''
    #     구하고싶은 기간 series 받아서 기간누적수익율 구하기.
    #     iloc[0]일 매수한경우임.
    #     '''
    #     dic = {}
    #     누적수익율s = round( ((s / s.iloc[0]) -1 ) * 100, 1)

    #     최고수익율 = max(누적수익율s)
    #     최고수익일 = 누적수익율s.idxmax()
    #     최고수익달성기간 = len(누적수익율s.iloc[:최고수익일])

    #     sub_dic = {}
    #     sub_dic['수익율']=최고수익율
    #     sub_dic['보유기간']=최고수익달성기간
    #     sub_dic['수익날짜']=최고수익일
    #     dic['최고']=sub_dic

    #     최저수익율 = min(누적수익율s)
    #     최저수익일 = 누적수익율s.idxmin()
    #     최저수익달성기간 = len(누적수익율s.iloc[:최저수익일])

    #     sub_dic={}
    #     sub_dic['수익율']=최저수익율
    #     sub_dic['보유기간']=최저수익달성기간
    #     sub_dic['수익날짜']=최저수익일
    #     dic['최저']=sub_dic

    #     최종수익율 = 누적수익율s.iloc[-1]
    #     총보유기간 = len(누적수익율s) -1
    #     최종수익일 = 누적수익율s.index[-1]

    #     sub_dic={}
    #     sub_dic['수익율']=최종수익율
    #     sub_dic['보유기간']=총보유기간
    #     sub_dic['수익날짜']=최종수익일
    #     dic['최종']=sub_dic

    #     return dic
