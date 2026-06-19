from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.get_dashboard_data, name='dashboard'),
    path('note/add/', views.add_note, name='add_note'),
    path('vibe/update/', views.update_vibe, name='update_vibe'),
    path('game/score/', views.submit_game_score, name='game_score'),
]
