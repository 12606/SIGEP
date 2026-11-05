import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("Falta DJANGO_SECRET_KEY en backend/.env")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",
    "usuarios",
    "clientes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR.parent / "frontend"], "APP_DIRS": True,
     "OPTIONS": {"context_processors": [
         "django.template.context_processors.debug",
         "django.template.context_processors.request",
         "django.contrib.auth.context_processors.auth",
         "django.contrib.messages.context_processors.messages",
     ]}},
]
WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("DB_ENGINE", "mariadb").lower() == "sqlite":
    # DB temporal para pruebas locales. No cambia la configuracion de MariaDB.
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "local_test.sqlite3"}}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "sigep"),
        "USER": os.getenv("DB_USER", "sigep_app"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
    }}

AUTH_USER_MODEL = "usuarios.Usuario"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "CHECK_USER_IS_ACTIVE": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
# El frontend se sirve desde Django en la MISMA URL y puerto 8000.
STATICFILES_DIRS = [BASE_DIR.parent / "frontend"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS opcional, solo para quien pruebe otro servidor frontend (p. ej. puerto 5500).
# El uso recomendado es http://127.0.0.1:8000/ y no necesita CORS.
CORS_ALLOWED_ORIGINS = [
    origen.strip() for origen in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500",
    ).split(",") if origen.strip()
]
CORS_URLS_REGEX = r"^/api/"
