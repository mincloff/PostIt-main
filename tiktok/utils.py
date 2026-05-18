import requests
from django.conf import settings

def gen_access_token(refresh_token):
    """Generate new access token using refresh token (v2 API)"""
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    
    data = {
        "client_key": settings.TIKTOK_CLIENT_ID,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(url, data=data, headers=headers)
    result = response.json()
    return result.get("access_token")