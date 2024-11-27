import json
from django.core.management.base import BaseCommand
from django.apps import apps


class Command(BaseCommand):
    help = 'Restore Book model data from a JSON file 이파일과 백업파일은 동작하지 않음 Serializer 직렬화 역직열화가 필요함. '

    def handle(self, *args, **kwargs):
        
        model_list = ['dashboard.Ticker']
        for model_name in model_list:
            # JSON 파일 경로
            split_model_name=model_name.split('.')
            
            file_path = f"backup_{'.'.join(model_name).lower()}.json"

            # JSON 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            model_obj = apps.get_model(*split_model_name)
            # 데이터베이스에 저장
            create_cnt=0
            update_cnt=0
            for item in data:
                # 객체 생성 및 저장
                the_model, created = model_obj.objects.update_or_create(
                    id=item['id'],  # id가 존재하는 경우 업데이트, 없으면 새로 생성
                    defaults={**item}
                )
                if created:
                    create_cnt +=1
                else:
                    update_cnt +=1
            self.stdout.write(self.style.SUCCESS(f'Created model: {create_cnt}'))
            self.stdout.write(self.style.SUCCESS(f'Updated model: {update_cnt}'))