import sys
import os
import pickle
import requests
import json
import pandas as pd
import io
import time
# import schedule
import threading
from datetime import datetime, timedelta
from django.conf import settings

##############   현재 시크릿 키만 가져옴. 키 되는지 확인도 해야하고. shell plus 에서 확안히가.   조건검색 기능 중지중임.  
class Kis:
    
    def __init__(self,mode=1):
        '''
        mode :0 모의투자 , 1 실전투자
        '''
        self.data_path = os.path.dirname(os.path.realpath(__file__)) 
        if mode == 0 :
            self.APP_KEY = settings.MYENV('KIS_TEST_APP_KEY')
            self.APP_SECRET = settings.MYENV('KIS_TEST_APP_SECRET')
            self.acc_no = settings.MYENV('KIS_TEST_ACC_NO')
            self.user_id = settings.MYENV('KIS_TEST_USER_ID')
            self.URL_BASE = "https://openapivts.koreainvestment.com:29443"
            self.mode = 0
        else:
            self.APP_KEY = settings.MYENV('KIS_APP_KEY')
            self.APP_SECRET = settings.MYENV('KIS_APP_SECRET')
            self.acc_no = settings.MYENV('KIS_ACC_NO')
            self.user_id = settings.MYENV('KIS_USER_ID')
            self.URL_BASE = "https://openapi.koreainvestment.com:9443" 
            self.mode = 1
        
        self.ACCESS_TOKEN = self._access_token() ## access_token 받기.

        
        ## 현재 내 조건식리스트 
        
        # self.my_cond_list = self._get_condition_list() # [('1', 'ac_2060_up'),('2', 'coke_status_coke_up_ac'),...
        # print("전체조건식:", self.my_cond_list)
        # print("==============================================")
        # self.my_cond_list = [cond for cond in self.my_cond_list if (('ac' in cond[1]) | ('doksa' in cond[1])| ('my' in cond[1]) | ('up' in cond[1])) ]     ## 특정조건만 필터.
        # print("적용조건식:", self.my_cond_list)
        # # [('1', 'short'), ('2', 'ac_2060_up'), ('3', 'coke_status_coke_up_ac'), ('4', 'coke_status_sun_up_ac'), ('6', 'sun_status_ac')]
        # print("==============================================")
    
    def __del__(self):
        try:
            self._access_token_delete()
        except:
            pass
        
        
    ############# api 정보 ############3
    def _access_token(self):
        ## access_token(보안인증키) 받기
        headers = {"content-type":"application/json"}
        body = {"grant_type":"client_credentials",
                "appkey":self.APP_KEY, 
                "appsecret":self.APP_SECRET}
        PATH = "oauth2/tokenP"
        URL = f"{self.URL_BASE}/{PATH}"
        res = requests.post(URL, headers=headers, data=json.dumps(body))
        ACCESS_TOKEN = res.json()["access_token"]
        return ACCESS_TOKEN

    def _access_token_delete(self):
        try:
            body = {
                    "appkey":self.APP_KEY, 
                    "appsecret":self.APP_SECRET,
                    "token":self.ACCESS_TOKEN }
            
            PATH = "/oauth2/revokeP"
            URL = f"{self.URL_BASE}/{PATH}"
            res = requests.post(URL, data=json.dumps(body))
            if res['code'] == 200:
                print('ACCESS_TOKEN 폐기 성공!')
            else:
                print('ACCESS_TOKEN 폐기 실패!')
        except Exception as e:
            print('access_token_delete error',e)
            # for _ in range(5):
            #     time.sleep(10)
            #     print('token 폐기 오류 10초후 재시도')
            #     try:
            #         self._access_token_delete()
            #         print('재시도 성공1')
            #     except:
            #         pass
                    
            # print('5 재시도후 실패.')
            # ## 끝내기.
            # return
        
                

    def _hashkey(self, datas):
        '''
        datas : requests body 
        '''
        PATH = "uapi/hashkey"
        URL = f"{self.URL_BASE}/{PATH}"
        headers = {
        'content-Type' : 'application/json',
        'appKey' : self.APP_KEY,
        'appSecret' : self.APP_SECRET,}
        res = requests.post(URL, headers=headers, data=json.dumps(datas))
        hashkey = res.json()["HASH"]
        return hashkey 

    ############ 계좌정보 #############3
    def _get_balance(self, only_response=False):
        '''
        잔고조회
        실전계좌 : 한 번의 호출에 최대 50건까지 확인 가능, 이후의 값은 연속조회를 통해 확인하실 수 있습니다. 
        모의계좌 : 한 번의 호출에 최대 20건까지 확인 가능, 이후의 값은 연속조회를 통해 확인하실 수 있습니다. 
        '''
        
        PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"
        URL = f"{self.URL_BASE}/{PATH}"
        if self.mode == 0:
            tr_id = "VTTC8434R"
        else:
            tr_id = "TTTC8434R"
        
        params = {"CANO": self.acc_no.split("-")[0],
                "ACNT_PRDT_CD" : self.acc_no.split("-")[1],
                "AFHR_FLPR_YN" : "N", # N:기본값 Y:시간외단일가
                "OFL_YN" : "",
                "INQR_DVSN" : "02" , # 01:대출일별, 02:종목별
                "UNPR_DVSN" : "01", # 단가구분 기본값 01
                "FUND_STTL_ICLD_YN" : "N", # 펀드결제분포함여부
                "FNCG_AMT_AUTO_RDPT_YN" : "N", # 융자금액자동상환여부
                "PRCS_DVSN" : "01" ,  # 00: 전일매매포함 01:전일매매미포함
                "CTX_AREA_FK100" : "" , 
                "CTX_AREA_NK100" : "",
                }

        headers ={
            "content-type" : "application/json; charset=utf-8",
            "authorization" : f"Bearer {self.ACCESS_TOKEN}",
            "appkey": self.APP_KEY,
            "appsecret" : self.APP_SECRET, 
            "tr_id"  : tr_id,
            "tr_cont" : "",
            "hashkey" : self._hashkey(params)
            }

        res = requests.get(URL, headers=headers, params=params)
        if only_response:
            return res
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_balance.__name__}")    

        js =  res.json()
        ######################        할일 . 필요한 데이터만 추출해야함. 
        return js
        
    ########### 국내주식시세 #############

    ########### 조건검색 가져오기.  #############
    def _get_condition_list(self, only_response=False):
        # 조건검색리스트 조회
        if self.mode == 0: ## 모의투자 미지원
            return None
        PATH = "/uapi/domestic-stock/v1/quotations/psearch-title"
        URL = f"{self.URL_BASE}/{PATH}"
        params = {"user_id": self.user_id}
        headers ={
            "content-type" : "application/json; charset=utf-8",
            "authorization" : f"Bearer {self.ACCESS_TOKEN}",
            "appkey": self.APP_KEY,
            "appsecret" : self.APP_SECRET, 
            "tr_id"  : "HHKST03900300",
            "tr_cont" : "",
            "hashkey" : self._hashkey(params)
            }
        res = requests.get(URL, headers=headers, params=params)
        if only_response:
            return res
        
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_condition_list.__name__}")    
        
        res.json()['output2']
        my_cond_list = []
        for cond in res.json()['output2']:
            seq = cond['seq']
            name = cond['condition_nm']
            if "test" not in name:  ## test 제외.
                my_cond_list.append((seq, name))
        return my_cond_list
    
    def _get_condition_code_list_test(self, seq, only_response=False):
        # 조건검색 종목 결과 리스트 조회
        PATH = "/uapi/domestic-stock/v1/quotations/psearch-result"
        URL = f"{self.URL_BASE}/{PATH}"
        # print(URL)

        params = {"user_id": self.user_id,
                "seq" : seq}

        headers ={
            "content-type" : "application/json; charset=utf-8",
            "authorization" : f"Bearer {self.ACCESS_TOKEN}",
            "appkey": self.APP_KEY,
            "appsecret" : self.APP_SECRET, 
            "tr_id"  : "HHKST03900400",
            "tr_cont" : "",
            "hashkey" : self._hashkey(params)
            }

        res = requests.get(URL, headers=headers, params=params)
        if only_response:
            return res
        
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_condition_code_list.__name__}")    
            

            
        dic = res.json()
        # print("recieve dic : ", dic)
        data = dic.get('output2')
        return data
    
    
    def _get_condition_code_list(self, seq, only_response=False):
        # 조건검색 종목 결과 리스트 조회
        PATH = "/uapi/domestic-stock/v1/quotations/psearch-result"
        URL = f"{self.URL_BASE}/{PATH}"
        # print(URL)

        params = {"user_id": self.user_id,
                "seq" : seq}

        headers ={
            "content-type" : "application/json; charset=utf-8",
            "authorization" : f"Bearer {self.ACCESS_TOKEN}",
            "appkey": self.APP_KEY,
            "appsecret" : self.APP_SECRET, 
            "tr_id"  : "HHKST03900400",
            "tr_cont" : "",
            "hashkey" : self._hashkey(params)
            }

        res = requests.get(URL, headers=headers, params=params)
        if only_response:
            return res
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_condition_code_list.__name__}")    
            

            
        dic = res.json()
        # print("recieve dic : ", dic)
        data = dic.get('output2')
        if data != None:
            result_df = pd.DataFrame(res.json()['output2'])
            col = {"code":"종목코드",
            "name":"종목명",
            "daebi":"전일대비부호",
            "price":"현재가",
            "chgrate":"등락율",
            "acml_vol":"거래량",
            "trade_amt":"거래대금",
            "change":"전일대비",
            "cttr":"체결강도",
            "open":"시가",
            "high":"고가",
            "low":"저가",
            "high52":"52주최고가",
            "low52":"52주최저가",
            "expprice":"예상체결가",
            "expchange":"예상대비",
            "expchggrate":"예상등락률",
            "expcvol":"예상체결수량",
            "chgrate2":"전일거래량대비율",
            "expdaebi":"예상대비부호",
            "recprice":"기준가",
            "uplmtprice":"상한가",
            "dnlmtprice":"하한가",
            "stotprice":"시가총액",}
            result_df = result_df.rename(columns=col)
            
            for col in result_df.columns[2:]:
                result_df[col] = pd.to_numeric(result_df[col],errors='coerce')
            return result_df
        else:
            return pd.DataFrame()

    def _get_all_mycond_df(self):
        all_ls = []
        for seq, cond_name in self.my_cond_list:
            result = self._get_condition_code_list(seq)
            result['cond_name'] = cond_name
            all_ls.append(result)
            time.sleep(0.5)
            
        df = pd.concat(all_ls).reset_index(drop=True)
        grouped = df.groupby("종목명")
        all_ls = []
        for _ , group in grouped:
            if len(group) >1:
                group['cond_name'] = ','.join(list(group['cond_name']))
            all_ls.append(group)
        df = pd.concat(all_ls)
        df = df.drop_duplicates('종목명')
        col = ['종목코드', '종목명',  '현재가', '등락율', '거래량', '거래대금', '전일대비', '체결강도','시가', '고가', '저가', '전일거래량대비율',  '시가총액','cond_name']
        df = df[col].reset_index(drop=True)
        df['cond_cnt'] = df['cond_name'].str.count(',')
        df = df.sort_values(by=['cond_cnt','등락율'] , ascending=[False,False])
        return df
    
        
        
    def _check_cond_code(self, code, cond_name, sended_dic, now) -> dict:
        '''
        기존 sended_dic 확인후 처리후 다시 반환. 
        msg : True 면 메세지 보내기. 
        '''
        skip_allow_hour = 1   ## 한시간 동안 중복 스킵.
        msg = False
        if not code in sended_dic['sended'].keys():  ## 코드가 없다면 추가.
            sended_dic['sended'][code]= {}
            sended_dic['sended'][code][cond_name]= {'time' : now, 'count' : 1}
            print(code, cond_name, '새로운 code 추가')
            msg = True
        else:
            ## 코드가 있다면 cond_name 이 존재하는지 확인. 
            if not cond_name in sended_dic['sended'][code].keys(): # 기존신호가 없으면 자료 추가. 
                sended_dic['sended'][code][cond_name] = {'time':now,'count':1}
                print('기존코드에 조건식 새로 추가',cond_name)
                msg = True
            else:  ## # 시간차이가 1시간보다 크면 데이터 업데이트.
                pre_time = sended_dic['sended'][code][cond_name]['time']
                diff_time = now - pre_time
                if diff_time.seconds >= skip_allow_hour * 60 * 60:
                    print(code, cond_name ,'data 없데이트 됨.')
                    sended_dic['sended'][code][cond_name]['time'] = now
                    sended_dic['sended'][code][cond_name]['count'] += 1
                    msg = True
                else:
                    # print(sended_dic['sended'][code][cond_name]['time'], '에 기존 보낸자료에 최근에 존재함')
                    pass
        if msg == False:
            print(f'===================  시간제한으로 제외되는 종목 {code} =========================')
        print(f'현재시간 :{now}')
        return msg, sended_dic

    def _send_photo(self,code, code_name, gb, msg, caption):
        try:
            s = ms.Stock(code, code_name, gb)  ## 객체 만들고 . 
            try:     ### trend 가 있으면 trend 그리기. 
                trend = self._get_invest_trend(code)
                trend = trend.filter(regex="외국인.*|기관.*")
                fig = s._plot(cnt=120, trend=trend) ## fig 만들어
            except:
                fig = s._plot(cnt=120) ## fig 만들어
            
            # msg= ms.Mymsg(chat_name='키움알림')
            # #### method 1
            buf = io.BytesIO()
            fig.savefig(buf,format='png',dpi=200)
            time.sleep(0.5)    ## 1초 쉬기. 객체만드는데 시간이 들어서 안쉬어도 될듯.
            print('send_phto!!5456525')
            buf.seek(0)
            msg._send_photo(photo= buf.read(), caption = caption)
        except:
            print('send_phto!! failed!! ')
            
        
        
    def __send_message_all_text(self, grouped, msg_class,picked_good_buy_rate_df, mode):
        ### 종목명 grouped 인자 필요
        try:
            text_ls = []
            for code_name, group in grouped:
                # code_name = group.iloc[0]['종목명']
                code = group.iloc[0]['종목코드']
                change = group.iloc[0]['등락율']
                cond_name = group.iloc[0]['cond_name']
                buy_rate = group.iloc[0]['체결강도']
                
                
                ### coke_up 이 겹치는경우 별표 표시해서 알려줌..    picked_good_buy_rate_df 에 포함된종목 ## 추가하기 
                coke_up_cond_name_list = [name for name in cond_name.split(",") if "coke_up" in name]
                if len(coke_up_cond_name_list) > 1:
                    if len(picked_good_buy_rate_df) & (code in picked_good_buy_rate_df['code']):
                        text_ls.append(f"✭✭_**_##_{code_name}({change:,.1f}% {buy_rate:,.0f}%)")
                    else:
                        text_ls.append(f"✭✭_**_{code_name}({change:,.1f}% {buy_rate:,.0f}%)")
                else:
                    if len(picked_good_buy_rate_df) & (code in picked_good_buy_rate_df['code']):
                        text_ls.append(f"##_{code_name}({change:,.1f}% {buy_rate:,.0f}%)")
                    else:
                        text_ls.append(f"{code_name}({change:,.1f}% {buy_rate:,.0f}%)")
                
            all_txt = '\n'.join(text_ls)
            if mode ==1:
                all_txt = "==종가매수==\n" + all_txt
            msg_class._send_message(all_txt)
        except Exception as e:
            print(e)
            print('__send_message_all_text err')
    
    def choice_stock(self):
        
        
        ## mode 1 일때는 upper_inclination20 값이 -1이상인것만 취급하기.
        # if self.mode ==1 :
        self.send_df = self.send_df.loc[self.send_df['upper_inclination20'] >= -1]    ### bb upper 변화율 고려
        self.send_df = self.send_df.loc[self.send_df['r_array_status'] == 0 ]    ### 역배열 이면 True 인 값. 
        print('upper_inclination20   고려됨. ====   완전 역배열 제외 ============================')
        ## 종목 거르기 .
        
        ## 하방 제거.   "역방향" 포함 제거
        # reasons 에 "역방향" 키워드 있으면 제외하기.
        cond_역방향 = self.send_df['reasons'].apply(lambda x: True if '역방향' in x else False)
        self.send_df = self.send_df.loc[~cond_역방향]
        
        ## "상투"  포함 제거
        cond_상투  = self.send_df['reasons'].apply(lambda x: True if '상투' in x else False)
        self.send_df = self.send_df.loc[~cond_상투]
        
        ## "W"  포함만 취급
        cond_W  = self.send_df['reasons'].apply(lambda x: True if 'W' in x else False)
        self.send_df = self.send_df.loc[cond_W]
        
        ##  "new_phase"    새로운국면 항상 주시하기. 
        cond_new_phase  = self.send_df['reasons'].apply(lambda x: True if 'new_phase' in x else False)
        # self.send_df = self.send_df.loc[cond_new_phase]

        
        print("===================================================")
        print(len(self.send_df) ,'개의 조건 검색 데이터가 있음. ')
        print("===================================================")
        ## 착시 abc  앞산거래량. 고려.   착시일 가져와서 그날부터 현재까지 개수 확인하기. 
        cond_abc = self.send_df['reasons'].apply(lambda x: True if '착시' in x else False)
        cond_low_v = self.send_df['거래량'] < self.send_df['기준거래량']
        cond_location_price = self.send_df['abc_b'] < self.send_df['현재가']
        cond_low_candle = abs(self.send_df['등락율']) < 2 
        cond_pre_mtv_exists = self.send_df['pre_mt_v_cnt'] > 0   ## 앞산거래량
        cond_착시 = (cond_abc & cond_low_v & cond_location_price & cond_low_candle & cond_pre_mtv_exists)
        
        
        # # # ac+ sun
        cond_gcv = self.send_df['reasons'].apply(lambda x: True if '착시' in x else False)
        cond_alphabeta = self.send_df['reasons'].apply(lambda x: True if 'alphabeta_20' in x else False)
        cond_sun_gc = self.send_df['reasons'].apply(lambda x: True if 'sun_gc' in x else False)
        cond_bb_gc = self.send_df['reasons'].apply(lambda x: True if 'bb_gc' in x else False)
        cond_sun_ac = (self.send_df['전일거래량대비율'] > 200) & (cond_gcv | cond_alphabeta | cond_sun_gc | cond_bb_gc)
        
        
        ## only sun  돌파
        cond_sun_up = (self.send_df['sun_current_up_value'] < self.send_df['현재가']) & (self.send_df['sun_current_up_value'] < self.send_df['저가'])
        cond_only_sun = (self.send_df['전일거래량대비율'] > 200) & cond_sun_up
        
        
        
        ## only coke 돌파
        # # bb + ac   (bb 너비상태 추가해야함. )
        cond_width = self.send_df['bb_gc_width_value'] <= 60
        cond_coke_up = (self.send_df['bb_current_up_value'] < self.send_df['현재가']) & (self.send_df['bb_current_up_value'] < self.send_df['저가'])
        cond_only_coke = (self.send_df['전일거래량대비율'] > 200) &  cond_coke_up
        
        
        # 20w gcv. 기준거래량. 
        cond_alphabeta = self.send_df['reasons'].apply(lambda x: True if 'alphabeta_20' in x else False)
        cond_low_v = self.send_df['거래량'] < self.send_df['기준거래량']
        cond_only_alphabeta =  (cond_alphabeta & cond_low_v)
        
        choiced_sended_df = self.send_df.loc [cond_착시 | cond_sun_ac | cond_only_sun | cond_only_coke | cond_only_alphabeta]
        
        return choiced_sended_df 
    
    def _check_data_for_send1(self,mode):
        '''
        mode : 0 장중매수
        mode : 1 종가매수
        mode 로 특정 COND_name 제거하면 된다. 
        '''
        self.mode = mode
        data_path = os.path.dirname(os.path.realpath(__file__)) 
        now = datetime.now()
        
        #### 매집비 종목 가져오기. 
        with open(f'{data_path}/datas/picked_good_buy_rate.df','rb') as f:
            picked_good_buy_rate_df = pickle.load(f)
        
        ### picked_good_buy_rate_df columns
        ### ['code', 'code_name', '기간', '순매수대금_억', '매집비', '주도기관', '저점대비상승률']
        
        ######################  새로운 조건 데이터 가져옴.  #############################################
        code_df = ms.Fnguide.get_ticker_by_fnguide('db')
        code_df['code'] = code_df['cd'].apply(lambda x: x[1:]) ## code columns 생성.
        
        ## 애초에 code_df 와 매칭.
        self.new_cond_df = self._get_all_mycond_df()
        
        print('new_cond_df_cnt', len(self.new_cond_df))
        print('code_df_cnt', len(code_df))
        
        if len(self.new_cond_df) ==0:
            print('조건만족 종목이 없습니다.')
            return 
        self.new_cond_df['cond_time'] = now # 시간 추가. 
        try:
            self.new_cond_df = pd.merge(self.new_cond_df, code_df, left_on='종목코드', right_on='code',how='inner')  ## code_df 에 있는 종목만 GB 가져오기. 
        except:
            self.new_cond_df['gb'] = '코스피'   ## 오류날때 억지로 구색맞춤.
        print('새로받은데이터 개수 ' , len(self.new_cond_df))
        
        self.new_cond_df = self.new_cond_df.set_index('code')
        self.new_cond_df = self.new_cond_df.filter(regex='[^(gb)|(nm)|(mkt_gb)|(stk_gb)|(cd)]')  ## 이후 picked_df 와 합쳐지기때문에 불필요한 columns제거 . 
        ################################################################################
        
        ################## sended_dic 재저장. ################################################
        try:
            temp_cond_file_name = f'{data_path}/datas/new_cond_df.pkl'
            with open(temp_cond_file_name,'wb') as f:
                pickle.dump(self.new_cond_df, f, protocol=pickle.HIGHEST_PROTOCOL)
                print('new sended_saved !!')
        except:
            pass
        ########################################################################################
        
        
        
        ############# 기존 데이터  sended_dic 가져오기.. #######################
        sended_dic_file_name = f'{data_path}/datas/sended_dic.pkl'
        now = datetime.today()
        today = now.date()
        if not os.path.exists(sended_dic_file_name):
            print("파일이 없어 새로 dic 생성")
            sended_dic = {'date': today,
                        'sended':{}}
        else:
            with open(sended_dic_file_name,'rb') as f:
                sended_dic= pickle.load(f)
                print('기존파일 가져옴. ')
        if today != sended_dic['date'] :
            sended_dic = {'date': today,
                        'sended':{}}
            print('파일 초기화')
        ###############################################################
        
        ############ 종가 mode 일때 ac 관련 모두 지우기.##############################
        if self.mode == 1:
            sended_dic = {'date': today,
            'sended':{}}
            print('파일 초기화')
        ##################################################################
        
        
        
        ############ picked_df 에 포함된 종목만 추출.###################################
        with open(f'{data_path}/datas/picked_df.pkl','rb') as f:
            self.picked_df = pickle.load(f)
            # code, code_name, gb, reasons(ls)
        self.picked_df = self.picked_df.set_index('code') # .loc['005303','reasons']
        
        ############ picked_df_all mode1일때만 사용..###################################
        # if mode ==1:
        with open(f'{data_path}/datas/picked_df_all.pkl','rb') as f:
            self.picked_df_all = pickle.load(f)
            # code, code_name, gb, reasons(ls)
        self.picked_df_all = self.picked_df_all.set_index('code') # .loc['005303','reasons']
        
        
        
        ##????????? 이거 초이스 함수로 옮겨도 돼.?
        ## new_cond_df  자료에 picked_df 내용 삽입.#################
        
        self.new_cond_df = pd.merge(self.new_cond_df, self.picked_df, how='inner', left_index=True, right_index=True)
            
            
            
        if len(self.new_cond_df) ==0:   ## 데이터가 없으면 작업 종료 
            print('해당데이터 없어서 작업종료함.')
            return
        print( f"{len(self.new_cond_df)}개 데이터 검색" )
        ###########################################################################
        # new_cond_df db저장하기 
        
        
        ############ 기존 sended_dict로 거르기. ########################################
        msg_list = []
        for _ , row in self.new_cond_df.iterrows():
            code = row['종목코드']
            code_name = row['종목명']
            cond_name= row['cond_name']
            cond_time = row['cond_time']
            gb = row['gb']
            # if cond_name != 'short':  ### short 는 계속 모니터링 하겠다는 말. 
            msg_bool , sended_dic = self._check_cond_code(code, cond_name, sended_dic, cond_time )
            if msg_bool:
                msg_list.append( code )
        ################################################################################
        
        
        
        ################## sended_dic 재저장. ################################################
        with open(sended_dic_file_name,'wb') as f:
            pickle.dump(sended_dic, f, protocol=pickle.HIGHEST_PROTOCOL)
            print('new sended_saved !!')
        ########################################################################################
        
        
        ##############   상투 A급 가까워지는것 제외하기. ##########################3
        except_df = self.new_cond_df.loc[(self.new_cond_df['거래량'] > self.new_cond_df['유통주식수'] * 0.9)]   ## 제외될 종목.
        if len(except_df):
            print("======================== 상투로 제외되는 종목 ================================")
            print(list(except_df['종목명']))
            print("=========================================================================")
        self.new_cond_df= self.new_cond_df.loc[~(self.new_cond_df['거래량'] > self.new_cond_df['유통주식수'] * 0.9)]
        ########################################################################################
        
        
        
        if len(msg_list) == 0:
            print('보낼메세지 없어 종료함.')
            return
        
        print('msg_list : ', msg_list)
        
        ## 자료가 있다면 메세지 보내기 작업 .
        self.send_df = self.new_cond_df.loc[self.new_cond_df['종목코드'].isin(msg_list)].copy()
        print('send_df_cnt : ',len(self.send_df))
        # msg = ms.Mymsg(chat_name='키움알림')
        msg = ms.Mymsg(chat_name='종목알림')
        
        
        ############# db 저장하기. =================  reasons 에 있는 list 를 변환해야 저장가능. 
        try:
            if len(self.send_df):
                # send_df
                col = ['종목코드', '종목명', '현재가', '등락율', '거래량', '거래대금','체결강도','전일거래량대비율', '시가총액', 'cond_name', 'cond_cnt', 'cond_time',
        'reasons', '유통주식수', '착시', 'abc_b', 'pre_mt_v_cnt',
       '기준거래량', 'ma20_v', 'bb_gc_width_value', 'bb_current_up_value',
       'sun_gc_width_value', 'sun_current_up_value']
                data1 = self.send_df[col].copy()
                data1['reasons'] = data1['reasons'].apply(lambda x: ','.join(x))
                data_base_name = 'kis'
                table_name = "cond"
                mydb = ms.Db(f'{data_path}/info/db_info_mini.json',data_base_name)
                mydb._create_db()
                mydb._put_db(data1, table_name,if_exists='append')
                mydb._close()
                print('my_cond 저장')
        except Exception as e:
            print('my_cond  send err ############################',e)        
        
        
        
        
        ## 조건건색받은 데이터에서 메세지 보낸데이터 제외한 데이터 --> 메세지 보낼 데이터.
        with open(f"{data_path}/datas/temp_new_cond_df.pkl",'wb') as f:
            pickle.dump(self.send_df, f, protocol=pickle.HIGHEST_PROTOCOL)

        ################################################################
        
        # mode에 따라 send_df 추리기
        self.send_df = self.choice_stock()
        
        ## 조건건색받은 데이터에서 메세지 보낸데이터 제외한 데이터 --> 메세지 보낼 데이터.
        with open(f"{data_path}/datas/temp_new_cond_df_1.pkl",'wb') as f:
            pickle.dump(self.send_df, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        #########  temp_new_cond_df 와 temp_new_cond_df_1 과 차이 비교. choice_stock 으로 걸러지나.?
        
        
        if len(self.send_df) == 0:
            print('보낼메세지 없어 종료함33.')
            return
        
        ################################################################################
        
        
        
        grouped = self.send_df.groupby('종목명')
        ## 체크할 기준 검색종목개수 k
        k = 10
        
        #### 일단 문자로 메세지 보냄. 
        self.__send_message_all_text(grouped, msg, picked_good_buy_rate_df,self.mode)  # 이 안에서 진짜 원하는것 체크하는게 좋겠다. 

        
        ### 차트 보내기. 
        if (self.mode == 1) | (len(grouped) < k) : ## k 이하의 갯수거나. 종가베팅시 그래프 보내기. 
            ##############  Mode에 따라 차트 보내기 변경. ###################
            
            ## 착시 거래량 만족 code_list -> abc_v_list 
            # cond_v = new_cond_df['착시'] & (new_cond_df['거래량'] <= new_cond_df['기준거래량'])
            # abc_v_list = list(new_cond_df.loc[cond_v]['종목코드'])
            # print('기준거래량 만족 종목 개수:', len(abc_v_list))
            # cond_cnt = len(grouped)   ## 검색종목의 개수.
            
            
            for code_name, group in grouped:
                code = group.iloc[0]['종목코드']
                gb = group.iloc[0]['gb']
                change = group.iloc[0]['등락율']
                current_price = group.iloc[0]['현재가']
                전일대비거래량비 = group.iloc[0]['전일거래량대비율']
                체결강도 = group.iloc[0]['체결강도']
                현재거래량 = group.iloc[0]['거래량']
                거래대금_억 = group.iloc[0]['거래대금']
                
                유통주식수 = group.iloc[0]['유통주식수']
                착시여부 = group.iloc[0]['착시']
                abc_b = group.iloc[0]['abc_b']
                기준거래량 = group.iloc[0]['기준거래량']
                평균거래량20 = group.iloc[0]['ma20_v']
                bb_gc_width =  group.iloc[0]['bb_gc_width_value']  # 50보다 작고 
                corrent_bb_up_value = group.iloc[0]['bb_current_up_value']
                
                
                ## bb 돌파후 2차파동. 조건. 
                cond_second_up = (bb_gc_width <= 50)  & (corrent_bb_up_value < current_price)
                
                
                ### sended_df columns
                # ['종목코드', '종목명', '전일대비부호', '현재가', '등락율', '거래량', '거래대금', '전일대비', '체결강도',
                # '시가', '고가', '저가', '52주최고가', '52주최저가', '예상체결가', '예상대비', '예상등락률',
                # '예상체결수량', '전일거래량대비율', '예상대비부호', '기준가', '상한가', '하한가', '시가총액',
                # 'cond_name', 'cond_time', 'code_name', 'gb', 'reasons', '유통주식수', '착시',
                # 'abc_b', 'pre_mt_v_cnt', '기준거래량', 'ma20_v', 'bb_gc_width_value',
                # 'bb_current_up_value', 'sun_gc_width_value', 'sun_current_up_value']
               
                cond_names= group.iloc[0]['cond_name']
                my_cond_status= ','.join(group.iloc[0]['reasons'])
                
                coke_up_cond_name_list = [name for name in cond_names.split(",") if "coke_up" in name]
                
                
                '''
                종가베팅에서는( mode ==1)  abc와 눌릶목에서 현재거래량으로 거래눌림목 기법 추가.  
                '''
                try:
                    text = f"{str(now)}(검색종목:=={cond_names}==\n=={my_cond_status}==\n{code_name} {change:.1f}%\n현재가:{current_price:,}원\n전일대비거래량{전일대비거래량비:.1f}%\n체결강도{체결강도:.0f}% 거래대금:{(거래대금_억/100000):,.2f}억"
                except:
                    text = f"{str(now)}(검색종목:=={cond_names}==\n=={my_cond_status}==\n{code_name}"
                
                if len(coke_up_cond_name_list) > 1:
                    text = "✭✭_**_" + text
                
                try:
                    if self.mode == 0:  ## 장중.
                        if change < 25:   
                            # 차트 전송.
                            if cond_second_up:
                                text = "✭_*_" + text
                            print('차트전송시작.!!')
                            self._send_photo(code, code_name, gb , msg=msg, caption = str(text))
                            print(f"send_msg장중 17이하.: {code}{code_name} {str(text)}")  
                    
                    ##############################   mode =1 일때 데이터 확인   #################################################
                    elif self.mode == 1: ## 종가
                        cond_low_v = 착시여부 & ( abc_b > current_price) & ((현재거래량 <= 기준거래량) | (현재거래량 <= 평균거래량20))
                        
                        if cond_low_v:  #  착시고 abc_b보가 크고 기준거래량이나 ma20_v 보다 현재거래량이 작은것. 
                            if cond_second_up:
                                text = "✭_*_" + text
                            text = "<종가매수_거래량>\n"+ text
                            self._send_photo( code=code, code_name=code_name, gb=gb ,msg=msg, caption = str(text))
                            print(f"send_msg(종가매수 거래량 만족.): {code}{code_name} {str(text)}")  
                    
                        
                        elif ('up' in cond_names) | ('doksa' in cond_names) |('ac' in cond_names) :
                            print(f'coke_up..sun_up....{code_name}.....')
                            # 차트 전송.
                            if cond_second_up:
                                text = "✭_*_" + text
                            text = "<종가매수_추세>\n"+ text
                            self._send_photo( code=code, code_name=code_name, gb=gb ,msg=msg, caption = str(text))
                            print(f"send_msg(종가매수): {code}{code_name} {str(text)}")  
                        
                        # ## picked 에 기준거래량 추가. 
                        # if len(abc_v_list):
                        #     if code in abc_v_list:
                        #         text = "<종가매수_low_vol>\n"+ text
                        #         self._send_photo( code=code, code_name=code_name, gb=gb ,msg=msg, caption = str(text))
                        #         print(f"send_msg(종가매수 거래량 만족.): {code}{code_name} {str(text)}")  
                        
                        
                   
                        ## ac 중. 돌파종목 10프로 미만.???
                        '''
                        전체적인 정리. 간결유지.!!
                        '''

                    
                except Exception as e:
                    print('차트 에러45674657',e , code_name)
                
      
           
        # # 나중에 분석에 쓰임.  ======== > 실제로 Kis 조건 과 내 조건이 맞은것들 추출해서 저장해야함. 
        # 실제 보낸 데이터만 추출하기. 
        # print(my_cond_code_dic)
        # try:
        #     print("my_cond_code_dic: ",my_cond_code_dic)
        #     my_send_df = send_df.loc[send_df['종목코드'].isin( list(my_cond_code_dic.keys()) ) ] .copy()  ## 경고없애기.명시적 카피
            
        #     ## my_cond 넣기.  권장사항.
        #     for code, mycond in my_cond_code_dic.items():
        #         my_send_df.loc[my_send_df['종목코드']==code,'mycond'] = mycond
        
        # except Exception as e:
        #     print('mycond23333err',e)
        # try:
        #     if len(my_send_df):
        #         data_base_name = 'kis'
        #         table_name = "cond"
        #         mydb = ms.Db(f'{data_path}/info/db_info_mini.json',data_base_name)
        #         mydb._create_db()
        #         mydb._put_db(my_send_df, table_name,if_exists='append', index=True)
        #         mydb._close()
        #         print('my_cond 저장')
        # except Exception as e:
        #     print('my_cond  send err',e)        
        
        print("============= ",now," ====================")




    def _get_investor(self,code):
        ############ 투자자 정보 가져오기################
        PATH = "/uapi/domestic-stock/v1/quotations/inquire-investor"
        URL = f"{self.URL_BASE}/{PATH}"
        
        params = {
            "FID_COND_MRKT_DIV_CODE":"J",
            "FID_INPUT_ISCD":code }
        headers = {"Content-Type":"application/json", 
                "authorization": f"Bearer {self.ACCESS_TOKEN}",
                "appKey":self.APP_KEY,
                "appSecret":self.APP_SECRET,
                "tr_id":"FHKST01010900",
                "tr_cont": "",
                "hashkey":self._hashkey(params)}
        ## 주식현재가 시세의 tr_id는 "FHKST01010100" 
        res = requests.get(URL, headers=headers, params=params)
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_investor.__name__}")    
            
        df = pd.DataFrame(res.json()['output'])
        col= {
        "stck_bsop_date":"날짜",
        "stck_clpr":"종가",
        "prdy_vrss":"전일대비",
        "prdy_vrss_sign":"전일대비부호",    ## 1:상한, 2:상승, 3:보합, 4:하한. 5:하락
        "prsn_ntby_qty":"개인_순매수_수량",
        "frgn_ntby_qty":"외국인_순매수_수량",
        "orgn_ntby_qty":"기관계_순매수_수량",
        "prsn_ntby_tr_pbmn":"개인_순매수_거래대금",
        "frgn_ntby_tr_pbmn":"외국인_순매수_거래대금",
        "orgn_ntby_tr_pbmn":"기관계_순매수_거래대금",
        "prsn_shnu_vol":"개인_매수_거래량",
        "frgn_shnu_vol":"외국인_매수_거래량",
        "orgn_shnu_vol":"기관계_매수_거래량",
        "prsn_shnu_tr_pbmn":"개인_매수_거래대금",
        "frgn_shnu_tr_pbmn":"외국인_매수_거래대금",
        "orgn_shnu_tr_pbmn":"기관계_매수_거래대금",
        "prsn_seln_vol":"개인_매도_거래량",
        "frgn_seln_vol":"외국인_매도_거래량",
        "orgn_seln_vol":"기관계_매도_거래량",
        "prsn_seln_tr_pbmn":"개인_매도_거래대금",
        "frgn_seln_tr_pbmn":"외국인_매도_거래대금",
        "orgn_seln_tr_pbmn":"기관계_매도_거래대금",
        }
        df = df.rename(columns=col)
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col],errors='coerce')
            
        col  = ['날짜', '종가', '전일대비', '전일대비부호',
        '개인_순매수_거래대금', '외국인_순매수_거래대금', '기관계_순매수_거래대금', '개인_매수_거래대금', '외국인_매수_거래대금',
        '기관계_매수_거래대금',  '개인_매도_거래대금',
        '외국인_매도_거래대금', '기관계_매도_거래대금']
        df = df[col]
        df['날짜'] = pd.to_datetime(df['날짜'])
        df =  df.set_index('날짜',drop = True)
        df = df.sort_index()
        return df
    
    def _get_inquire_member(self,code):
        
        '''
        효율 떨어짐.
        '''
        ############ 거래원 정보 가져오기################
        PATH = "/uapi/domestic-stock/v1/quotations/inquire-member"
        URL = f"{self.URL_BASE}/{PATH}"
        
        params = {
            "FID_COND_MRKT_DIV_CODE":"J",
            "FID_INPUT_ISCD":code }
        
        headers = {"Content-Type":"application/json", 
                "authorization": f"Bearer {self.ACCESS_TOKEN}",
                "appKey":self.APP_KEY,
                "appSecret":self.APP_SECRET,
                "tr_id":"FHKST01010600",
                "tr_cont": "",
                "hashkey":self._hashkey(params)}
        ## 주식현재가 시세의 tr_id는 "FHKST01010100" 
        res = requests.get(URL, headers=headers, params=params)
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_inquire_member.__name__}")    
            
            
        date = res.headers['Date']  ## timezone 해결해야됨.
        
        js =res.json()['output']
        sell_dic = {"회원사": [js['seln_mbcr_name1'], js['seln_mbcr_name2'], js['seln_mbcr_name3'], js['seln_mbcr_name4'], js['seln_mbcr_name5']],
        "수량" : [js["total_seln_qty1"], js["total_seln_qty2"], js["total_seln_qty3"], js["total_seln_qty4"], js["total_seln_qty5"]], 
        "회원사비중" : [js["seln_mbcr_rlim1"], js["seln_mbcr_rlim2"], js["seln_mbcr_rlim3"], js["seln_mbcr_rlim4"], js["seln_mbcr_rlim5"]],
        "매도수량증감" : [js["seln_qty_icdc1"], js["seln_qty_icdc2"], js["seln_qty_icdc3"], js["seln_qty_icdc4"], js["seln_qty_icdc5"]],
        "외국계여부" : [js["seln_mbcr_glob_yn_1"], js["seln_mbcr_glob_yn_2"], js["seln_mbcr_glob_yn_3"], js["seln_mbcr_glob_yn_4"], js["seln_mbcr_glob_yn_5"]], 
        }

        buy_dic= {"회원사": [js["shnu_mbcr_name1"], js["shnu_mbcr_name2"], js["shnu_mbcr_name3"], js["shnu_mbcr_name4"], js["shnu_mbcr_name5"]], 
        "수량" : [js["total_shnu_qty1"], js["total_shnu_qty2"], js["total_shnu_qty3"], js["total_shnu_qty4"], js["total_shnu_qty5"]], 
        "회원사비중" : [js["shnu_mbcr_rlim1"], js["shnu_mbcr_rlim2"], js["shnu_mbcr_rlim3"], js["shnu_mbcr_rlim4"], js["shnu_mbcr_rlim5"]], 
        "매수수량증감" : [js["shnu_qty_icdc1"], js["shnu_qty_icdc2"], js["shnu_qty_icdc3"], js["shnu_qty_icdc4"], js["shnu_qty_icdc5"]], 
        "외국계여부" : [js["shnu_mbcr_glob_yn_1"], js["shnu_mbcr_glob_yn_2"], js["shnu_mbcr_glob_yn_3"], js["shnu_mbcr_glob_yn_4"], js["shnu_mbcr_glob_yn_5"]], 
            }
        매도 = pd.DataFrame(sell_dic)
        매수 = pd.DataFrame(buy_dic)

        return 매수, 매도
        
    def _get_investor_today(self):
        '''
        # 0000:전체, 0001:코스피, 1001:코스닥 
        return : tuple 장중.(순매수df, 순매도.df)
        국내기관_외국인 매매종목가집계 API입니다.
        증권사 직원이 장중에 집계/입력한 자료를 단순 누계한 수치로서,
        # 상위 하위 검색.  종목별은 _get_invest_trend 사용. 
        ######
        입력시간은 외국인 09:30, 11:20, 13:20, 14:30 / 기관종합 10:00, 11:20, 13:20, 14:30 이며, 사정에 따라 변동될 수 있습니다.
        ######
        '''
       
        ############ 거래원 정보 가져오기################
        PATH = "/uapi/domestic-stock/v1/quotations/foreign-institution-total"
        URL = f"{self.URL_BASE}/{PATH}"
        
        params = {
            "FID_COND_MRKT_DIV_CODE":"V",
            "FID_COND_SCR_DIV_CODE" : "16449" ,
            "FID_INPUT_ISCD" : "1001" ,    #0000:전체, 0001:코스피, 1001:코스닥  - 포탈 (FAQ : 종목정보 다운로드 - 업종코드 참조)
            "FID_DIV_CLS_CODE" : "0" ,  ## 0: 수량정열, 1: 금액정열
            "FID_RANK_SORT_CLS_CODE" : "0" , ##	0: 순매수상위, 1: 순매도상위
            "FID_ETC_CLS_CODE" : "0" ,}    ## 0:전체 1:외국인 2:기관계 3:기타
        
        headers = {"Content-Type":"application/json", 
                "authorization": f"Bearer {self.ACCESS_TOKEN}",
                "appKey":self.APP_KEY,
                "appSecret":self.APP_SECRET,
                "tr_id":"FHPTJ04400000",
                "tr_cont": "",
                "hashkey":self._hashkey(params)}
        ## 주식현재가 시세의 tr_id는 "FHKST01010100" 
        
        json_ls = []
        for FID_INPUT_ISCD in ["0001","1001"]:
            for FID_RANK_SORT_CLS_CODE in ["0","1"]:
                params["FID_INPUT_ISCD"] = FID_INPUT_ISCD
                params["FID_RANK_SORT_CLS_CODE"] = FID_RANK_SORT_CLS_CODE
                res = requests.get(URL, headers=headers, params=params)
                try:
                    if res.headers['tr_cont'] != "":
                        print('연속조회가능.??')
                except:
                    print(f"{self._get_investor_today.__name__}")    

                time.sleep(0.3)
                ls = res.json().get('output')
                if ls:
                    json_ls += ls
                
        if len(json_ls):
            col_dic = {
                "hts_kor_isnm":	"종목명",	
                "mksc_shrn_iscd": "종목코드",
                "ntby_qty":	"순매수량",	
                "stck_prpr":"현재가",	
                "prdy_vrss_sign":"전일대비부호",	        
                "prdy_vrss":"전일대비",
                "prdy_ctrt":"전일대비율",	        
                "acml_vol":"거래량",
                "frgn_ntby_qty":"외국인",	
                "orgn_ntby_qty":"기관계",	
                "ivtr_ntby_qty":"투신",
                "bank_ntby_qty":"은행",
                "insu_ntby_qty":"보험",
                "mrbn_ntby_qty":"종금",
                "fund_ntby_qty":"기금",
                "etc_orgt_ntby_vol":"기타",
                "etc_corp_ntby_vol":"기타법인",
                "frgn_ntby_tr_pbmn":"외국인_거래대금",	                                                           
                "orgn_ntby_tr_pbmn":"기관계_거래대금",
                "ivtr_ntby_tr_pbmn":"투신_거래대금",
                "bank_ntby_tr_pbmn":"은행_거래대금",
                "insu_ntby_tr_pbmn":"보험_거래대금",
                "mrbn_ntby_tr_pbmn":"종금_거래대금",
                "fund_ntby_tr_pbmn":"기금_거래대금",
                "etc_orgt_ntby_tr_pbmn":"기타_거래대금",
                "etc_corp_ntby_tr_pbmn":"기타법인_거래대금",
                }
            
            col = ['종목명', '종목코드', '순매수량', '현재가','전일대비율', '거래량','외국인', '기관계', '투신', '은행', '보험', '종금', '기금', '기타', '기타법인', '외국인_거래대금',  
                    '기관계_거래대금', '투신_거래대금', '은행_거래대금', '보험_거래대금', '종금_거래대금', '기금_거래대금','기타_거래대금', '기타법인_거래대금']
            
            result = pd.DataFrame(json_ls)
            result = result.rename(columns=col_dic)
            for c in result.columns:
                if "종목" in c:
                    continue
                result[c] = pd.to_numeric(result[c],errors='coerce')
            
            ## 외국인 + 이면 상위 60  - 이면 하위 60
            
            
            return result
        else:
            return pd.DataFrame()
           
    def _get_volume_rank(self):
        ## 단타사용시 유용. 거래량 순위에서 회전율 고려하기. 
        ############ 거래량 순위 정보 가져오기################
        PATH = "/uapi/domestic-stock/v1/quotations/volume-rank"
        URL = f"{self.URL_BASE}/{PATH}"
        
        params = {
            "FID_COND_MRKT_DIV_CODE" : "J",  ## 시장분류코드
            "FID_COND_SCR_DIV_CODE" : "20171", # 화면번호
            "FID_INPUT_ISCD" : "0000",       ## 0000(전체) 기타(업종코드)
            "FID_DIV_CLS_CODE" : "0",    ## 0(전체) 1(보통주) 2(우선주)
            "FID_BLNG_CLS_CODE" : "2",  ## 소속구분 0  :  평균거래량 1 : 거래증가율 2 : 평균거래회전율 3 : 거래금액순 4 : 평균거래금액회전율 
            "FID_TRGT_CLS_CODE" : "000000000",         ## 대상구분 1 or 0 9자리 (차례대로 증거금 30% 40% 50% 60% 100% 신용보증금 30% 40% 50% 60%)ex) "111111111"
            "FID_TRGT_EXLS_CLS_CODE" : "111111",   ##대상제외 1 or 0 6자리 (차례대로 투자위험/경고/주의, 관리종목, 정리매매, 불성실공시, 우선주, 거래정지) ex) "000000"
            "FID_INPUT_PRICE_1" : "1000",       ## 가격 ~ ,전체 가격 대상 조회 시 FID_INPUT_PRICE_1, FID_INPUT_PRICE_2 모두 ""(공란) 입력
            "FID_INPUT_PRICE_2" : "9999999",       ## ~ 가격 , ex)"1000000"  전체 가격 대상 조회 시 FID_INPUT_PRICE_1, FID_INPUT_PRICE_2 모두 ""(공란) 입력
            "FID_VOL_CNT" : "100000",       ## 거래량 ~ ,전체 거래량 대상 조회 시 FID_VOL_CNT ""(공란) 입력
            "FID_INPUT_DATE_1" : "",       ## ""(공란) 입력
            }
        print('2')
        
        headers = {"Content-Type" : "application/json", 
                "authorization" :  f"Bearer {self.ACCESS_TOKEN}",
                "appKey" : self.APP_KEY,
                "appSecret" : self.APP_SECRET,
                "tr_id" : "FHPST01710000",
                "tr_cont" :  "",
                "hashkey" : self._hashkey(params) }
        
        res = requests.get(URL, headers=headers, params=params)
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_volume_rank.__name__}")    
        
        
        if res.json().get('output'):
            df = pd.DataFrame(res.json()['output'])
            col_dic = {
            "hts_kor_isnm" : "종목명",
            "mksc_shrn_iscd" : "종목코드",
            "data_rank" : "순위",
            "stck_prpr" : "현재가",
            "prdy_vrss_sign" : "전일대비부호",
            "prdy_vrss" : "전일대비",
            "prdy_ctrt" : "전일대비율",
            "acml_vol" : "누적거래량",
            "prdy_vol" : "전일거래량",
            "lstn_stcn" : "상장주수",
            "avrg_vol" : "평균거래량",
            "n_befr_clpr_vrss_prpr_rate" : "N일전종가대비현재가대비율",
            "vol_inrt" : "거래량증가율",
            "vol_tnrt" : "거래량회전율",
            "nday_vol_tnrt" : "N일거래량회전율",
            "avrg_tr_pbmn" : "평균거래대금",
            "tr_pbmn_tnrt" : "거래대금회전율",
            "nday_tr_pbmn_tnrt" : "N일거래대금회전율",
            "acml_tr_pbmn" : "누적거래대금",
            }
        df = df.rename(columns=col_dic)
        ## 숫자화. 
        for col in df.columns:
            if "종목" in col:
                continue
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # 상장주식수 대비 평균거래량, 
        # 거래량 회전율 50 이하
        # 거래대금 회전율
        cond_거래량회전율 = df['거래량회전율'] < 50
        cond_거래대금회전율 = df['거래대금회전율'] < 50
        cond_거래량 = df['평균거래량'] * 2 <= df['상장주수'] # 거래량 두배. 
        df = df.loc[cond_거래량회전율 & cond_거래대금회전율 & cond_거래량]
        df = df.sort_values(['전일대비율']) ## sorting
        return df
    
    def _get_invest_trend(self,code):
        '''
        국내주식 종목별 외국인, 기관 추정가집계 API입니다.
        한국투자 MTS > 국내 현재가 > 투자자 > 투자자동향 탭 > 왼쪽구분을 '추정(주)'로 선택 시 확인 가능한 데이터를 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.
        증권사 직원이 장중에 집계/입력한 자료를 단순 누계한 수치로서,
        입력시간은 외국인 09:30, 11:20, 13:20, 14:30 / 기관종합 10:00, 11:20, 13:20, 14:30 이며, 사정에 따라 변동될 수 있습니다.
        
        ### 차트에 오늘 가집계 그래프에 전달하기. 
        
        '''
        ############ tren 정보 가져오기################
        PATH = "/uapi/domestic-stock/v1/quotations/investor-trend-estimate"
        URL = f"{self.URL_BASE}/{PATH}"
        
        params = {
            "MKSC_SHRN_ISCD":code,   ## 종목코드
                }
        headers = {"Content-Type":"application/json", 
                "authorization": f"Bearer {self.ACCESS_TOKEN}",
                "appKey":self.APP_KEY,
                "appSecret":self.APP_SECRET,
                "tr_id":"HHPTJ04160200",
                "tr_cont": "",
                "hashkey":self._hashkey(params)}
        ## 주식현재가 시세의 tr_id는 "FHKST01010100" 
        
        res = requests.get(URL, headers=headers, params=params)
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_invest_trend.__name__}")    

        df = pd.DataFrame(res.json()['output2'])
        col_dic = {
                "bsop_hour_gb" : "입력구분",
                "frgn_fake_ntby_qty" : "외국인수량(가집계)",
                "orgn_fake_ntby_qty" : "기관수량(가집계)",
                "sum_fake_ntby_qty" : "합산수량(가집계)",}
        time_dic  = {
                "1" : "09시30분",
                "2" : "10시00분",
                "3" : "11시20분",
                "4" : "12시30분",
                "5" : "14시30분",
                }

        df = df.rename(columns=col_dic)

        for col in df.columns:
            df[col] = pd.to_numeric(df[col])
        df['입력구분'] = df['입력구분'].apply(lambda x: time_dic[str(x)])
        df = df.sort_values('입력구분')
        df = df.set_index('입력구분',drop=True)
        return df
    
    def _get_overtime_price(self,code):
        '''
        
        '''
        
        ############ tren 정보 가져오기################
        PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice"
        URL = f"{self.URL_BASE}/{PATH}"
        
        params = {
            "FID_COND_MRKT_DIV_CODE" : 'J',
            "FID_INPUT_ISCD" : code,   ## 종목코드
                }
        
        headers = {"Content-Type":"application/json", 
                "authorization": f"Bearer {self.ACCESS_TOKEN}",
                "appKey":self.APP_KEY,
                "appSecret":self.APP_SECRET,
                "tr_id":"FHPST02320000",
                "tr_cont": "",
                "hashkey":self._hashkey(params)}
        ## 주식현재가 시세의 tr_id는 "FHKST01010100" 
        
        res = requests.get(URL, headers=headers, params=params)
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_overtime_price.__name__}")    

        
        js = res.json()
        if js.get('output2'):
            df = pd.DataFrame(js['output2'])
            dic2 = {
                "stck_bsop_date" : "날짜",	
                "ovtm_untp_prpr" : "현재가",	
                "ovtm_untp_prdy_vrss" : "전일대비",	
                "ovtm_untp_prdy_vrss_sign" : "전일대비부호",	
                "ovtm_untp_prdy_ctrt" : "전일대비율",	
                "ovtm_untp_vol" : "거래량",	
                "stck_clpr" : "종가",	
                "prdy_vrss" : "정규장전일대비",	
                "prdy_vrss_sign" : "정규장전일대비부호",	
                "prdy_ctrt" : "정규장전일대비율",	
                "acml_vol" : "누적거래량",	
                "ovtm_untp_tr_pbmn" : "시간외단일가거래대금",	
                }
            df = df.rename(columns=dic2)
            
            df = df.set_index('날짜')
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors= 'coerce')
            df = df.sort_index()     
        else:
            print('요청오류')
            df = pd.DataFrame()
        return df
    
    def _get_ohlcv_min(self,code):
        '''
        
        '''
        ############ 당일 분봉가져오기. 정보 가져오기################
        PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        URL = f"{self.URL_BASE}/{PATH}"
        
        
        str_time = datetime.now().time().strftime("%H%M%S")
        ## 현재시간으로 요청함. 요청한 시간부터  30개 데이터만 가져옴. 쓸모있나.??
        params = {
            "FID_ETC_CLS_CODE" : '',
            "FID_COND_MRKT_DIV_CODE" : 'J',
            "FID_INPUT_ISCD" : code,   ## 종목코드
            "FID_INPUT_HOUR_1" : str_time,  ## 조회대상(FID_COND_MRKT_DIV_CODE)에 따라 입력하는 값 상이 종목(J)일 경우, 조회 시작일자(HHMMSS) ex) "123000" 입력 시 12시 30분 이전부터 1분 간격으로 조회
                                      ## 업종(U)일 경우, 조회간격(초) (60 or 120 만 입력 가능) ex) "60" 입력 시 현재시간부터 1분간격으로 조회 "120" 입력 시 현재시간부터 2분간격으로 조회
            "FID_PW_DATA_INCU_YN" : "",
                }
        
        headers = {"Content-Type":"application/json", 
                "authorization": f"Bearer {self.ACCESS_TOKEN}",
                "appKey":self.APP_KEY,
                "appSecret":self.APP_SECRET,
                "tr_id":"FHKST03010200",
                "tr_cont": "",
                "hashkey":self._hashkey(params)}

        
        res = requests.get(URL, headers=headers, params=params)
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_ohlcv_min.__name__}")    
            
        dic = {
            "stck_bsop_date" : "날짜",	
            "stck_cntg_hour" : "체결시간",	
            "acml_tr_pbmn" : "누적거래대금",	
            "stck_prpr" : "Close",	
            "stck_oprc" : "Open",	
            "stck_hgpr" : "High",	
            "stck_lwpr" : "Low",	
            "cntg_vol" : "volume",	   
            }
        js = res.json()
        if js.get("output2"):
            df = pd.DataFrame(js["output2"])
            df = df.rename(columns= dic)
            df['날짜'] = pd.to_datetime(df['날짜'])
            df['체결시간']= df['체결시간'].apply(lambda x : datetime.strptime(x,"%H%M%S").time())
            df = df.sort_values('체결시간')
            for col in df.columns[2:]:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        else:
            print('요청오류')
            return pd.DataFrame()
                

    
    ############# 휴장일 가져오기
    def _get_holiday(self):
        '''
        return tuple ,
        is_bzday : bool , remain_days_for_this_month : int
        '''
        today = datetime.today()
        str_today = today.strftime("%Y%m%d")
        PATH = "/uapi/domestic-stock/v1/quotations/chk-holiday"
        URL = f"{self.URL_BASE}/{PATH}"
            # BASS_DT	기준일자	기준일자(YYYYMMDD)
            # CTX_AREA_NK	연속조회키	String	Y	20	공백으로 입력
            # CTX_AREA_FK
        params = {
            "BASS_DT":str_today,
            "CTX_AREA_NK":"",
            "CTX_AREA_FK":"",}
        
        headers = {"Content-Type":"application/json", 
                "authorization": f"Bearer {self.ACCESS_TOKEN}",
                "appKey":self.APP_KEY,
                "appSecret":self.APP_SECRET,
                "tr_id":"CTCA0903R",
                "tr_cont": "",
                "hashkey":self._hashkey(params)}
        
        res = requests.get(URL, headers=headers, params=params)
        try:
            if res.headers['tr_cont'] != "":
                print('연속조회가능.??')
        except:
            print(f"{self._get_holiday.__name__}")    
            

        col = {"bass_dt":"기준일자",
            "wday_dvsn_cd":"요일구분코드",
            "bzdy_yn":"영업일여부",
            "tr_day_yn":"거래일여부",
            "opnd_yn":"개장일여부",
            "sttl_day_yn":"결제일여부",}
        weekday = {"01":"일요일", "02":"월요일", "03":"화요일", "04":"수요일", "05":"목요일", "06":"금요일", "07":"토요일"}

        if res.json().get('output'):
            
            df  = pd.DataFrame(res.json()['output'])
            df = df.rename(columns=col)
            df['요일구분코드'] = df['요일구분코드'].apply(lambda x: weekday[x])
            df['기준일자'] = pd.to_datetime(df['기준일자'])
            df  = df.set_index('기준일자',drop=True)

            # 오늘 영업일 여부 알아내기
            today =  datetime.today().date()
            today_month = today.month
            str_today = today.strftime('%Y-%m-%d')
            if df.loc[str_today,'영업일여부'] == 'N':
                is_bzday = False
            else:
                is_bzday = True

            ## 이번달 남은 영업일 알아내기.
            cond1 = df['영업일여부'] == "Y"
            cond2 = pd.DatetimeIndex(df.index).month == today_month
            remain_days_for_this_month = len(df.loc[cond1 & cond2])
            
            return is_bzday, remain_days_for_this_month
        else:
            print("'output' json이 없습니다.")
            return None

    ############# 모든 조건만족 종목 가져오기.############





