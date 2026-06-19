"""
app/settings.py
===============
Django settings for development and production.

Environment variables (set in Render):
  SECRET_KEY       - Random long string (required in production)
  DEBUG            - "False" in production
  ALLOWED_HOSTS    - Your Render domain, e.g. "my-app.onrender.com"
  BOT_TOKEN        - Telegram bot token from BotFather
  ALLOWED_TG_IDS   - Comma-separated Telegram IDs, e.g. "123,456"
  CLOUDINARY_CLOUD_NAME  - Cloudinary cloud name
  CLOUDINARY_API_KEY     - Cloudinary API key
  CLOUDINARY_API_SECRET  - Cloudinary API secret
  GEMINI_API_KEY   - Google Gemini API key
  WEB_APP_URL      - Full URL of the deployed app
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-only-insecure-key-change-in-production-please"
)

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS_ENV = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(",") if h.strip()]
if DEBUG or not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

# ── Templates ─────────────────────────────────────────────────────────────────
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
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── Internationalization ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ── Static Files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Bot Config ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Allowed Telegram IDs - only these users can access the mini-app
_allowed_raw = os.environ.get("ALLOWED_TG_IDS", "")
ALLOWED_TG_IDS = [
    int(i.strip()) for i in _allowed_raw.split(",") if i.strip().isdigit()
]

# ── Cloudinary Config ─────────────────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

# ── Gemini Config ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ── Web App URL ───────────────────────────────────────────────────────────────
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://your-app.onrender.com")

# ── Media Cleanup ─────────────────────────────────────────────────────────────
# Days after which media files are auto-deleted from Cloudinary
MEDIA_RETENTION_DAYS = int(os.environ.get("MEDIA_RETENTION_DAYS", "30"))

# ── File Upload Limits ────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20MB
