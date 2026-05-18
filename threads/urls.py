from django.urls import path
from . import views

urlpatterns = [
    path('', views.threads, name='threads'),
    path('connect/', views.threads_connect, name='threads_connect'),
    path('callback/', views.threads_callback, name='threads_callback'),
    path('disconnect/<str:account_id>/', views.threads_disconnect, name='threads_disconnect'),
    path('api/post-to-threads/', views.post_to_threads, name='post_to_threads'),
]