import asyncio
import os
import io
from django.conf import settings
import matplotlib.pyplot as plt
import plotly.io as pio
import telegram
from discord.webhook import SyncWebhook
from discord import Embed, File
import numpy as np
import pandas as pd
from . import config

## https://janu8ry.tistory.com/7?category=957746 # Bot 참고하기. 
# https://janu8ry.tistory.com/9?category=957746  #embed 참고
# embed 색상참고.
## https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=1&ie=utf8&query=%EC%83%89%EC%83%81+%ED%8C%94%EB%A0%88%ED%8A%B8





class My_discord:

    def __init__(self, webhook_url=None):
       
        if webhook_url is None:
            webhook_url = settings.MYENV('DISCORD_WEBHOOK_URL')
            # print("webhook_url:" , webhook_url)
        
        self.data_path = os.path.dirname(os.path.realpath(__file__)) 
        self.wh = SyncWebhook.from_url(webhook_url)
    
    
    async def send_message(self, text):
        self.wh.send(text)
    
    async def send_photo(self, file_path=None, fig=None):
        
        if not fig is None:
            temp_folder_path = f"{self.data_path}/temp_folder/"
            if not os.path.exists(temp_folder_path):
                os.makedirs(temp_folder_path, exist_ok=True)
                
            file_path = f'{temp_folder_path}/temp.png'
            pio.write_image(fig, file_path, 'png')
            
        if file_path is None:
            print('send_photo err')
            return
        
        with open(file_path, 'rb') as image:
            self.wh.send(file=File(image),)
    
    async def df_to_embed_send(self, df:pd.DataFrame, corp_name_col:list, columns:list, dart_title:str, description:str ) -> None:
        '''
        dart_title = '공급계약공시'
        description = "최근매출대비 20%이상 공시입니다."
        corp_name_col = 'corp_name'
        columns = ["corp_name","계약명","계약금액(억)","매출액대비(%)","계약상대","계약시작일","계약종료일"]
        '''
        all_ls = []
        for i, row in df.iterrows():
            dic = {}
            dic['title'] = f"{dart_title} - ({row[corp_name_col]})"
            dic["description"] = description
            dic['color'] = 0xAAFFFF
            dic['field_data'] = []
            for col in columns:
                f_dic = {"name":col, "value" :row[col], "inline" :True }
                dic['field_data'].append(f_dic)
            all_ls.append(dic)

        # Embed 만들기.
        for dic in all_ls:
            embed = Embed(title=dic['title'],
                        description=dic['description'],
                        color=dic['color'])
            for f_dic in dic['field_data']:
                embed.add_field(name=f_dic['name'], value=f_dic['value'], inline=f_dic['inline'])
            # 인베드 보내기. 
            
            await self.send_embed(embed)    
    
    async def send_embed(self, embed):
        '''
        embed 객체 생성해서 전달해야함. 
        '''
        
        
        self.wh.send(embed=embed)
        
