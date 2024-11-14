FROM postgres:14

ENV POSTGRES_DB=${POSTGRES_DB}
ENV POSTGRES_USER=${POSTGRES_USER}
ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# PostgreSQL 설정을 위한 파일 복사
COPY ./pg_hba.conf /etc/postgresql/pg_hba.conf
COPY ./postgresql.conf /etc/postgresql/postgresql.conf


CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
