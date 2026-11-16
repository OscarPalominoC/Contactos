# Backend Dockerfile - Check Contactos (Django 5 + Python 3.13)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    openssl \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

COPY . /app/backend/
COPY ../scripts /app/scripts
COPY ../docker/backend/entrypoint.sh /app/docker/backend/entrypoint.sh
RUN sed -i '1s/^\xef\xbb\xbf//' /app/docker/backend/entrypoint.sh && \
    sed -i 's/\r$//' /app/docker/backend/entrypoint.sh && \
    chmod +x /app/docker/backend/entrypoint.sh

RUN mkdir -p /app/backend/staticfiles /app/backend/keys /app/logs

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/docker/backend/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

