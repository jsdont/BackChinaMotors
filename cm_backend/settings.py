from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
# secret берём из секретов Fly
# Берём ключ из DJANGO_SECRET_KEY или из SECRET_KEY.

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-build-key")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Уведомления: e-mail (SMTP) и SMS ---
# Без EMAIL_HOST используем консольный бэкенд: письма печатаются в логи и
# наружу ничего не уходит, пока не заданы реальные SMTP-секреты на Fly.
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "China Motors <no-reply@chinamotors.kz>")

# SMS-шлюз (опционально). Универсальный HTTP-POST под шлюзы вроде SMSC.kz /
# Mobizon. Без SMS_GATEWAY_URL SMS-отправка просто отключена.
SMS_GATEWAY_URL = os.getenv("SMS_GATEWAY_URL", "")
SMS_GATEWAY_LOGIN = os.getenv("SMS_GATEWAY_LOGIN", "")
SMS_GATEWAY_PASSWORD = os.getenv("SMS_GATEWAY_PASSWORD", "")
SMS_GATEWAY_SENDER = os.getenv("SMS_GATEWAY_SENDER", "ChinaMotors")

# Текст «как оплатить» (реквизиты банка/Kaspi) — показывается клиенту по
# сделке с остатком к оплате. Настраивается через переменную окружения.
PAYMENT_INSTRUCTIONS = os.getenv("PAYMENT_INSTRUCTIONS", "")

DJANGO_DEBUG=True

DEBUG = os.getenv("DEBUG", "false").lower() == "true"


ALLOWED_HOSTS = ["127.0.0.1", "localhost", "cm-backend-daniyal.fly.dev", "cm-backend-daniyal-blue-pond-9890.fly.dev", "chinamotors.com.kz", "www.chinamotors.com.kz"]


INSTALLED_APPS = [
    "corsheaders",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "django_filters",

    "cloudinary",
    "cloudinary_storage",

    "cars",
    "core",
    "app",
    "drf_spectacular",
    "rest_framework_simplejwt",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]



ROOT_URLCONF = "cm_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cm_backend.wsgi.application"

# БД: сначала пробуем DATABASE_URL, иначе SQLite
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///db.sqlite3"
    )
}
# Язык/время — без фанатизма
LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

# Статика + WhiteNoise
# === STATIC FILES ===
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Django 5.1+ читает ТОЛЬКО STORAGES; DEFAULT_FILE_STORAGE / STATICFILES_STORAGE
# в новых версиях игнорируются, из-за чего загрузки падали на эфемерный диск Fly
# и пропадали после рестарта. default -> Cloudinary (постоянное хранилище),
# staticfiles -> WhiteNoise. Требуется секрет CLOUDINARY_URL.
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ChinaMotors API",
    "DESCRIPTION": "Vehicles, rates, telegram endpoint",
    "VERSION": "1.0.0",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://cm-backend-daniyal.fly.dev",
    "https://cm-backend-daniyal-blue-pond-9890.fly.dev",
    "https://jsdont.github.io",
    "https://chinamotors.com.kz",
    "https://www.chinamotors.com.kz", # если используете
    "https://chinamotors.kz",
    "https://www.chinamotors.kz",
    "https://china-motors-site.netlify.app",
    "http://localhost:4200",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

CSRF_TRUSTED_ORIGINS = [
    "https://china-motors-site.netlify.app",
    "https://chinamotors.com.kz",
    "https://www.chinamotors.com.kz",
    "https://chinamotors.kz",
    "https://www.chinamotors.kz",
    "https://cm-backend-daniyal.fly.dev",
    "https://jsdont.github.io",
]

# Cloudinary (хранилище задано выше через STORAGES["default"])
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

MEDIA_URL = '/media/'  # Django всё равно ждёт URL, но физически файлы в Cloudinary



# Логирование в консоль (видно в fly logs)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
AUTH_USER_MODEL = 'core.User'
from datetime import timedelta

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}



SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
