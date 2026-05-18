from django.urls import path
from . import views

urlpatterns = [
    path('', views.youtube, name='youtube'),
    path("auth/start/", views.youtube_auth_start, name="youtube_auth_start"),
    path("callback/", views.youtube_auth_callback, name="youtube_auth_callback"),
    path("refresh-info/", views.refresh_youtube_info, name="refresh_youtube_info"),
    path('disconnect/<str:channel_id>/', views.disconnectAcc, name='disconnect_yt'),
    path('api/upload/', views.upload_video_api, name='upload_video_api'),
]