class Trader():
    
    def __init__(self, cond_words = ['my']):
        self.data_path = os.path.dirname(os.path.realpath(__file__)) 
        self.cond_words= cond_words
        self.kis = Kis(cond_word=self.cond_words)
        print('kis객체 생성!')
        self.msg = astock.Msg(chat_name='종목알림')
        print('msg객체 생성!')
        print('my_cond_list_apply : ', self.kis.my_cond_list_apply)
        self.SENDED_CODE_LS =  []
        
        print('stocks객체 가져오는중.....')
        with open(f'{self.data_path}/datas/all_cls_by_astock.pkl', 'rb') as f:
            self.stocks = pickle.load(f)
        print('stocks 데이터 가져오기 성공')
        print("=============="*10)
        
        
    def get_code_list_for_cond_list(self, cond_list):
        '''
        cond_list 에 따라 code df 가져오기.  Kis._get_all_mycond_df() 와 같은 함수 
        '''
        try:
            all_ls = []
            for seq, cond_name in cond_list:
                print(seq, cond_name)
                result = self.kis._get_condition_code_list(seq)
                result['cond_name'] = cond_name
                all_ls.append(result)
                time.sleep(1)
            ## group 해서 cond name 합치기. 
            df = pd.concat(all_ls).reset_index(drop=True)
            df.head()
            grouped = df.groupby("종목명")
            all_ls = []
            for code_name, group in grouped:
                if len(group) >1:
                    group['cond_name'] = ','.join(list(group['cond_name']))
                all_ls.append(group)
            df = pd.concat(all_ls)
            df = df.drop_duplicates('종목명')
            col = ['종목코드', '종목명',  '현재가', '등락율', '거래량', '거래대금', '전일대비', '체결강도','시가', '고가', '저가', '전일거래량대비율',  '시가총액','cond_name']
            df = df[col].reset_index(drop=True)
            df['cond_cnt'] = df['cond_name'].str.count(',')
            df = df.sort_values(by=['cond_cnt','등락율'] , ascending=[False,False])
            return df
        except Exception as e:
            print(f"{e} 조건검색종목 가져오기 오류!!")
            return pd.DataFrame()
    
    def except_code(self, cond_code_df, now, cond_interval_min=120):
        '''
        Interval 에 따라 제외종목 정리하고. 새 종목에서 제외종목 제외하기. 
        '''
        if self.SENDED_CODE_LS:
            self.SENDED_CODE_LS = [items for items in self.SENDED_CODE_LS if (items[0] + timedelta(minutes=cond_interval_min)) >= now ]
            print('제외하고남은 보낸메세지 목록11' ,  self.SENDED_CODE_LS)
        print(f"현재 sended_code_ls: {self.SENDED_CODE_LS}")
        new_df = cond_code_df.loc[~cond_code_df['종목코드'].isin(self.SENDED_CODE_LS)]
        return new_df
    
    def send_choiced_code_5min(self, cond_interval_min=120, test_mode = False):
        print("==========" * 10)
        now = datetime.now()
        print(now)
        cond_df = self.get_code_list_for_cond_list(self.kis.my_cond_list_apply)  ###??? 시간에 따라 kis.my_cond_list_apply 변경필요. 
        if len(cond_df) ==0:
            print('조건검색 검색데이터 없음. !!')
            return 
        excepted_df  = self.except_code(cond_df, now, cond_interval_min=cond_interval_min)
            
        ## 2. 추출된 데이터 종목코드로 전체 stock 객체만 추출. 
        new_ohlcv_df = excepted_df['종목코드 종목명 시가 고가 저가 현재가 거래량 등락율'.split()].copy()
        new_ohlcv_df['Date'] = now.date()
        temp_dic  = {"종목코드":"code", "종목명":"code_name", "시가":"Open", "고가":"High", "저가":"Low", "현재가":"Close", "거래량":"Volume", "등락율":"Change"}
        # code(index) Open	High	Low	Close	Volume	Change Date 형태로 만듬. 
        new_ohlcv_df= new_ohlcv_df.rename(columns=temp_dic)
        new_ohlcv_df= new_ohlcv_df.set_index('code', drop=True)
        
        # new_ohlcv_df sorting 하고 객체 추출.
        new_stocks =[]
        new_ohlcv_df = new_ohlcv_df.sort_values("Change", ascending=False)
        for idx, row in new_ohlcv_df.iterrows():
            stock = [stock for stock in self.stocks if stock.code == idx]
            if len(stock):
                new_stocks.append(stock[0])
                
                
        ## 3. 추출된 객체 업데이트 (df 에서 ohlcv 추출.)
        # new_stocks = [ stock for stock in self.stocks if stock.code in list(new_ohlcv_df.index)]
        print(f"finded {len(new_stocks)} stocks. ")
        # # ohlcv df 가져와서 업데이트 하는 메써드 만들기. 
        
        
        # update
        start_time= time.time()
        new_updated_stocks=[]
        for stock in new_stocks:
            ## SENDED_CODE_LS 에 종목 포함되어있으면 pass
            if stock.code in [item[1] for item in self.SENDED_CODE_LS]:
                print(f'{stock.code} pass..................')
                continue
            stock._update_day(new_ohlcv_df)
            ## 4. check
            if stock.kis_cond():  ## check 됐을때만. ######################### 
                new_updated_stocks.append(stock)
        end_time = time.time()
        elapsed_time = end_time - start_time
        ## 추출된 데이터 개수 파악. 
        print(f"보낼데이터 총 개수 : {len(new_updated_stocks)} 종목! 작업 {elapsed_time:.1f}초 소요!")
        print("보낼데이터 ", [stock.code_name for stock in new_updated_stocks])
        
        # 데이터 너무 많으면 문자로 보내는 거 만들어야함. 
        if len(new_updated_stocks) > 20: # 1분에 5개밖에 보내지 못함. 
            over_choied= True
            try:
                ## text로 보낸 메세지는 sended_code_ls 에 추가하지 않음.  20개로 나누는게 아니고 20개씩 나누기. 
                msg_ls = [(s.code_name, s.df.iloc[-1]['Change']*100) for s in new_updated_stocks]
                msg_ls = [f"{item[0]}:{item[1]:.2f}%" for item in msg_ls] ## 등락율 함께 표기하기 위함.
                cnt = 0
                n= 20
                while True:
                    temp_ls = msg_ls[cnt:cnt+n]
                    if len(temp_ls):
                        txt = '\n'.join(temp_ls)
                        self.msg.send_message(txt)
                        time.sleep(1.5)
                        cnt += n
                    else:
                        break
            except Exception as e:
                print('전체 데이터 보내기 오류', e)
                
    
        print('메세지 보내기 시작!')
        start_time= time.time()
        cnt = 0
        for stock in new_updated_stocks:
            if cnt > 20:
                break
            temp_df = excepted_df.loc[excepted_df['종목코드'] == stock.code]
            cond_names = temp_df.iloc[0]['cond_name']
            change = temp_df.iloc[0]['등락율']
            current_price = temp_df.iloc[0]['현재가']
            전일대비거래량비 = temp_df.iloc[0]['전일거래량대비율']
            체결강도 = temp_df.iloc[0]['체결강도']
            거래대금_억 = temp_df.iloc[0]['거래대금']
        
            caption = f"{str(now)} 검색조건:=={cond_names}==\n==검색종목:{stock.code_name} {change:.1f}%\n현재가:{current_price:,}원\n전일대비거래량{전일대비거래량비:.1f}%\n체결강도{체결강도:.0f}% 거래대금:{(거래대금_억/100000):,.2f}억"
            
            try:
                if test_mode == False:
                    self._send_photo(stock, self.msg, caption )
                    self.SENDED_CODE_LS.append( (now, stock.code, stock.code_name) )
                    cnt +=1
                else:
                    print('test_mode send_message', caption)
                    self.SENDED_CODE_LS.append( (now, stock.code, stock.code_name) )
            except:
                pass
        
            
            
            
        end_time = time.time()
        elapsed_time = end_time - start_time

        print()
        print("==== 현재 보내진 종목들(2시간내) ====")
        print([items[2] for items in self.SENDED_CODE_LS])
        
        print(f"보내기 완료 작업{elapsed_time:.1f}초 소요!")
        
        
    def send_choiced_code_after_market(self, test_mode = False): # 종가매수
        print("==========" * 10)
        now = datetime.now()
        # new cond list 가져오기
        my_cond_list_apply = self.kis.extract_my_cond_list(['close']) ## 종가매수에 필요한 조건명 가져오기. 

        # 조건검색종목 가져오기
        cond_df = self.get_code_list_for_cond_list(my_cond_list_apply)   
        if len(cond_df) ==0:
            print('조건검색 검색데이터 없음. !!')
            return 

             
        ## 2. 추출된 데이터 종목코드로 전체 stock 객체만 추출. 
        new_ohlcv_df = cond_df['종목코드 종목명 시가 고가 저가 현재가 거래량 등락율'.split()].copy()
        new_ohlcv_df['Date'] = now.date()
        temp_dic  = {"종목코드":"code", "종목명":"code_name", "시가":"Open", "고가":"High", "저가":"Low", "현재가":"Close", "거래량":"Volume", "등락율":"Change"}
        # code(index) Open	High	Low	Close	Volume	Change Date 형태로 만듬. 
        new_ohlcv_df= new_ohlcv_df.rename(columns=temp_dic)
        new_ohlcv_df= new_ohlcv_df.set_index('code', drop=True)
        
        new_stocks =[]
        new_ohlcv_df = new_ohlcv_df.sort_values("Change", ascending=True) ## 종가베팅은 등락률 낮은거부터 알림.
        for idx, row in new_ohlcv_df.iterrows():
            stock = [stock for stock in self.stocks if stock.code == idx]
            if len(stock):
                new_stocks.append(stock[0])
        
        
        ## 3. 추출된 객체 업데이트 (df 에서 ohlcv 추출.)
        # new_stocks = [ stock for stock in self.stocks if stock.code in list(new_ohlcv_df.index)]
        print(f"finded {len(new_stocks)} stocks. ")
        
        ## 2차 추출 (내 조건과도 맞는지 확인.)
        start_time = time.time()
        new_updated_stocks=[]
        for stock in new_stocks:
            # if stock.code in [item[1] for item in self.SENDED_CODE_LS]:  ## 종가매수에는 기존데이터 무시하기.
            #     print(f'{stock.code} pass..................')
            #     continue
            stock._update_day(new_ohlcv_df)
            if stock._is_관종():
                new_updated_stocks.append(stock)
        end_time = time.time()
        elapsed_time = end_time - start_time
        ## 추출된 데이터 개수 파악. 
        print(f"보낼데이터 총 개수 : {len(new_updated_stocks)} 종목! {elapsed_time:.1f}초 소요!")
        print("보낼데이터 ", [stock.code_name for stock in new_updated_stocks])
        
        
        # 일단 text 로 보내기
        
        msg_ls = [s.code_name for s in new_updated_stocks]
        cnt = 0
        n= 25 # 한번에 보낼 종목수
        while True:
            temp_ls = msg_ls[cnt:cnt+n]
            if len(temp_ls):
                txt = '\n'.join(temp_ls)
                txt = "==종가매수==\n" + txt
                self.msg.send_message(txt)
                time.sleep(1.5)
                cnt += n
            else:
                break


        ## 그래프 문자 보내기.
        start_time = time.time()
        for stock in new_updated_stocks:
            temp_df = cond_df.loc[cond_df['종목코드'] == stock.code]
            cond_names = temp_df.iloc[0]['cond_name']
            change = temp_df.iloc[0]['등락율']
            current_price = temp_df.iloc[0]['현재가']
            전일대비거래량비 = temp_df.iloc[0]['전일거래량대비율']
            체결강도 = temp_df.iloc[0]['체결강도']
            거래대금_억 = temp_df.iloc[0]['거래대금']
        
            caption = f"==종가매수==\n{str(now)} 검색명:=={cond_names}==\n==검색종목:{stock.code_name} {change:.1f}%\n현재가:{current_price:,}원\n전일대비거래량{전일대비거래량비:.1f}%\n체결강도{체결강도:.0f}% 거래대금:{(거래대금_억/100000):,.2f}억"
            
            try:
                if test_mode == False:
                    self._send_photo(stock, self.msg, caption )
                    
                else:
                    print('test_mode send_message', caption)
                    
            except:
                pass
        end_time = time.time()
        elapsed_time = end_time - start_time
    
        print(f"보내기 완료 작업 {elapsed_time:.1f}초 소요!")
                
    def _send_photo(self, s, msg, caption):
        
        try:     ### trend 가 있으면 trend 그리기. 
            trend = self.kis._get_invest_trend(s.code)
            trend = trend.filter(regex="외국인.*|기관.*")
            fig = s._plot(cnt=120, trend=trend) ## fig 만들어
        except:
            fig = s._plot(cnt=120) ## fig 만들어
        
        buf = io.BytesIO()
        fig.savefig(buf,format='png',dpi=200)
        time.sleep(0.5)    ## 1초 쉬기. 객체만드는데 시간이 들어서 안쉬어도 될듯.
        buf.seek(0)
        msg._send_photo(photo= buf.read(), caption = caption)
        

