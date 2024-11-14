from django.core.management import BaseCommand
# from django.core.management.base import CommandParser
# from myapp2.utils.dbupdater import GetData, DBUpdater
from dashboard.utils.dbupdater import GetData, DBUpdater

class Command(BaseCommand):
    help = "Ticker 모델 업데이트 하는 명령"

    # def add_arguments(self, parser: CommandParser) -> None:
        
    #     parser.add_argument('test_cnt', type=int, help='테스트로 test_cnt개만 수행한다.')
    #     # return super().add_arguments(parser)
    
    def handle(self, *args, **options):
        
        # update_codes= ['011230','000910','081150']
        
        DBUpdater.update_basic_info()
        