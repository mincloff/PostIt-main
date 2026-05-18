import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_access_token(youtube_account):
    """
    Get a fresh access token using the stored refresh token
    """
    if not youtube_account.refresh_token:
        logger.error("No refresh token available")
        return None
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        "refresh_token": youtube_account.refresh_token,
        "grant_type": "refresh_token",
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()
        
        access_token = token_data.get("access_token")
        if not access_token:
            logger.error(f"No access token in response: {token_data}")
            return None
            
        # Check if we got a new refresh token and update it
        new_refresh_token = token_data.get("refresh_token")
        if new_refresh_token:
            youtube_account.refresh_token = new_refresh_token
            youtube_account.save()
            logger.info("Updated refresh token")
        
        return access_token
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error refreshing access token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {e}")
        return None