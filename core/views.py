"""
core/views.py
=============
All API endpoints for Phase 2.

Authentication:
  - Telegram initData validation
  - ALLOWED_TG_IDS enforcement
  - Non-Telegram requests get a minimal "Bot is Live" response

Features:
  - Dashboard with presence info
  - Notes with media upload (Cloudinary)
  - Routines with scheduled time + delete
  - Todos with scheduled date/time + call dates + delete
  - Presence tracking (online/offline)
  - AI chat (Gemini Flash)
  - Media cleanup
  - Keep-alive ping
"""

import json
import hashlib
import hmac
import os
import logging
from datetime import timedelta

import cloudinary
import cloudinary.uploader
import google.generativeai as genai

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings

from .models import (
    TelegramUser, DailyNote, Routine, RoutineLog,
    ToDoList, GameSession, PresenceLog, AIChatLog
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Cloudinary setup
# ─────────────────────────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

# Gemini setup
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Telegram initData validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.
    Returns parsed user dict if valid, None otherwise.
    """
    if not init_data:
        return None

    try:
        # Parse the init_data
        pairs = {}
        for pair in init_data.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                pairs[k] = v

        hash_value = pairs.pop("hash", None)
        if not hash_value:
            return None

        # Build check string
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

        # Compute HMAC
        secret_key = hmac.new(
            b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, check_string.encode(), hashlib.sha256
        ).hexdigest()

        if computed_hash != hash_value:
            return None

        # Parse user data
        user_data = pairs.get("user", "")
        if user_data:
            from urllib.parse import unquote
            user_obj = json.loads(unquote(user_data))
            return user_obj

        return None
    except Exception as e:
        logger.error(f"Init data validation error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Security helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_telegram_request(request) -> bool:
    """
    Detect if request comes from Telegram WebApp.
    Checks for:
      1. Telegram initData in headers
      2. Telegram-specific headers
    """
    # Check for initData in various places
    init_data = (
        request.headers.get("X-Telegram-Init-Data", "") or
        request.GET.get("init_data", "") or
        request.META.get("HTTP_X_TELEGRAM_INIT_DATA", "")
    )
    if init_data:
        user = validate_telegram_init_data(init_data)
        if user:
            return True

    # Check User-Agent for Telegram
    ua = request.META.get("HTTP_USER_AGENT", "")
    if "TelegramBot" in ua or "Telegram" in ua:
        return True

    # Check for tg_id from Telegram context
    tg_id = request.GET.get("tg_id") or request.POST.get("tg_id")
    if tg_id and str(tg_id).isdigit():
        tid = int(tg_id)
        if settings.ALLOWED_TG_IDS and tid in settings.ALLOWED_TG_IDS:
            return True

    return False


def is_allowed_user(tg_id: int) -> bool:
    """Check if the Telegram ID is in the allowed list."""
    if not settings.ALLOWED_TG_IDS:
        return True  # No restrictions if not configured
    return tg_id in settings.ALLOWED_TG_IDS


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_user(tg_id: int, first_name: str = "User", username: str = None) -> TelegramUser:
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=tg_id,
        defaults={"first_name": first_name, "username": username}
    )
    if not created:
        if user.first_name != first_name and first_name != "User":
            user.first_name = first_name
        if username and user.username != username:
            user.username = username
        user.save()
    return user


def parse_body(request) -> dict:
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body)
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


def json_response(data: dict, status: int = 200) -> JsonResponse:
    return JsonResponse(data, status=status)


def error_response(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": message}, status=status)


def require_tg_id(request_data: dict):
    raw = request_data.get("tg_id") or request_data.get("telegram_id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public status page (for non-Telegram visitors)
# ─────────────────────────────────────────────────────────────────────────────

def public_status(request):
    """Minimal response for non-Telegram visitors - just confirms bot is live."""
    return JsonResponse({
        "status": "live",
        "bot": "online",
        "message": "Bot is Live",
        "uptime_check": True,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Keep-alive ping
# ─────────────────────────────────────────────────────────────────────────────

def keep_alive_ping(request):
    """Endpoint for self-ping to prevent Render from sleeping."""
    return JsonResponse({"ok": True, "alive": True, "ts": timezone.now().isoformat()})


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def dashboard(request):
    """
    GET /api/dashboard/?tg_id=123&name=Ali
    Returns all app data in one shot.
    """
    tg_id = require_tg_id(request.GET)
    if not tg_id:
        return error_response("tg_id required", 401)

    if not is_allowed_user(tg_id):
        return error_response("Access denied", 403)

    first_name = request.GET.get("name", "User")
    username = request.GET.get("username")
    user = get_or_create_user(tg_id, first_name, username)

    # Mark user as online
    user.set_online()
    PresenceLog.objects.create(user=user, action="online")

    # Notes (shared between both users)
    notes = DailyNote.objects.select_related("author").order_by("-is_pinned", "-created_at")[:20]
    notes_data = [
        {
            "id": n.id,
            "text": n.text,
            "mood_tag": n.mood_tag,
            "author_name": n.author.first_name,
            "author_id": n.author.telegram_id,
            "is_mine": n.author.telegram_id == tg_id,
            "is_pinned": n.is_pinned,
            "media_type": n.media_type,
            "media_url": n.media_url,
            "media_thumbnail": n.media_thumbnail,
            "created_at": n.created_at.strftime("%H:%M - %d %b"),
        }
        for n in notes
    ]

    # Shared todos
    shared_todos = ToDoList.objects.filter(is_private=False).select_related("owner", "done_by")
    todos_data = [
        {
            "id": t.id,
            "title": t.title,
            "emoji": t.emoji,
            "is_done": t.is_done,
            "priority": t.priority,
            "owner_name": t.owner.first_name,
            "is_mine": t.owner.telegram_id == tg_id,
            "done_by": t.done_by.first_name if t.done_by else None,
            "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
            "scheduled_time": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else None,
            "is_call_date": t.is_call_date,
            "created_at": t.created_at.strftime("%H:%M - %d %b"),
        }
        for t in shared_todos
    ]

    # My private todos
    my_todos = ToDoList.objects.filter(owner=user, is_private=True)
    my_todos_data = [
        {
            "id": t.id,
            "title": t.title,
            "emoji": t.emoji,
            "is_done": t.is_done,
            "priority": t.priority,
            "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
            "scheduled_time": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else None,
            "is_call_date": t.is_call_date,
            "created_at": t.created_at.strftime("%H:%M - %d %b"),
        }
        for t in my_todos
    ]

    # Routines
    today = timezone.now().date()
    routines = Routine.objects.filter(owner=user, is_active=True)
    done_today_ids = set(
        RoutineLog.objects.filter(routine__in=routines, date=today)
        .values_list("routine_id", flat=True)
    )
    routines_data = [
        {
            "id": r.id,
            "title": r.title,
            "emoji": r.emoji,
            "frequency": r.frequency,
            "scheduled_time": r.scheduled_time.strftime("%H:%M") if r.scheduled_time else None,
            "done_today": r.id in done_today_ids,
        }
        for r in routines
    ]

    # Leaderboard
    leaderboard = list(
        TelegramUser.objects.values(
            "telegram_id", "first_name", "vibe_emoji", "total_points"
        ).order_by("-total_points")
    )

    # Partner info with presence
    other_users = TelegramUser.objects.exclude(telegram_id=tg_id)
    partner_data = None
    if other_users.exists():
        partner = other_users.first()
        partner_data = {
            "name": partner.first_name,
            "vibe_emoji": partner.vibe_emoji,
            "vibe_label": partner.vibe_label,
            "vibe_is_today": partner.vibe_is_today,
            "points": partner.total_points,
            "is_online": partner.is_online,
            "last_seen": partner.last_seen.strftime("%H:%M - %d %b"),
        }

    return json_response({
        "ok": True,
        "user": {
            "id": user.telegram_id,
            "name": user.first_name,
            "vibe_emoji": user.vibe_emoji,
            "vibe_label": user.vibe_label,
            "vibe_is_today": user.vibe_is_today,
            "points": user.total_points,
            "is_online": user.is_online,
        },
        "partner": partner_data,
        "notes": notes_data,
        "shared_todos": todos_data,
        "my_todos": my_todos_data,
        "routines": routines_data,
        "leaderboard": leaderboard,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Presence
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def set_offline(request):
    """Mark user as offline when they leave the mini-app."""
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    try:
        user = TelegramUser.objects.get(telegram_id=tg_id)
        user.set_offline()
        PresenceLog.objects.create(user=user, action="offline")
        return json_response({"ok": True})
    except TelegramUser.DoesNotExist:
        return error_response("User not found", 404)


@require_http_methods(["GET"])
def presence_status(request):
    """Get online status of both users."""
    users = TelegramUser.objects.all()
    result = [
        {
            "telegram_id": u.telegram_id,
            "name": u.first_name,
            "is_online": u.is_online,
            "last_seen": u.last_seen.isoformat(),
        }
        for u in users
    ]
    return json_response({"ok": True, "users": result})


# ─────────────────────────────────────────────────────────────────────────────
# Daily Notes (with media)
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def add_note(request):
    """
    POST /api/notes/add/
    Body (multipart/form-data for media, JSON for text-only):
      - tg_id, name, text, mood_tag
      - media_file (optional: image/video/audio)
      - media_type (optional: image/video/audio/gif/sticker)
    """
    # Handle multipart (media upload) vs JSON (text-only)
    content_type = request.content_type or ""
    if "multipart" in content_type:
        data = request.POST.dict()
        media_file = request.FILES.get("media_file")
    else:
        data = parse_body(request)
        media_file = None

    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    if not is_allowed_user(tg_id):
        return error_response("Access denied", 403)

    text = data.get("text", "").strip()
    mood_tag = data.get("mood_tag", "")
    media_type = data.get("media_type", "none")

    # Must have either text or media
    if not text and not media_file:
        return error_response("Note must have text or media")

    user = get_or_create_user(tg_id, data.get("name", "User"))

    note = DailyNote.objects.create(
        author=user,
        text=text,
        mood_tag=mood_tag,
        media_type="none",
    )

    # Upload media to Cloudinary if provided
    if media_file:
        try:
            resource_type = "auto"
            if media_type == "image" or media_file.content_type and media_file.content_type.startswith("image"):
                resource_type = "image"
            elif media_type == "video" or media_file.content_type and media_file.content_type.startswith("video"):
                resource_type = "video"
            elif media_type == "audio" or media_file.content_type and media_file.content_type.startswith("audio"):
                resource_type = "raw"  # Cloudinary uses 'raw' for audio

            # Upload with a folder and unique public_id
            public_id = f"notes/{user.telegram_id}/{timezone.now().strftime('%Y%m%d_%H%M%S')}_{note.id}"
            result = cloudinary.uploader.upload(
                media_file,
                public_id=public_id,
                resource_type=resource_type,
                folder="miniapp-notes",
            )

            note.media_url = result.get("secure_url", "")
            note.media_public_id = result.get("public_id", "")

            # Determine actual media type from upload
            if resource_type == "image":
                if media_type == "gif" or media_file.name and media_file.name.lower().endswith(".gif"):
                    note.media_type = "gif"
                else:
                    note.media_type = "image"
                note.media_thumbnail = result.get("secure_url", "")
            elif resource_type == "video":
                note.media_type = "video"
                # Get thumbnail from Cloudinary
                note.media_thumbnail = result.get("secure_url", "").replace(
                    "/video/", "/video/", 1
                ).replace(".mp4", ".jpg") if result.get("secure_url") else ""
            elif resource_type == "raw":
                note.media_type = "audio"
            else:
                note.media_type = media_type if media_type != "none" else "image"

            note.save()

        except Exception as e:
            logger.error(f"Cloudinary upload error: {e}")
            # Save note without media if upload fails
            note.media_type = "none"

    return json_response({
        "ok": True,
        "note": {
            "id": note.id,
            "text": note.text,
            "mood_tag": note.mood_tag,
            "media_type": note.media_type,
            "media_url": note.media_url,
            "media_thumbnail": note.media_thumbnail,
            "author_name": user.first_name,
            "created_at": note.created_at.strftime("%H:%M"),
        }
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_note(request, note_id: int):
    """Delete a note. Only the author can delete their own notes."""
    tg_id = require_tg_id(request.GET)
    if not tg_id:
        return error_response("tg_id required", 401)

    try:
        note = DailyNote.objects.get(id=note_id)
    except DailyNote.DoesNotExist:
        return error_response("Note not found", 404)

    if note.author.telegram_id != tg_id:
        return error_response("Only the author can delete", 403)

    # Delete media from Cloudinary
    if note.media_public_id:
        try:
            cloudinary.uploader.destroy(note.media_public_id, resource_type="auto")
        except Exception as e:
            logger.error(f"Cloudinary delete error: {e}")

    note.delete()
    return json_response({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Vibe
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def update_vibe(request):
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    emoji = data.get("emoji", "").strip()
    label = data.get("label", "").strip()
    if not emoji:
        return error_response("Emoji is required")

    user = get_or_create_user(tg_id, data.get("name", "User"))
    user.vibe_emoji = emoji
    user.vibe_label = label or "No vibe"
    user.vibe_updated_at = timezone.now()
    user.save(update_fields=["vibe_emoji", "vibe_label", "vibe_updated_at"])

    return json_response({
        "ok": True,
        "vibe": {"emoji": user.vibe_emoji, "label": user.vibe_label}
    })


# ─────────────────────────────────────────────────────────────────────────────
# To-Do (with scheduling, call dates, delete)
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def add_todo(request):
    """
    POST /api/todos/add/
    Body: { tg_id, name, title, emoji?, priority?, is_private?,
            scheduled_date?, scheduled_time?, is_call_date? }
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    if not is_allowed_user(tg_id):
        return error_response("Access denied", 403)

    title = data.get("title", "").strip()
    if not title:
        return error_response("Title is required")

    user = get_or_create_user(tg_id, data.get("name", "User"))

    # Parse scheduled date/time
    scheduled_date = None
    scheduled_time = None
    is_call_date = data.get("is_call_date", False)

    sd = data.get("scheduled_date", "")
    if sd:
        try:
            from datetime import datetime
            scheduled_date = datetime.strptime(sd, "%Y-%m-%d").date()
        except ValueError:
            pass

    st = data.get("scheduled_time", "")
    if st:
        try:
            from datetime import datetime
            scheduled_time = datetime.strptime(st, "%H:%M").time()
        except ValueError:
            try:
                from datetime import datetime
                scheduled_time = datetime.strptime(st, "%H:%M:%S").time()
            except ValueError:
                pass

    todo = ToDoList.objects.create(
        owner=user,
        title=title,
        emoji=data.get("emoji", ""),
        priority=int(data.get("priority", 1)),
        is_private=data.get("is_private", False),
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        is_call_date=bool(is_call_date),
    )

    return json_response({
        "ok": True,
        "todo": {
            "id": todo.id,
            "title": todo.title,
            "is_done": False,
            "scheduled_date": todo.scheduled_date.isoformat() if todo.scheduled_date else None,
            "scheduled_time": todo.scheduled_time.strftime("%H:%M") if todo.scheduled_time else None,
            "is_call_date": todo.is_call_date,
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def toggle_todo(request, todo_id: int):
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    try:
        todo = ToDoList.objects.get(id=todo_id)
    except ToDoList.DoesNotExist:
        return error_response("Item not found", 404)

    user = get_or_create_user(tg_id, data.get("name", "User"))

    if todo.is_done:
        todo.is_done = False
        todo.done_by = None
        todo.done_at = None
        todo.save(update_fields=["is_done", "done_by", "done_at"])
    else:
        todo.mark_done(user)

    return json_response({
        "ok": True,
        "is_done": todo.is_done,
        "done_by": todo.done_by.first_name if todo.done_by else None,
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_todo(request, todo_id: int):
    """Delete a todo item. Only the owner can delete."""
    tg_id = require_tg_id(request.GET)
    if not tg_id:
        return error_response("tg_id required", 401)

    try:
        todo = ToDoList.objects.get(id=todo_id)
    except ToDoList.DoesNotExist:
        return error_response("Item not found", 404)

    if todo.owner.telegram_id != tg_id:
        return error_response("Only the owner can delete", 403)

    todo.delete()
    return json_response({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Routines (with scheduled time + delete)
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def add_routine(request):
    """
    POST /api/routines/add/
    Body: { tg_id, name, title, emoji?, frequency?, scheduled_time? }
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    if not is_allowed_user(tg_id):
        return error_response("Access denied", 403)

    title = data.get("title", "").strip()
    if not title:
        return error_response("Title is required")

    user = get_or_create_user(tg_id, data.get("name", "User"))

    # Parse scheduled time
    scheduled_time = None
    st = data.get("scheduled_time", "")
    if st:
        try:
            from datetime import datetime
            scheduled_time = datetime.strptime(st, "%H:%M").time()
        except ValueError:
            pass

    routine = Routine.objects.create(
        owner=user,
        title=title,
        emoji=data.get("emoji", "⚡"),
        frequency=data.get("frequency", "daily"),
        scheduled_time=scheduled_time,
    )

    return json_response({
        "ok": True,
        "routine": {
            "id": routine.id,
            "title": routine.title,
            "emoji": routine.emoji,
            "scheduled_time": routine.scheduled_time.strftime("%H:%M") if routine.scheduled_time else None,
            "done_today": False,
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_routine(request, routine_id: int):
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    try:
        routine = Routine.objects.get(id=routine_id, owner__telegram_id=tg_id)
    except Routine.DoesNotExist:
        return error_response("Routine not found", 404)

    today = timezone.now().date()
    log, created = RoutineLog.objects.get_or_create(routine=routine, date=today)

    if not created:
        log.delete()
        return json_response({"ok": True, "done_today": False})

    return json_response({"ok": True, "done_today": True})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_routine(request, routine_id: int):
    """Delete a routine. Only the owner can delete."""
    tg_id = require_tg_id(request.GET)
    if not tg_id:
        return error_response("tg_id required", 401)

    try:
        routine = Routine.objects.get(id=routine_id)
    except Routine.DoesNotExist:
        return error_response("Routine not found", 404)

    if routine.owner.telegram_id != tg_id:
        return error_response("Only the owner can delete", 403)

    # Soft delete
    routine.is_active = False
    routine.save(update_fields=["is_active"])
    return json_response({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Game
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def submit_score(request):
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    game_type = data.get("game_type", "tap_battle")
    score = int(data.get("score", 0))

    if score < 0 or score > 99999:
        return error_response("Invalid score")

    user = get_or_create_user(tg_id, data.get("name", "User"))

    GameSession.objects.create(
        player=user,
        game_type=game_type,
        score=score,
        duration_sec=int(data.get("duration_sec", 0)),
    )

    user.total_points += score
    user.save(update_fields=["total_points"])

    leaderboard = list(
        TelegramUser.objects.values("first_name", "vibe_emoji", "total_points")
        .order_by("-total_points")
    )

    return json_response({
        "ok": True,
        "new_total": user.total_points,
        "leaderboard": leaderboard,
    })


@require_http_methods(["GET"])
def leaderboard_view(request):
    users = TelegramUser.objects.order_by("-total_points")
    result = []
    for u in users:
        best_scores = {}
        for game_type, _ in GameSession.GAME_TYPES:
            best = GameSession.objects.filter(
                player=u, game_type=game_type
            ).order_by("-score").first()
            if best:
                best_scores[game_type] = best.score

        result.append({
            "name": u.first_name,
            "vibe_emoji": u.vibe_emoji,
            "total_points": u.total_points,
            "best_scores": best_scores,
        })

    return json_response({"ok": True, "leaderboard": result})


# ─────────────────────────────────────────────────────────────────────────────
# AI Chat (Gemini Flash)
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def ai_chat(request):
    """
    POST /api/ai/chat/
    Body: { tg_id, message }
    Sends message to Gemini Flash and returns response.
    Maintains conversation history per user.
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id required", 401)

    if not is_allowed_user(tg_id):
        return error_response("Access denied", 403)

    if not settings.GEMINI_API_KEY:
        return error_response("AI assistant not configured", 503)

    message = data.get("message", "").strip()
    if not message:
        return error_response("Message is required")

    user = get_or_create_user(tg_id, data.get("name", "User"))

    # Save user message
    AIChatLog.objects.create(user=user, role="user", content=message)

    # Build conversation context (last 20 messages)
    recent = AIChatLog.objects.filter(user=user).order_by("-created_at")[:20]
    history = list(reversed(list(recent)))

    try:
        model = genai.GenerativeModel("gemini-3.5-flash")

        # Build conversation
        chat_history = []
        for msg in history[:-1]:  # Exclude current message
            chat_history.append({
                "role": "model" if msg.role == "assistant" else "user",
                "parts": [msg.content]
            })

        chat = model.start_chat(history=chat_history)
        response = chat.send_message(message)

        ai_response = response.text

        # Save AI response
        AIChatLog.objects.create(user=user, role="assistant", content=ai_response)

        return json_response({
            "ok": True,
            "response": ai_response,
        })

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return error_response(f"AI error: {str(e)}", 500)


# ─────────────────────────────────────────────────────────────────────────────
# Media Cleanup
# ─────────────────────────────────────────────────────────────────────────────

def cleanup_old_media(request=None):
    """
    Delete media files older than MEDIA_RETENTION_DAYS from Cloudinary.
    Note text is preserved, only media is removed.
    Called by scheduler.
    """
    cutoff = timezone.now() - timedelta(days=settings.MEDIA_RETENTION_DAYS)
    old_notes = DailyNote.objects.filter(
        created_at__lt=cutoff,
        media_type__in=["image", "video", "audio", "gif"]
    )

    cleaned = 0
    for note in old_notes:
        if note.media_public_id:
            try:
                cloudinary.uploader.destroy(note.media_public_id, resource_type="auto")
            except Exception as e:
                logger.error(f"Cleanup error for {note.media_public_id}: {e}")

        note.media_url = ""
        note.media_public_id = ""
        note.media_thumbnail = ""
        note.media_type = "none"
        note.save(update_fields=["media_url", "media_public_id", "media_thumbnail", "media_type"])
        cleaned += 1

    logger.info(f"Media cleanup: removed {cleaned} files")
    if request is not None:
        return json_response({"ok": True, "cleaned": cleaned})
