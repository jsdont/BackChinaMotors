# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# system deps (минимум)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# python deps
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# проект
COPY . /code

# Django settings модуль (если у тебя другой — поправь)
ENV DJANGO_SETTINGS_MODULE=cm_backend.settings

# внешний порт контейнера
EXPOSE 8000

# ВАЖНО: слушаем 0.0.0.0:8000
CMD ["gunicorn", "cm_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
