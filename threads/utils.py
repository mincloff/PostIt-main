import requests
from django.conf import settings
from .models import ThreadsAccount

THREADS_SCOPES = [
    'threads_basic',
    'threads_content_publish',
    'threads_manage_insights',
    'threads_manage_replies',
    'threads_read_replies'
]

def get_access_token(user):
    """Get valid access token for user, refresh if needed"""
    try:
        account = ThreadsAccount.objects.get(user=user)
        
        # Check if token needs refresh (you can add expiry logic here if needed)
        # For now, just return the stored token
        return account.token
    except ThreadsAccount.DoesNotExist:
        return None

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    url = "https://graph.threads.net/oauth/access_token"
    
    data = {
        'client_id': settings.THREADS_APP_ID,
        'client_secret': settings.THREADS_APP_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': settings.THREADS_REDIRECT_URI,
        'code': code,
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        return response.json()
    return None

def get_long_lived_token(short_token):
    """Get long-lived token"""
    url = "https://graph.threads.net/access_token"
    
    params = {
        'grant_type': 'th_exchange_token',
        'client_secret': settings.THREADS_APP_SECRET,
        'access_token': short_token,
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    return None

def get_user_info(access_token, user_id):
    """Get user profile info"""
    url = f"https://graph.threads.net/v1.0/{user_id}"
    
    params = {
        'fields': 'id,username,name',
        'access_token': access_token,
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    return None