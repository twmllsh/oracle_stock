import json
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Backup Book model data to a JSON file'

    def handle(self, *args, **kwargs):
        model_list = ['dashboard.Ticker']
        for model_name in model_list:
            split_model_name=model_name.split('.')
            model_obj = apps.get_model(*split_model_name)
            qs = model_obj.objects.all().values()  # 모든 Book 객체 가져오기
            backup_data = list(qs)

            with open(f"backup_{'.'.join(split_model_name).lower()}.json", 'w') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)
            self.stdout.write(self.style.SUCCESS(f'{model_name} Backup completed successfully!'))