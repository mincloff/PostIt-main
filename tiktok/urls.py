from django.urls import path
from . import views

urlpatterns = [
    path('', views.tiktok, name='tiktok'),
    path('connect/', views.connect_tiktok, name='connect_tiktok'),
    path('callback/', views.tiktok_callback, name='callback_tiktok'),
    path('disconnect/<str:tiktok_id>/', views.disconnect_tiktok, name='disconnect_tiktok'),
    path('api/upload/', views.upload_tiktok_video, name='upload_tiktok_video'),
    path('api/status/<str:publish_id>/', views.get_upload_status, name='get_upload_status'),
]