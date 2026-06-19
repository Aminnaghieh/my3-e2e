"""
app/urls.py
===========
URL routing اصلی.

  /          → مینی‌اپ (index.html)
  /api/...   → تمام API endpointها
  /admin/    → پنل ادمین Django (برای مدیریت دیتا)
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # ── مینی‌اپ ───────────────────────────────────────────────────
    # وقتی مینی‌اپ باز میشه این صفحه رو لود می‌کنه
    path("", TemplateView.as_view(template_name="index.html"), name="miniapp"),

    # ── API ───────────────────────────────────────────────────────
    path("api/", include("core.urls")),

    # ── Django Admin ──────────────────────────────────────────────
    # آدرس ادمین: /admin-panel/ (امن‌تر از /admin/)
    path("admin-panel/", admin.site.urls),
]
