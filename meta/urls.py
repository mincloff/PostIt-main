from django.urls import path
from . import views

urlpatterns = [
    path('', views.meta, name='meta'),
    path('connect/', views.connect_meta_form, name='connect_meta_form'),
    path('callback/', views.meta_callback, name='meta_callback'),
    path('disconnect/<int:account_id>/', views.disconnect_account, name='disconnect_meta'),
    path('api/post/', views.post_to_meta_platforms, name='meta_post_api'),
]