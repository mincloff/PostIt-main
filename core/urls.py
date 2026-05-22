# pyrefly: ignore [missing-import]
from django.urls import path
from . import views

urlpatterns = [
    # Auth Routes
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    
    # App Routes
    path('dashboard/', views.dashboard, name='dashboard'),
    path('generate/', views.generate_post, name='generate_post'),
    path('store/', views.store, name='store'),
    path('checkout/', views.checkout, name='checkout'),
    path('drafts/', views.drafts, name='drafts'),
    path('drafts/new/', views.create_manual_draft, name='create_manual_draft'),
    path('drafts/<int:post_id>/edit/', views.edit_draft, name='edit_draft'),
    path('drafts/<int:post_id>/delete/', views.delete_draft, name='delete_draft'),
    path('settings/', views.integrations_settings, name='integrations_settings'),
    path('drafts/<int:post_id>/publish/', views.publish_draft_now, name='publish_now'),
]