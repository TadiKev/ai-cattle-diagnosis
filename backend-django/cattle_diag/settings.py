# backend-django/cattle_diag/settings.py
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Base dirs
BASE_DIR = Path(__file__).resolve().parent.parent         # backend-django/
PROJECT_ROOT = BASE_DIR.parent                            # repo root (ai-cattle-diagnosis)

# Load .env from repo root if present
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Optional: dj_database_url for DATABASE_URL parsing (may not be installed in dev)
try:
    import dj_database_url  # type: ignore
except Exception:
    dj_database_url = None

# Inference service config (used by backend code)
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://ml-inference:8001")
INFERENCE_SECRET = os.getenv("INFERENCE_SECRET", os.getenv("INFERENCE_TOKEN", "change-me"))

INFERENCE_URL = "http://127.0.0.1:8001/predict"
INFERENCE_SECRET = "dev-secret-please-change"
INFERENCE_ALLOW_FALLBACK = False
ML_TEMP = 1.0  # <1.0 sharpens, >1.0 smooths probabilities; tune later
ML_KEYWORD_BOOST = 0.18
ML_UNCERTAINTY_THRESHOLD = 0.5
INFERENCE_ALLOW_FALLBACK = True
SAMPLE_GRADCAM_PATH = "/mnt/data/8f8836c2-e4d4-4caf-8536-bda95d776817.png"
# Basic settings
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-placeholder-change-me")
DEBUG = os.getenv("DEBUG", "1") in ("1", "True", "true", "TRUE")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Applications
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",

    # Local apps
    "api.apps.ApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cattle_diag.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "cattle_diag.wsgi.application"

# Database: prefer DATABASE_URL, fall back to sqlite
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL and dj_database_url:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
elif DATABASE_URL and not dj_database_url:
    # NOTE: dj_database_url missing - parse minimal postgres DSN manually if needed (quick fallback)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "cattle_db"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Auth
AUTH_USER_MODEL = "api.CustomUser"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Africa/Harare")
USE_I18N = True
USE_TZ = True

# Static & media
STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_ROOT / "media"

# Default primary key field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF + JWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", 60))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS - dev convenience
if os.getenv("CORS_ALLOW_ALL", "1") in ("1", "True", "true", "TRUE"):
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