class ScheduleJop():
    
    def __init__(self, cond_words=['my'], interval_min = 5, cond_interval_min=120, test_mode=False):
        '''
        interval_min : n 분마다 실행.
        cond_interval_min : n 분동안 보낸메세지 skip 
        '''
        self.trader = Trader(cond_words=cond_words)
        if test_mode == False:
            if not self.trader.kis._is_bzday()[0]:
                print('휴장일 작업 중지.')
                sys.exit()
            pass
            
        '''
        2024년 1월24일 기준--
        send_choiced_code_5min 은 self.kis_cond() 적용
        send_choiced_code_after_market 은 self._is_관종() 적용
        
        '''
        self.interval_job_schedule = schedule.every(interval_min).minutes.do(self.trader.send_choiced_code_5min, cond_interval_min, test_mode) #3분마다 실행 조건 검색 가져와서 종목 확인하기.
        self.cancel_job_schedule = schedule.every().day.at("15:05:00").do(self.cancel_job) # 특정시간에 필요한 작업실행.
        self.last_condition_job_schedule = schedule.every().day.at("15:06:00").do(self.trader.send_choiced_code_after_market, test_mode)
        self.finish_job_schedule = schedule.every().day.at("15:50:00").do(self.finished) #특정시간에 코드실행 중지!
   
        # 시작할때 한번 먼저 실행하기. 
        print('start running....')
        self.trader.send_choiced_code_5min(cond_interval_min=cond_interval_min,  test_mode=test_mode )
        
        ## 일시적 작업 테스트.
        # self.last_condition_job_schedule = schedule.every().day.at("17:24:00").do(self.trader.send_choiced_code_after_market, test_mode)
        # #실제 실행하게 하는 코드
        while True:
            try:
                schedule.run_pending()
            except Exception as e:
                print('while True err',e)
            # print('sleep' , end=",")
            time.sleep(0.9)
    
    def cancel_job(self):
        schedule.cancel_job(self.interval_job_schedule)
        now = datetime.now()
        print(f'주기적 조회 실행 중지!{now}')
    
    def the_time_job(self):
        ## 장중 투자자  또는 거래량 순위. 또는 전체 상승종목 , 특정시간에 해야할일 정의하기. ????####
        print('특정시간 작업 시작 완료.')
    
    def finished(self):
        now = datetime.now()
        print("작업종료:",now)
        sys.exit("모든 작업 종료")
    
 
          