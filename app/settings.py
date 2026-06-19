"""
app/settings.py
===============
تنظیمات Django برای محیط‌های development و production.

متغیرهای محیطی مهم (در Render باید ست کنید):
  SECRET_KEY      → یه رشته تصادفی طولانی (اجباری در production)
  DEBUG           → "False" در production
  ALLOWED_HOSTS   → دامنه Render شما، مثل "my-app.onrender.com"
  BOT_TOKEN       → توکن ربات تلگرام از BotFather
  ALLOWED_TG_IDS  → آیدی‌های تلگرام که اجازه دارن (مثل "123,456")
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
# در production حتماً SECRET_KEY رو از environment بخونید
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-only-insecure-key-change-in-production-please"
)

DEBUG = os.environ.get("DEBUG", "True") == "True"

# دامنه‌های مجاز - در Render باید دامنه render.com رو اضافه کنید
ALLOWED_HOSTS_ENV = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(",") if h.strip()]
if DEBUG or not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]  # فقط برای development

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",  # اپ اصلی پروژه ما
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # سرو static files در production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CSRF برای API endpointهایی که با @csrf_exempt مشخص نشدن فعاله
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
        "DIRS": [BASE_DIR / "templates"],  # فایل index.html مینی‌اپ اینجاست
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
# SQLite کافیه چون فقط دو نفریم و داده زیادی نداریم
# اگه خواستید بعداً به PostgreSQL مهاجرت کنید، فقط این بخش رو عوض کنید
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── Internationalization ──────────────────────────────────────────────────────
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ── Static Files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# whitenoise برای سرو static در production بدون nginx
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Bot Config (read-only در settings - استفاده در bot.py) ───────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# آیدی‌های تلگرام مجاز - از environment بخون
_allowed_raw = os.environ.get("ALLOWED_TG_IDS", "")
ALLOWED_TG_IDS = [
    int(i.strip()) for i in _allowed_raw.split(",") if i.strip().isdigit()
]
