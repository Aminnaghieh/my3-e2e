"""
core/models.py
==============
All database models for the Phase 2 mini-app.

Features:
  - TelegramUser with presence tracking
  - DailyNote with media attachment support
  - Routine with scheduled time
  - ToDoList with scheduled date/time + call_date flag
  - RoutineLog
  - GameSession
  - PresenceLog (online/offline tracking)
  - AIChatLog (conversation history)
"""

import os
from django.db import models
from django.utils import timezone


class TelegramUser(models.Model):
    """
    Telegram user profile.

    Fields:
        telegram_id:   Unique Telegram user ID
        username:      Telegram username (optional)
        first_name:    Display name from Telegram
        vibe_emoji:    Daily mood emoji
        vibe_label:    Mood description
        vibe_updated_at: When vibe was last set
        total_points:  Cumulative game score
        is_online:     Current online status
        last_seen:     Last activity timestamp
        created_at:    Registration date
    """
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=100, default="User")

    # Vibe
    vibe_emoji = models.CharField(max_length=10, default="✨")
    vibe_label = models.CharField(max_length=50, default="No vibe")
    vibe_updated_at = models.DateTimeField(default=timezone.now)

    # Points
    total_points = models.IntegerField(default=0)

    # Presence
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} (TG:{self.telegram_id}) {self.vibe_emoji}"

    @property
    def vibe_is_today(self):
        return self.vibe_updated_at.date() == timezone.now().date()

    def set_online(self):
        self.is_online = True
        self.last_seen = timezone.now()
        self.save(update_fields=["is_online", "last_seen"])

    def set_offline(self):
        self.is_online = False
        self.last_seen = timezone.now()
        self.save(update_fields=["is_online", "last_seen"])


class PresenceLog(models.Model):
    """
    Log of user online/offline events.
    Used to track when users visit the bot.
    """
    ACTION_CHOICES = [
        ("online", "Online"),
        ("offline", "Offline"),
    ]

    user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, related_name="presence_logs"
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.first_name} {self.action} at {self.timestamp}"


class DailyNote(models.Model):
    """
    Daily notes with media attachment support.

    Fields:
        author:          Who wrote it
        text:            Note content
        mood_tag:        Emotional tag emoji
        is_pinned:       Pinned status
        media_type:      Type of attached media (image/video/audio/gif/sticker/none)
        media_url:       Cloudinary URL for the media
        media_public_id: Cloudinary public ID (for deletion)
        media_thumbnail: Thumbnail URL (for video/image)
        created_at:      Timestamp
    """
    MEDIA_TYPE_CHOICES = [
        ("none", "No Media"),
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("gif", "GIF"),
        ("sticker", "Sticker"),
    ]

    author = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, related_name="notes"
    )
    text = models.TextField(blank=True, default="")
    mood_tag = models.CharField(max_length=10, blank=True, default="")
    is_pinned = models.BooleanField(default=False)

    # Media
    media_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, default="none"
    )
    media_url = models.URLField(blank=True, default="")
    media_public_id = models.CharField(max_length=300, blank=True, default="")
    media_thumbnail = models.URLField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        preview = self.text[:40] + "..." if len(self.text) > 40 else self.text
        media = f" [{self.media_type}]" if self.media_type != "none" else ""
        return f"[{self.author.first_name}] {preview}{media}"


class Routine(models.Model):
    """
    Daily routines with scheduled time.

    Fields:
        owner:       Owner of the routine
        title:       Title (e.g., "Morning workout")
        emoji:       Visual emoji
        frequency:   daily / weekly
        is_active:   Soft delete flag
        scheduled_time: Time of day to perform (optional)
        created_at:  Creation date
    """
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
    ]

    owner = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, related_name="routines"
    )
    title = models.CharField(max_length=200)
    emoji = models.CharField(max_length=10, default="⚡")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default="daily")
    is_active = models.BooleanField(default=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        time_str = f" @ {self.scheduled_time.strftime('%H:%M')}" if self.scheduled_time else ""
        return f"{self.emoji} {self.title}{time_str} ({self.owner.first_name})"


class RoutineLog(models.Model):
    """
    Routine completion log.

    Unique constraint on (routine, date) prevents duplicate check-ins.
    """
    routine = models.ForeignKey(
        Routine, on_delete=models.CASCADE, related_name="logs"
    )
    date = models.DateField(default=timezone.now)
    done_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("routine", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.routine.title} done {self.date}"


class ToDoList(models.Model):
    """
    To-Do items with scheduling and call date support.

    Fields:
        owner:          Who created it
        title:          Item title
        emoji:          Optional emoji
        is_done:        Completion status
        is_private:     Private vs shared
        priority:       1=low, 2=medium, 3=high
        scheduled_date: Date when this task is due (optional)
        scheduled_time: Time when this task is due (optional)
        is_call_date:   If True, this is a call/meeting with reminder
        done_by:        Who marked it done
        done_at:        When it was marked done
        created_at:     Creation timestamp
    """
    PRIORITY_CHOICES = [
        (1, "Low"),
        (2, "Medium"),
        (3, "High"),
    ]

    owner = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, related_name="todos"
    )
    title = models.CharField(max_length=300)
    emoji = models.CharField(max_length=10, blank=True, default="")
    is_done = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)

    # Scheduling
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    is_call_date = models.BooleanField(default=False)

    done_by = models.ForeignKey(
        TelegramUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="completed_todos"
    )
    done_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_done", "-priority", "-created_at"]

    def mark_done(self, user: TelegramUser):
        self.is_done = True
        self.done_by = user
        self.done_at = timezone.now()
        self.save()

    def __str__(self):
        status = "done" if self.is_done else "pending"
        call = " [CALL]" if self.is_call_date else ""
        return f"{status} {self.emoji} {self.title}{call}"


class GameSession(models.Model):
    """
    Game session record.
    """
    GAME_TYPES = [
        ("tap_battle", "Tap Battle"),
        ("memory", "Memory Game"),
        ("reaction", "Reaction Test"),
    ]

    player = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, related_name="game_sessions"
    )
    game_type = models.CharField(max_length=20, choices=GAME_TYPES)
    score = models.IntegerField(default=0)
    duration_sec = models.IntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-played_at"]

    def __str__(self):
        return f"{self.player.first_name} | {self.get_game_type_display()} | {self.score}pt"


class AIChatLog(models.Model):
    """
    Conversation log for the AI assistant.
    """
    user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE, related_name="ai_chats"
    )
    role = models.CharField(max_length=10)  # "user" or "assistant"
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
