"""
app/urls.py
===========
Main URL routing.

Security is handled client-side:
  - If running inside Telegram (mobile/desktop) → app loads
  - If opened in a regular browser → shows "Bot is Live"
  - API endpoints enforce ALLOWED_TG_IDS server-side
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # ── Mini App (always served; JS checks Telegram context) ─────
    path("", TemplateView.as_view(template_name="index.html"), name="miniapp"),

    # ── API ───────────────────────────────────────────────────────
    path("api/", include("core.urls")),

    # ── Django Admin ──────────────────────────────────────────────
    path("admin-panel/", admin.site.urls),
]
