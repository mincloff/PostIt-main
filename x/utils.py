import requests
import base64
from django.conf import settings

def gen_access_token(refresh_token):
    """Generate new access token using refresh token"""
    url = "https://api.twitter.com/2/oauth2/token"
    
    auth = base64.b64encode(
        f"{settings.X_CLIENT_ID}:{settings.X_CLIENT_SECRET}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": settings.X_CLIENT_ID,
        "client_secret": settings.X_CLIENT_SECRET
    }
    
    response = requests.post(url, headers=headers, data=data)
    resp = response.json()
    return {"access_token": resp.get("access_token"), "refresh_token": resp.get("refresh_token")}