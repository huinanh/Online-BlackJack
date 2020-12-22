from django.contrib import admin
from django.urls import include, path

from game import consumers, views

urlpatterns = [
    path('', views.lobby, name='home'),
    path('room/<str:room_name>/', views.game_room, name='game-room'),
    path('login', views.user_login, name='login'),
    path('register', views.user_register, name='register'),
    path('profile/<str:username>', views.user_profile, name='profile'),
    path('photo/<int:profile_id>', views.get_photo, name='photo'),
    path('blackjack', views.enter_room, name='room'),
    path('logout', views.user_logout, name='logout'),
    path('addRoom', views.add_room),
    path('score', views.score_board, name='score-board'),
    path('refresh-score', views.refresh_score, name='refresh-score'),
    path('refresh-game-room', views.refresh_game_room),
    path('refresh-friends', views.refresh_friends, name='refresh-friends'),
    path('send-invitation', views.send_invitation, name='send-invitation'),
    path('get-invitation', views.get_invitation, name='get-invitation'),
    path('accept-invitation', views.accept_invitation, name='accept-invitation'),
]
