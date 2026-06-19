"""
core/admin.py
=============
Django admin panel registration.
Access at /admin-panel/
"""

from django.contrib import admin
from .models import (
    TelegramUser, DailyNote, Routine, RoutineLog,
    ToDoList, GameSession, PresenceLog, AIChatLog
)


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["first_name", "telegram_id", "vibe_emoji", "total_points", "is_online", "last_seen", "created_at"]
    search_fields = ["first_name", "telegram_id", "username"]
    list_filter = ["is_online"]


@admin.register(DailyNote)
class DailyNoteAdmin(admin.ModelAdmin):
    list_display = ["author", "text_preview", "mood_tag", "media_type", "is_pinned", "created_at"]
    list_filter = ["is_pinned", "author", "media_type"]

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Text"


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = ["emoji", "title", "owner", "frequency", "scheduled_time", "is_active"]
    list_filter = ["is_active", "frequency", "owner"]


@admin.register(RoutineLog)
class RoutineLogAdmin(admin.ModelAdmin):
    list_display = ["routine", "date", "done_at"]
    list_filter = ["date"]


@admin.register(ToDoList)
class ToDoListAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "is_done", "priority", "scheduled_date", "scheduled_time", "is_call_date", "is_private"]
    list_filter = ["is_done", "is_private", "priority", "is_call_date"]


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ["player", "game_type", "score", "duration_sec", "played_at"]
    list_filter = ["game_type", "player"]
    ordering = ["-played_at"]


@admin.register(PresenceLog)
class PresenceLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "timestamp"]
    list_filter = ["action"]


@admin.register(AIChatLog)
class AIChatLogAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "content_preview", "created_at"]
    list_filter = ["role"]

    def content_preview(self, obj):
        return obj.content[:60] + "..." if len(obj.content) > 60 else obj.content
    content_preview.short_description = "Content"
