# pyrefly: ignore [missing-import]
from django.contrib import admin
# pyrefly: ignore [missing-import]
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('auth/', include('auths.urls')),
    path('youtube/', include('youtube.urls')),
    path('meta/', include('meta.urls')),
    path('threads/', include('threads.urls')),
    path('x/', include('x.urls')),
    path('tiktok/', include('tiktok.urls')),
    path('linkedin/', include('linkedin.urls')),
    path('policy/', views.policy, name='policy'),
    path('tos/', views.tos, name='tos'),
    path('manage/', views.manage, name='manage'),
    path('compose/', views.compose, name='compose'),
    path("tiktokmhtTXhUjYfG3YODPQSXSgUpTKL7XQoIj.txt", views.tiktok_verification),
    path("ping/", views.ping, name="ping"),
    path('', include('core.urls')),
    path('accounts/', include('allauth.urls')),
]
