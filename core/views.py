from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import TelegramUser, DailyNote, ToDoItem, GameScore
import json

# یک تابع کمکی برای گرفتن یا ساخت کاربر بر اساس آیدی تلگرام
def get_or_create_user(telegram_id, name):
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={'name': name}
    )
    return user

@api_view(['GET'])
def get_dashboard_data(request):
    """
    این API تمام اطلاعات لازم برای لود اولیه مینی‌اپ را برمی‌گرداند.
    """
    # در محیط واقعی، telegram_id را از هدر Telegram Web App initData استخراج می‌کنیم
    # برای سادگی اینجا فرض می‌کنیم از کلاینت ارسال شده (در فایل HTML مدیریت شده)
    telegram_id = request.GET.get('tg_id')
    if not telegram_id:
        return Response({'error': 'Unauthorized'}, status=403)
        
    try:
        user = TelegramUser.objects.get(telegram_id=telegram_id)
    except TelegramUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    # جمع‌آوری دیتا
    notes = DailyNote.objects.all().order_by('-created_at')[:10]
    todos = ToDoItem.objects.all().order_by('is_done', '-created_at')
    
    data = {
        'user': {'name': user.name, 'avatar': user.avatar_emoji, 'points': user.points},
        'notes': [{'id': n.id, 'text': n.text, 'author': n.user.name} for n in notes],
        'todos': [{'id': t.id, 'title': t.title, 'is_done': t.is_done} for t in todos],
        'leaderboard': list(TelegramUser.objects.values('name', 'avatar_emoji', 'points').order_by('-points'))
    }
    return Response(data)

@api_view(['POST'])
def add_note(request):
    """ثبت دیلی نوت جدید"""
    telegram_id = request.data.get('tg_id')
    user = get_or_create_user(telegram_id, request.data.get('name', 'Unknown'))
    note = DailyNote.objects.create(user=user, text=request.data.get('text'))
    return Response({'status': 'success', 'note_id': note.id})

@api_view(['POST'])
def update_vibe(request):
    """آپدیت وایب مودینگ (ایموجی روز)"""
    telegram_id = request.data.get('tg_id')
    user = get_or_create_user(telegram_id, request.data.get('name', 'Unknown'))
    user.avatar_emoji = request.data.get('emoji')
    user.save()
    return Response({'status': 'success', 'new_vibe': user.avatar_emoji})

@api_view(['POST'])
def submit_game_score(request):
    """ثبت امتیاز بازی"""
    telegram_id = request.data.get('tg_id')
    user = get_or_create_user(telegram_id, request.data.get('name', 'Unknown'))
    GameScore.objects.create(
        user=user,
        game_name=request.data.get('game_name'),
        score=request.data.get('score')
    )
    # آپدیت امتیاز کلی برای لیدربورد
    user.points += request.data.get('score', 0)
    user.save()
    return Response({'status': 'success', 'total_points': user.points})