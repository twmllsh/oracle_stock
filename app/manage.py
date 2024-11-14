#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from django.core.management import call_command
from django.conf import settings
import dotenv

def main():
    dotenv.read_dotenv()
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # 마이그레이션 실행하고 server 시작하기 
    #if not settings.DEBUG:
    #    call_command('migrate')

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