class My_telegram():
    '''
    msg 보내기. 단일 보내기와 asynio 로 여러개 동시 보내기 (list or dict 로 받아 )기능 포함하기. telegram ver 20 이상에서만 사용가능. 
    '''
    def __init__(self, token=None, chat_id=None, data_path=None, chat_name="sean78_bot"):
        """
           telegram v20 비동기방식.
        chat_id:
           sean78_bot
           나의채널
           공시알림
           종목알림
           뉴스알림
           종목조회
           CB알림채널
           나의그룹
           키움알림
           야깡평아!
        """
        ## token check!
        if data_path == None:
            self.data_path = os.path.dirname(os.path.realpath(__file__))
        else:
            self.data_path = data_path

        if token == None:
            # self.token = config.get_telegram_token()
            self.token = settings.MYENV("TELEGRAM_TOKEN")
            
        else:
            self.token = token
        # self.chat_id = config.get_telegram_chat_id(chat_name)
        self.chat_id = settings.MYENV("TELEGRAM_CHAT_ID_SEAN78")
        
        self.bot = telegram.Bot(token=self.token)

    def to_byteio(fig):
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png")
        buffer.seek(0)
        return buffer

    async def _asend_message(self, text, **kwargs):
        await self.bot.send_message(chat_id=self.chat_id, text=text, **kwargs)

    async def _asend_photo(self,photo, **kwargs):
        """
        Byteio 사용법.
        import io
        def to_byteio(fig):
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png")
            buffer.seek(0)
        return buffer
        buffer = to_byteio(fig)
        asyncio.run(self.bot.send_photo(photo=buffer.read()))
        
        photo 경로로 보낼때 : photo=open('이미지_파일_경로', 'rb')
        """
        if isinstance(photo, plt.Figure):
            photo = self.to_byteio(photo).read()
        await self.bot.send_photo(chat_id=self.chat_id, photo=photo, **kwargs)

    async def _asend_file(self, file, **kwargs):
        await self.bot.send_document(chat_id=self.chat_id, document=file)

    def send_message(self, text, **kwargs):
        # asyncio.run(self.bot.send_message(chat_id=self.chat_id, text = txt))
        asyncio.run(self._asend_message(text=text, **kwargs))

    def send_photo(self, photo, **kwargs):
        # asyncio.run(self.bot.send_message(chat_id=self.chat_id, text = txt))
        asyncio.run(self._asend_photo(photo=photo, **kwargs))

    def send_document(self, file, **kwargs):
        asyncio.run(self._asend_file(file, **kwargs))

    def _send_message(self, text, **kwargs):
        # asyncio.run(self.bot.send_message(chat_id=self.chat_id, text = txt))
        asyncio.run(self._asend_message(text=text, **kwargs))

    def _send_photo(self, photo, **kwargs):
        # asyncio.run(self.bot.send_message(chat_id=self.chat_id, text = txt))
        asyncio.run(self._asend_photo(photo=photo, **kwargs))
        
    def _send_document(self, file, **kwargs):
        asyncio.run(self._asend_file(file, **kwargs))
        
    def _df_to_msgtext(self, df, extract_col=[], title=""):
        """
        index : 종목 columns 은 종목의 속성  인 df
        index별 내용 전달 텍스트 생성 list 형
        extract = ['',''] 변환할 col만.
        :return: list  테스트 필요
        """

        ## 데이터프레임 전체내용 메세지 보낼때.[메세지 리스트 반환.]
        ## 필요한  column 만 추출한  df생성후 인자로 넣어줌.

        msg_list = []
        if len(extract_col) == 0:
            col_list = list(df.columns)
        else:
            col_list = [item for item in extract_col if item in df.columns]
            if not len(col_list):
                return []

        for ix, row in df.iterrows():
            if title != "":
                msg_text = f"=== {title} ===\n"
            else:
                msg_text = ""

            for col in col_list:
                value = row[col]
                if str(type(value)) == "<class 'int'>":  ## 숫자면 천단위 콤마,  넣고. str타입변경
                    value = format(value, ",")
                else:
                    value = value
                temp_text = f"{col}  : {value} \n"
                msg_text = msg_text + temp_text

            msg_list.append(msg_text)
        return msg_list

    def _dic_to_msgtext(self, dic):
        """
        모든 타입은 그냥  str으로 변환하면 된다. 수정하자.!
        :return:
        """
        ## 딕셔너리 형태를 메세지 보낼때 . text반환.
        text = ""
        for key, value in dic.items():
            if str(type(value)) == "<class 'int'>":
                value_int = format(value, ",")
            else:
                value_int = value
            #     key_text = '{0:<1}'.format(key)
            text = text + "{} : {}\n".format(key, value_int)
        return text

async def test_main():
    
    my_telegram = My_telegram()
    my_discord = My_discord()
    
    tasks = [
        asyncio.create_task(my_telegram._asend_message('test message')),
        asyncio.create_task(my_discord.send_message('test message')),
        ]
    await asyncio.gather(*tasks)
    
    
if __name__ == "__main__":
    
    asyncio.run(test_main())
   