from django.urls import path
from . import views

urlpatterns = [
    path('', views.linkedin, name='linkedin'),
    path('connect/', views.linkedin_connect, name='linkedin_connect'),
    path('callback/', views.linkedin_callback, name='linkedin_callback'),
    path('disconnect/<str:linkedin_id>/', views.linkedin_disconnect, name='linkedin_disconnect'),
    path('api/post/', views.post_to_linkedin, name='linkedin_post_api'),
]