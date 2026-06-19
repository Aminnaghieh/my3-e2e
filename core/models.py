"""
core/models.py
==============
تعریف تمام جداول دیتابیس.

این پروژه برای دو نفر طراحی شده (شما و دوست‌دخترتون) ولی
معماری طوری نوشته شده که اگر خواستید بعداً گسترش بدید راحت باشه.

دیتابیس: SQLite (پیش‌فرض Django) که روی Render کافیه.
"""

from django.db import models
from django.utils import timezone


class TelegramUser(models.Model):
    """
    جدول کاربران تلگرام.

    هر بار که کاربر با بات /start می‌زنه یا وارد مینی‌اپ میشه،
    یه رکورد اینجا ساخته میشه یا آپدیت میشه.

    Fields:
        telegram_id: آیدی عددی یونیک تلگرام (مثل 123456789)
        username:    نام کاربری تلگرام (اختیاریه، ممکنه null باشه)
        first_name:  اسم اول کاربر از پروفایل تلگرام
        vibe_emoji:  ایموجی وایب امروز - کاربر هر روز می‌تونه عوضش کنه
        vibe_label:  توضیح کوتاه وایب مثل "انرژی بالا" یا "آروم"
        vibe_updated_at: آخرین باری که وایب آپدیت شده (برای نمایش "امروز" یا "دیروز")
        total_points: مجموع امتیازات از همه بازی‌ها - برای لیدربورد
        created_at:  تاریخ اولین ورود
    """
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=100, default="کاربر")

    # ── وایب مودینگ ──────────────────────────────────────────────
    vibe_emoji = models.CharField(max_length=10, default="✨")
    vibe_label = models.CharField(max_length=50, default="بدون وایب")
    vibe_updated_at = models.DateTimeField(default=timezone.now)

    # ── پنل رقابتی ───────────────────────────────────────────────
    total_points = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} (TG:{self.telegram_id}) {self.vibe_emoji}"

    @property
    def vibe_is_today(self):
        """True اگه وایب امروز ست شده باشه."""
        return self.vibe_updated_at.date() == timezone.now().date()


class DailyNote(models.Model):
    """
    دیلی نوت‌ها - فضای شخصی برای نوشتن.

    هر کاربر می‌تونه نوت بزنه. نوت‌ها بین هر دو نفر قابل مشاهده‌ست.
    نوت‌ها ordered از جدیدترین به قدیمی‌ترین نمایش داده میشن.

    Fields:
        author:     کی نوشته (FK به TelegramUser)
        text:       محتوای نوت (بدون محدودیت طول)
        mood_tag:   تگ احساسی اختیاری مثل "😊" یا "💭" یا "🔥"
        created_at: زمان ثبت (auto)
        is_pinned:  نوت‌های مهم رو می‌شه پین کرد
    """
    author = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="notes"
    )
    text = models.TextField()
    mood_tag = models.CharField(max_length=10, blank=True, default="")
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        preview = self.text[:40] + "..." if len(self.text) > 40 else self.text
        return f"[{self.author.first_name}] {preview}"


class Routine(models.Model):
    """
    روتین‌های روزانه.

    هر کاربر یه لیست روتین داره (مثلاً "آب خوردن صبح" یا "مدیتیشن").
    هر روز می‌تونه تیک بزنه که انجام داده یا نه.

    Fields:
        owner:       صاحب روتین
        title:       عنوان (مثل "ورزش صبح")
        emoji:       ایموجی برای بصری‌تر شدن
        frequency:   daily / weekly
        is_active:   اگه false بشه از لیست حذف میشه بدون حذف از DB
        created_at:  تاریخ ساخت
    """
    FREQUENCY_CHOICES = [
        ("daily", "روزانه"),
        ("weekly", "هفتگی"),
    ]

    owner = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="routines"
    )
    title = models.CharField(max_length=200)
    emoji = models.CharField(max_length=10, default="⚡")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default="daily")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.emoji} {self.title} ({self.owner.first_name})"


class RoutineLog(models.Model):
    """
    لاگ انجام روتین‌ها.

    هر بار که کاربر روتینی رو تیک می‌زنه، یه رکورد اینجا ثبت میشه.
    جلوگیری از ثبت تکراری: unique_together روی (routine, date).

    Fields:
        routine:     FK به Routine
        date:        تاریخ انجام (فقط تاریخ، بدون ساعت)
        done_at:     زمان دقیق تیک زدن
    """
    routine = models.ForeignKey(
        Routine,
        on_delete=models.CASCADE,
        related_name="logs"
    )
    date = models.DateField(default=timezone.now)
    done_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("routine", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.routine.title} ✓ {self.date}"


class ToDoList(models.Model):
    """
    لیست‌های To-Do.

    دو نوع To-Do داریم:
    1. شخصی (private=True): فقط صاحبش می‌بینه
    2. مشترک (private=False): هر دو نفر می‌بینن و می‌تونن آپدیت کنن

    Fields:
        owner:      صاحب لیست
        title:      عنوان آیتم
        emoji:      ایموجی (اختیاری)
        is_done:    انجام شده؟
        is_private: شخصی یا مشترک
        done_by:    چه کسی تیک زده (null اگه انجام نشده)
        done_at:    کی تیک زده
        created_at: تاریخ ساخت
        priority:   اولویت: 1=کم، 2=متوسط، 3=مهم
    """
    PRIORITY_CHOICES = [
        (1, "عادی"),
        (2, "متوسط"),
        (3, "مهم 🔥"),
    ]

    owner = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="todos"
    )
    title = models.CharField(max_length=300)
    emoji = models.CharField(max_length=10, blank=True, default="")
    is_done = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)
    done_by = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_todos"
    )
    done_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # اول undone، بعد بر اساس priority نزولی، بعد جدیدترین
        ordering = ["is_done", "-priority", "-created_at"]

    def mark_done(self, user: TelegramUser):
        """ثبت انجام شدن آیتم به همراه اینکه چه کسی تیک زده."""
        self.is_done = True
        self.done_by = user
        self.done_at = timezone.now()
        self.save()

    def __str__(self):
        status = "✓" if self.is_done else "○"
        return f"{status} {self.emoji} {self.title}"


class GameSession(models.Model):
    """
    هر بار که یه بازی انجام میشه یه Session ثبت میشه.

    Fields:
        player:       کی بازی کرده
        game_type:    نوع بازی (tap_battle, memory, reaction)
        score:        امتیاز این session
        duration_sec: چند ثانیه بازی کرده
        played_at:    زمان بازی
    """
    GAME_TYPES = [
        ("tap_battle", "نبرد تپ"),
        ("memory", "بازی حافظه"),
        ("reaction", "تست واکنش"),
    ]

    player = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="game_sessions"
    )
    game_type = models.CharField(max_length=20, choices=GAME_TYPES)
    score = models.IntegerField(default=0)
    duration_sec = models.IntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-played_at"]

    def __str__(self):
        return f"{self.player.first_name} | {self.get_game_type_display()} | {self.score}pt"
