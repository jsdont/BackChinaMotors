FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . /code

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "cm_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
