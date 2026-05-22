# pyrefly: ignore [missing-import]
from django.contrib import admin
# pyrefly: ignore [missing-import]
from django.urls import path, include
# pyrefly: ignore [missing-import]
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # THE FIX: Redirect the front door straight to the new engine
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),
    
    # Keep your legal and verification routes
    path('policy/', views.policy, name='policy'),
    path('tos/', views.tos, name='tos'),
    path('tiktokmhtTXhUjYfG3YODPQSXSgUpTKL7XQoIj.txt', views.tiktok, name='tiktok_verify'),
    path('ping/', views.ping, name='ping'),
    
    # Include our new Core app routes
    path('', include('core.urls')),
    
    # Include Google/Facebook Auth routes
    path('accounts/', include('allauth.urls')),
]