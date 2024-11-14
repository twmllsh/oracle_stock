# 1. Python 3.11 공식 이미지 기반 설정
FROM python:3.11.10-bullseye

ENV LC_ALL=C.UTF-8
ENV TZ Asia/Seoul 
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 필수 패키지 설치 (TA-Lib을 빌드하는 데 필요한 패키지 포함)
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    gcc \
    make \
    libffi-dev \
    python3-dev \
    python3-distutils \
    python3-pip \
    autoconf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# TA-Lib 소스코드를 다운로드하고 설치
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib 
    # && ./configure \
WORKDIR /ta-lib
RUN ./configure --build=aarch64-unknown-linux-gnu \
    && make \
    && make install \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# RUN apt install -y fonts-nanum && \
#     apt install -y fonts-noto-cjk

# 환경 변수 설정
ENV LD_LIBRARY_PATH=/usr/local/lib
# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. Python 라이브러리 설치
COPY requirements.txt .
COPY requirements/ ./requirements/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. 프로젝트 파일 전체 복사
COPY . .

# 포트 설정 (디폴트는 8000)
EXPOSE 8000
EXPOSE 8888


# 7. 컨테이너 시작 시 실행할 명령어
# CMD sh -c "python app.py && tail -f /dev/null"
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]