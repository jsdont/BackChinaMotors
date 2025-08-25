FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=cm_backend.settings

WORKDIR /code

# зависимости, чтобы не страдать
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . /code

# WhiteNoise будет отдавать статику из STATIC_ROOT
# collectstatic выполняем в release_command (fly.toml), не здесь

EXPOSE 8000

CMD ["gunicorn", "cm_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
