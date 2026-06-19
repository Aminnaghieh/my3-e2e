"""
core/views.py
=============
تمام API endpointها اینجان.

هر view یه کار مشخص داره و بیشتر از یه مسئولیت نداره.
برای احراز هویت از initData تلگرام استفاده می‌کنیم:
  - در production باید هش HMAC رو validate کنید (تابع validate_init_data)
  - در development ساده‌ترین حالت رو داریم که فقط tg_id رو می‌گیره

جریان کلی request:
  1. Client مینی‌اپ tg_id رو از Telegram.WebApp.initDataUnsafe.user.id می‌گیره
  2. هر request این آیدی رو در header یا body ارسال می‌کنه
  3. ما کاربر رو پیدا (یا می‌سازیم) و عملیات رو انجام می‌دیم
  4. پاسخ JSON برمی‌گردونیم
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import TelegramUser, DailyNote, Routine, RoutineLog, ToDoList, GameSession


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_user(tg_id: int, first_name: str = "کاربر", username: str = None) -> TelegramUser:
    """
    کاربر رو بر اساس telegram_id پیدا می‌کنه یا می‌سازه.
    اگه اسم جدید داشت آپدیت می‌کنه (اسم تلگرام ممکنه عوض بشه).
    """
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=tg_id,
        defaults={"first_name": first_name, "username": username}
    )
    if not created and user.first_name != first_name:
        # اسم کاربر در تلگرام عوض شده، sync کنیم
        user.first_name = first_name
        user.save(update_fields=["first_name"])
    return user


def parse_body(request) -> dict:
    """
    Body یه POST request رو parse می‌کنه.
    اگه content-type=application/json بود JSON می‌خونه،
    وگرنه form data.
    """
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body)
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


def json_response(data: dict, status: int = 200) -> JsonResponse:
    """Wrapper کوتاه برای JsonResponse با ساختار ثابت."""
    return JsonResponse(data, status=status)


def error_response(message: str, status: int = 400) -> JsonResponse:
    """Response خطا با فرمت ثابت."""
    return JsonResponse({"ok": False, "error": message}, status=status)


def require_tg_id(request_data: dict):
    """
    tg_id رو از دیکشنری می‌گیره.
    اگه نبود یا invalid بود None برمی‌گردونه.
    """
    raw = request_data.get("tg_id") or request_data.get("telegram_id")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard - لود اولیه
# ─────────────────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def dashboard(request):
    """
    GET /api/dashboard/?tg_id=123&name=علی
    ---
    اولین چیزیه که مینی‌اپ بعد از لود صدا می‌زنه.
    همه داده‌های لازم رو یکجا برمی‌گردونه تا roundtrip کم باشه:
      - اطلاعات خود کاربر و طرف مقابل
      - آخرین ۱۰ نوت مشترک
      - لیست To-Do مشترک
      - روتین‌های امروز کاربر
      - لیدربورد (امتیازها)
    """
    tg_id = require_tg_id(request.GET)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    first_name = request.GET.get("name", "کاربر")
    username = request.GET.get("username")
    user = get_or_create_user(tg_id, first_name, username)

    # ── نوت‌های مشترک (از هر دو نفر) ────────────────────────────
    notes = DailyNote.objects.select_related("author").order_by("-is_pinned", "-created_at")[:15]
    notes_data = [
        {
            "id": n.id,
            "text": n.text,
            "mood_tag": n.mood_tag,
            "author_name": n.author.first_name,
            "author_id": n.author.telegram_id,
            "is_mine": n.author.telegram_id == tg_id,
            "is_pinned": n.is_pinned,
            # فرمت نسبی: "همین الان" / "دیروز" / تاریخ
            "created_at": n.created_at.strftime("%H:%M - %d %b"),
        }
        for n in notes
    ]

    # ── To-Do مشترک (is_private=False) ───────────────────────────
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
        }
        for t in shared_todos
    ]

    # ── To-Do شخصی همین کاربر ────────────────────────────────────
    my_todos = ToDoList.objects.filter(owner=user, is_private=True)
    my_todos_data = [
        {
            "id": t.id,
            "title": t.title,
            "emoji": t.emoji,
            "is_done": t.is_done,
            "priority": t.priority,
        }
        for t in my_todos
    ]

    # ── روتین‌های امروز ───────────────────────────────────────────
    today = timezone.now().date()
    routines = Routine.objects.filter(owner=user, is_active=True)
    done_today_ids = set(
        RoutineLog.objects.filter(
            routine__in=routines, date=today
        ).values_list("routine_id", flat=True)
    )
    routines_data = [
        {
            "id": r.id,
            "title": r.title,
            "emoji": r.emoji,
            "frequency": r.frequency,
            "done_today": r.id in done_today_ids,
        }
        for r in routines
    ]

    # ── لیدربورد ──────────────────────────────────────────────────
    leaderboard = list(
        TelegramUser.objects.values("telegram_id", "first_name", "vibe_emoji", "total_points")
        .order_by("-total_points")
    )

    # ── وایب طرف مقابل ───────────────────────────────────────────
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
        },
        "partner": partner_data,
        "notes": notes_data,
        "shared_todos": todos_data,
        "my_todos": my_todos_data,
        "routines": routines_data,
        "leaderboard": leaderboard,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Daily Notes
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def add_note(request):
    """
    POST /api/notes/add/
    Body: { tg_id, name, text, mood_tag? }
    ---
    یه نوت جدید ثبت می‌کنه.
    mood_tag اختیاریه (مثلاً "😊" یا "🔥").
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    text = data.get("text", "").strip()
    if not text:
        return error_response("متن نوت نمی‌تونه خالی باشه")

    user = get_or_create_user(tg_id, data.get("name", "کاربر"))
    note = DailyNote.objects.create(
        author=user,
        text=text,
        mood_tag=data.get("mood_tag", ""),
    )

    return json_response({
        "ok": True,
        "note": {
            "id": note.id,
            "text": note.text,
            "mood_tag": note.mood_tag,
            "author_name": user.first_name,
            "created_at": note.created_at.strftime("%H:%M"),
        }
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_note(request, note_id: int):
    """
    DELETE /api/notes/<note_id>/
    Header یا Query: tg_id
    ---
    فقط نویسنده‌ی نوت می‌تونه حذفش کنه.
    """
    tg_id = require_tg_id(request.GET)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    try:
        note = DailyNote.objects.get(id=note_id)
    except DailyNote.DoesNotExist:
        return error_response("نوت پیدا نشد", 404)

    if note.author.telegram_id != tg_id:
        return error_response("فقط نویسنده می‌تونه حذف کنه", 403)

    note.delete()
    return json_response({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Vibe Moodring
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def update_vibe(request):
    """
    POST /api/vibe/update/
    Body: { tg_id, name, emoji, label }
    ---
    وایب کاربر رو آپدیت می‌کنه.
    طرف مقابل دفعه بعد که لود می‌کنه وایب جدید رو می‌بینه.
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    emoji = data.get("emoji", "").strip()
    label = data.get("label", "").strip()
    if not emoji:
        return error_response("ایموجی الزامی است")

    user = get_or_create_user(tg_id, data.get("name", "کاربر"))
    user.vibe_emoji = emoji
    user.vibe_label = label or "بدون وایب"
    user.vibe_updated_at = timezone.now()
    user.save(update_fields=["vibe_emoji", "vibe_label", "vibe_updated_at"])

    return json_response({
        "ok": True,
        "vibe": {"emoji": user.vibe_emoji, "label": user.vibe_label}
    })


# ─────────────────────────────────────────────────────────────────────────────
# To-Do List
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def add_todo(request):
    """
    POST /api/todos/add/
    Body: { tg_id, name, title, emoji?, priority?, is_private? }
    ---
    یه آیتم To-Do جدید اضافه می‌کنه.
    is_private=false یعنی مشترکه و هر دو می‌بینن.
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    title = data.get("title", "").strip()
    if not title:
        return error_response("عنوان نمی‌تونه خالی باشه")

    user = get_or_create_user(tg_id, data.get("name", "کاربر"))
    todo = ToDoList.objects.create(
        owner=user,
        title=title,
        emoji=data.get("emoji", ""),
        priority=int(data.get("priority", 1)),
        is_private=data.get("is_private", False),
    )

    return json_response({
        "ok": True,
        "todo": {"id": todo.id, "title": todo.title, "is_done": False}
    })


@csrf_exempt
@require_http_methods(["POST"])
def toggle_todo(request, todo_id: int):
    """
    POST /api/todos/<todo_id>/toggle/
    Body: { tg_id, name }
    ---
    وضعیت انجام یه آیتم رو برعکس می‌کنه.
    اگه is_done=False بود True میشه (و ثبت می‌کنه چه کسی تیک زده).
    اگه is_done=True بود False میشه (undo).
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    try:
        todo = ToDoList.objects.get(id=todo_id)
    except ToDoList.DoesNotExist:
        return error_response("آیتم پیدا نشد", 404)

    user = get_or_create_user(tg_id, data.get("name", "کاربر"))

    if todo.is_done:
        # Undo: فقط صاحبش یا کسی که تیک زده می‌تونه undo کنه
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
    """
    DELETE /api/todos/<todo_id>/?tg_id=123
    ---
    حذف آیتم - فقط صاحبش.
    """
    tg_id = require_tg_id(request.GET)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    try:
        todo = ToDoList.objects.get(id=todo_id)
    except ToDoList.DoesNotExist:
        return error_response("آیتم پیدا نشد", 404)

    if todo.owner.telegram_id != tg_id:
        return error_response("فقط صاحب می‌تونه حذف کنه", 403)

    todo.delete()
    return json_response({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# Routines
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def add_routine(request):
    """
    POST /api/routines/add/
    Body: { tg_id, name, title, emoji?, frequency? }
    ---
    یه روتین جدید به لیست اضافه می‌کنه.
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    title = data.get("title", "").strip()
    if not title:
        return error_response("عنوان روتین الزامی است")

    user = get_or_create_user(tg_id, data.get("name", "کاربر"))
    routine = Routine.objects.create(
        owner=user,
        title=title,
        emoji=data.get("emoji", "⚡"),
        frequency=data.get("frequency", "daily"),
    )

    return json_response({
        "ok": True,
        "routine": {
            "id": routine.id,
            "title": routine.title,
            "emoji": routine.emoji,
            "done_today": False,
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_routine(request, routine_id: int):
    """
    POST /api/routines/<routine_id>/check/
    Body: { tg_id }
    ---
    روتین رو برای امروز تیک می‌زنه.
    اگه قبلاً تیک خورده بود، undo می‌کنه (RoutineLog رو حذف می‌کنه).
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    try:
        routine = Routine.objects.get(id=routine_id, owner__telegram_id=tg_id)
    except Routine.DoesNotExist:
        return error_response("روتین پیدا نشد", 404)

    today = timezone.now().date()
    log, created = RoutineLog.objects.get_or_create(routine=routine, date=today)

    if not created:
        # قبلاً تیک خورده بود - undo
        log.delete()
        return json_response({"ok": True, "done_today": False})

    return json_response({"ok": True, "done_today": True})


# ─────────────────────────────────────────────────────────────────────────────
# Game - ثبت امتیاز
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def submit_score(request):
    """
    POST /api/game/score/
    Body: { tg_id, name, game_type, score, duration_sec? }
    ---
    بعد از هر بازی صدا زده میشه.
    امتیاز رو ثبت می‌کنه و total_points کاربر رو آپدیت می‌کنه.
    """
    data = parse_body(request)
    tg_id = require_tg_id(data)
    if not tg_id:
        return error_response("tg_id الزامی است", 401)

    game_type = data.get("game_type", "tap_battle")
    score = int(data.get("score", 0))

    # validation: امتیازهای غیر واقعی رو رد کنیم
    if score < 0 or score > 99999:
        return error_response("امتیاز نامعتبر")

    user = get_or_create_user(tg_id, data.get("name", "کاربر"))

    GameSession.objects.create(
        player=user,
        game_type=game_type,
        score=score,
        duration_sec=int(data.get("duration_sec", 0)),
    )

    # آپدیت امتیاز کلی
    user.total_points += score
    user.save(update_fields=["total_points"])

    # لیدربورد به‌روز
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
def leaderboard(request):
    """
    GET /api/leaderboard/
    ---
    لیدربورد کامل رو برمی‌گردونه.
    شامل آخرین ۵ session برای هر بازی.
    """
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
