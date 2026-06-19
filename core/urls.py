"""
core/urls.py
============
All API endpoint patterns.

Phase 2 additions:
  - Presence tracking
  - AI chat
  - Routine delete
  - Keep-alive
  - Media cleanup
  - Public status
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Dashboard ─────────────────────────────────────────────────
    path("dashboard/", views.dashboard, name="dashboard"),

    # ── Daily Notes ───────────────────────────────────────────────
    path("notes/add/", views.add_note, name="add_note"),
    path("notes/<int:note_id>/delete/", views.delete_note, name="delete_note"),

    # ── Vibe Moodring ─────────────────────────────────────────────
    path("vibe/update/", views.update_vibe, name="update_vibe"),

    # ── To-Do ─────────────────────────────────────────────────────
    path("todos/add/", views.add_todo, name="add_todo"),
    path("todos/<int:todo_id>/toggle/", views.toggle_todo, name="toggle_todo"),
    path("todos/<int:todo_id>/delete/", views.delete_todo, name="delete_todo"),

    # ── Routines ──────────────────────────────────────────────────
    path("routines/add/", views.add_routine, name="add_routine"),
    path("routines/<int:routine_id>/check/", views.check_routine, name="check_routine"),
    path("routines/<int:routine_id>/delete/", views.delete_routine, name="delete_routine"),

    # ── Game & Leaderboard ────────────────────────────────────────
    path("game/score/", views.submit_score, name="submit_score"),
    path("leaderboard/", views.leaderboard_view, name="leaderboard"),

    # ── Presence ──────────────────────────────────────────────────
    path("presence/offline/", views.set_offline, name="set_offline"),
    path("presence/status/", views.presence_status, name="presence_status"),

    # ── AI Chat ───────────────────────────────────────────────────
    path("ai/chat/", views.ai_chat, name="ai_chat"),

    # ── System ────────────────────────────────────────────────────
    path("keep-alive/", views.keep_alive_ping, name="keep_alive"),
    path("status/", views.public_status, name="public_status"),
    path("media/cleanup/", views.cleanup_old_media, name="media_cleanup"),
]
