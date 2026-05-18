import requests
from .base import BasePublisher

class FacebookPublisher(BasePublisher):
    def publish(self, post_text, image_url=None):
        # Official Meta Graph API endpoint (using client's Facebook ID)
        url = f"https://graph.facebook.com/v19.0/{self.account_id}/feed"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # PLACEHOLDER: exact JSON payload
        payload = {
            "message": post_text
        }
        if image_url:
            payload["url"] = image_url

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return True, data.get("id", "success_id")
        except Exception as e:
            return False, str(e)
