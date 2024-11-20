from django.core.management import BaseCommand
from usa.utils import dbupdater

class Command(BaseCommand):
    help = 'Ticker 모델 업데이트 하는 명령'
 
    def handle(self, *args, **options):
        
        dbupdater.update_ticker_usa()
        
        
        
       