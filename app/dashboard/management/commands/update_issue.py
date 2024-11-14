from django.core.management import BaseCommand
from dashboard.utils.dbupdater import DBUpdater

class Command(BaseCommand):
    help = 'Ticker 모델 업데이트 하는 명령'
 
    def handle(self, *args, **options):
        
        DBUpdater.update_issue()
        
        