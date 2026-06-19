from django.db import models
from django.utils import timezone

class TelegramUser(models.Model):
    """
    مدل کاربران. چون ربات فقط برای شما دو نفر است، 
    در عمل فقط دو رکورد در این جدول خواهد بود.
    """
    telegram_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=100)
    avatar_emoji = models.CharField(max_length=10, default='🦊') # وایب پیش‌فرض
    points = models.IntegerField(default=0) # امتیاز پنل رقابتی
    
    def __str__(self):
        return f"{self.name} ({self.avatar_emoji})"

class DailyNote(models.Model):
    """دیلی نوت‌های مشترک"""
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class ToDoItem(models.Model):
    """لیست کارهای مشترک (To-Do List)"""
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class GameScore(models.Model):
    """ثبت امتیازات بازی‌ها برای پنل رقابتی"""
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    game_name = models.CharField(max_length=50) # مثلا 'TapBattle'
    score = models.IntegerField()
    played_at = models.DateTimeField(auto_now_add=True)