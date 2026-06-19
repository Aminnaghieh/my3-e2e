"""
core/urls.py
============
تمام endpointهای API.

Pattern کلی:
  /api/           → لیست endpointها (برای debug)
  /api/dashboard/ → لود اولیه مینی‌اپ
  /api/notes/     → عملیات روی نوت‌ها
  /api/todos/     → عملیات روی To-Do
  /api/routines/  → عملیات روی روتین‌ها
  /api/vibe/      → آپدیت وایب
  /api/game/      → ثبت امتیاز بازی
  /api/leaderboard/ → لیدربورد
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

    # ── Game & Leaderboard ────────────────────────────────────────
    path("game/score/", views.submit_score, name="submit_score"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
]
