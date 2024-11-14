from django.apps import AppConfig
import asyncio
import os
from threading import Thread
from django.conf import settings
from django.db.models.signals import post_migrate
from dashboard.utils.discord_bot import MyDiscordBot


class StockDashboardConfig(AppConfig):
# class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = '주식정보'

        
    def ready(self):
        if not settings.DEBUG:
            discord_bot = MyDiscordBot()
            thread = Thread(target=discord_bot.run_bot)
            thread.daemon = True  # 메인 스레드 종료 시 함께 종료
            thread.start()

