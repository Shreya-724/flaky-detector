"""
Django settings for flaky-detector.

Everything environment-specific comes from environment variables (loaded from
backend/.env in local dev), so the same file runs on a laptop and on Render.
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Real environment variables win over .env (load_dotenv never overrides), which is
# what lets `$env:DATABASE_URL=...` in a terminal point a one-off command at another DB.
load_dotenv(BASE_DIR / ".env")


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


# ---- core ---------------------------------------------------------------------

DEBUG = os.environ.get("DEBUG", "True") == "True"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-not-for-production")
if not DEBUG and SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a real secret when DEBUG is False.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Render sets this automatically for every web service.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Where the React app lives: used for CORS and for links inside alert messages.
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173")
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# ---- apps / middleware ----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "detector",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must sit above anything that can generate a response
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves collected static files (admin CSS) in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---- database -------------------------------------------------------------------

# DATABASE_URL unset -> SQLite. Set -> Postgres (local Docker, or Neon in production).
# conn_health_checks: Neon suspends idle databases, which kills pooled connections;
# this makes Django check a reused connection is alive before using it.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---- static files (Django admin CSS/JS) -------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- production hardening (only when DEBUG is off) ----------------------------------

if not DEBUG:
    # TLS ends at Render's proxy, which tells us the original scheme via this header.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ---- DRF / API docs ---------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min"},
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "flaky-detector API",
    "DESCRIPTION": (
        "Detects flaky tests from CI history. Upload JUnit XML reports from CI, "
        "browse ranked flaky tests on a public dashboard, and manage projects "
        "(auth required) — including quarantining tests and rotating CI tokens."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "ingest", "description": "CI uploads a JUnit XML report here. Authenticated with a per-project token, not JWT."},
        {"name": "tests", "description": "Public, unauthenticated: ranked flaky tests and per-test history."},
        {"name": "errors", "description": "Public: grouped failure messages."},
        {"name": "stats", "description": "Public: headline dashboard numbers."},
        {"name": "badge", "description": "Public: embeddable SVG status badge for READMEs."},
        {"name": "auth", "description": "Account registration and login. Returns JWTs."},
        {"name": "projects", "description": "Owner-only project management. Requires a JWT (see auth)."},
    ],
}

# ---- email (flaky-test alerts, see detector/notifications.py) ------------------------
# No EMAIL_HOST -> emails print to the server console. EMAIL_HOST set -> real SMTP.

EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "flaky-detector@localhost")