from django.urls import path, re_path
from game import consumers

websocket_urlpatterns = [
    path('game/', consumers.ChatConsumer.as_asgi()),
    path('game/room/<str:room_name>/', consumers.GameConsumer.as_asgi()),
]

