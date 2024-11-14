import json
from pathlib import Path
from typing import Optional

CURRENT_DIR = Path(__file__).resolve().parent  # 노트북에서는 path  = !pwd 문법 사용

# print(f"CURRENT_DIR: {CURRENT_DIR}")
JSON_PATH = str(CURRENT_DIR / ".secrets.json")
# print(f"JSON_PATH: {JSON_PATH}")


## .secrets.json 파일을 찾기와 못찾았을 경우 



def get_telegram_token(key:str = "TELEGRAM_TOKEN",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    '''
    "TELEGRAM_TOKEN"
    "TELEGRAM_SEAN1_TOKEN"
    "TELEGRAM_KKANG_TOKEN"
    '''
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets[key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")

def get_telegram_chat_id(key:str = "sean78_bot",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    '''
    "sean78_bot"
    "나의채널"
    "나의그룹"
    "공시알림"
    "종목알림"
    "뉴스알림"
    "종목조회"
    "CB알림채널"
    '''
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets['TELEGRAM_CHAT_ID'][key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")

def get_discord_bot_token(key:str = "DISCORD_BOT_TOKEN",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets[key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")



def get_discord_webhook_url(key:str = "DISCORD_WEBHOOK_URL",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets[key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")
    


def get_open_dart_token(key:str = "OPEN_DART_TOKEN",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets[key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")
    


def get_kis_key_dict(key:str = "KIS",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    '''
    KIS (실전)
    KIS_TEST (모의)
    '''
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets[key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")
    
def get_mysql_key_dict(key:str = "MY_SQL",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    '''
    MY_SQL
    '''
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets[key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")
    
def get_upbit_key_dict(key:str = "UPBIT",default_value: Optional[str]= None, json_path:str =  JSON_PATH):
    '''
    UPBIT
    '''
    with open(json_path) as f:
        secrets = json.loads(f.read())
        
    try:
        return secrets[key]
    except KeyError:
        if default_value:
            return default_value
        raise EnvironmentError(f"Set the {key} environment variable")







if __name__ == '__main__':
    token = get_upbit_key_dict()
    print(token)
    print(type(token))
