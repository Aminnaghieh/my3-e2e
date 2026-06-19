"""
core/admin.py
=============
ثبت مدل‌ها در پنل ادمین Django.

پنل ادمین در آدرس /admin-panel/ در دسترسه.
از اینجا می‌تونید:
  - کاربران رو ببینید و آیدی تلگرامشون رو اضافه کنید
  - نوت‌ها و To-Doها رو مدیریت کنید
  - امتیازات بازی رو ببینید
"""

from django.contrib import admin
from .models import TelegramUser, DailyNote, Routine, RoutineLog, ToDoList, GameSession


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["first_name", "telegram_id", "vibe_emoji", "total_points", "created_at"]
    search_fields = ["first_name", "telegram_id", "username"]


@admin.register(DailyNote)
class DailyNoteAdmin(admin.ModelAdmin):
    list_display = ["author", "text_preview", "mood_tag", "is_pinned", "created_at"]
    list_filter = ["is_pinned", "author"]

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = "متن"


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ["emoji", "title", "owner", "frequency", "is_active"]
    list_filter = ["is_active", "frequency", "owner"]


@admin.register(RoutineLog)
class RoutineLogAdmin(admin.ModelAdmin):
    list_display = ["routine", "date", "done_at"]
    list_filter = ["date"]


@admin.register(ToDoList)
class ToDoListAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "is_done", "priority", "is_private", "done_by"]
    list_filter = ["is_done", "is_private", "priority"]


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ["player", "game_type", "score", "duration_sec", "played_at"]
    list_filter = ["game_type", "player"]
    ordering = ["-played_at"]
