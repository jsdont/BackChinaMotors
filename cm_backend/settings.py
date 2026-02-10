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

    "catalog",
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

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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
    "http://localhost:4200",
]

CSRF_TRUSTED_ORIGINS = [
    "https://china-motors-site.netlify.app",
    "https://chinamotors.com.kz",
    "https://www.chinamotors.com.kz",
    "https://cm-backend-daniyal.fly.dev",
    "https://jsdont.github.io",
]

# Cloudinary
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

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
