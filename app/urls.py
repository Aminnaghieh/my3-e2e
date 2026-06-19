"""
app/urls.py
===========
Main URL routing.

Security: Non-Telegram requests to the mini-app root get
redirected to the public status page instead.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from core.views import public_status


def miniapp_gate(request):
    """
    Gate for the mini-app root URL.
    If request comes from Telegram → serve the app.
    If from a browser/public → redirect to status page.
    """
    from core.views import is_telegram_request

    if is_telegram_request(request):
        # Serve the full mini-app
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        html = render_to_string("index.html")
        return HttpResponse(html)
    else:
        # Show minimal "Bot is Live" page
        return public_status(request)


urlpatterns = [
    # ── Mini App (with security gate) ─────────────────────────────
    path("", miniapp_gate, name="miniapp"),

    # ── API ───────────────────────────────────────────────────────
    path("api/", include("core.urls")),

    # ── Django Admin ──────────────────────────────────────────────
    path("admin-panel/", admin.site.urls),
]
