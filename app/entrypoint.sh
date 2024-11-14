#!/bin/bash
set -e  # 명령어 실행 중 오류 발생 시 종료

python manage.py migrate || true  # 마이그레이션 실패해도 무시
python manage.py runserver 0.0.0.0:8000