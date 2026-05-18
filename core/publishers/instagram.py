import requests
from .base import BasePublisher

class InstagramPublisher(BasePublisher):
    def publish(self, post_text, image_url=None):
        # Official Meta Graph API endpoint (using linked Facebook Page ID)
        # Step 1: Create media container
        url_container = f"https://graph.facebook.com/v19.0/{self.account_id}/media"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # PLACEHOLDER: exact JSON payload for media container
        payload_container = {
            "image_url": image_url,
            "caption": post_text
        }

        try:
            # Step 1: Create container
            response_container = requests.post(url_container, headers=headers, json=payload_container)
            response_container.raise_for_status()
            container_id = response_container.json().get("id")
            
            # Step 2: Publish container
            url_publish = f"https://graph.facebook.com/v19.0/{self.account_id}/media_publish"
            payload_publish = {
                "creation_id": container_id
            }
            response_publish = requests.post(url_publish, headers=headers, json=payload_publish)
            response_publish.raise_for_status()
            data = response_publish.json()
            
            return True, data.get("id", "success_id")
        except Exception as e:
            return False, str(e)
