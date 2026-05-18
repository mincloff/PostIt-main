from django.urls import path
from . import views

urlpatterns = [
    path('', views.x, name='x'),
    path('connect/', views.connect_x, name='connect-x'),
    path('callback/', views.x_callback, name='callback-x'),
    path('disconnect/<str:x_id>/', views.disconnect_x, name='disconnect-x'),
    path('api/post-to-x/', views.post_to_x, name='post_to_x'),
]