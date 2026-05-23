import requests
import json
import time
from .base import BasePublisher

class InstagramPublisher(BasePublisher):
    def __init__(self, integration):
        self.access_token = integration.access_token
        self.ig_user_id = integration.platform_id

    def publish(self, text, image_path=None, video_path=None, **kwargs):
        if not self.access_token or not self.ig_user_id:
            return False, "Missing access token or IG User ID."

        image_url = kwargs.get('image_url')
        if not image_url:
            return False, "Instagram Graph API requires a public image_url to create a media container. Local uploads via path are not supported natively."

        base_url = f"https://graph.facebook.com/v19.0/{self.ig_user_id}"
        
        try:
            # Step 1: Create Media Container
            container_url = f"{base_url}/media"
            container_payload = {
                'caption': text,
                'access_token': self.access_token
            }
            
            if video_path or (image_url and image_url.endswith(('.mp4', '.mov'))):
                container_payload['media_type'] = 'REELS'
                container_payload['video_url'] = image_url
            else:
                container_payload['image_url'] = image_url

            container_res = requests.post(container_url, data=container_payload)
            container_data = container_res.json()
            
            if 'id' not in container_data:
                return False, f"Failed to create media container: {json.dumps(container_data)}"
                
            creation_id = container_data['id']

            # Step 1.5: If it's a video, wait for processing to finish
            if 'media_type' in container_payload and container_payload['media_type'] == 'REELS':
                status_url = f"https://graph.facebook.com/v19.0/{creation_id}?fields=status_code&access_token={self.access_token}"
                ready = False
                for _ in range(12): # Poll up to 1 minute (12 * 5s)
                    status_res = requests.get(status_url).json()
                    if status_res.get('status_code') == 'FINISHED':
                        ready = True
                        break
                    elif status_res.get('status_code') == 'ERROR':
                        return False, "Instagram Video Processing Error."
                    time.sleep(5)
                if not ready:
                    return False, "Video processing timed out on Instagram."

            # Step 2: Publish Container
            publish_url = f"{base_url}/media_publish"
            publish_payload = {
                'creation_id': creation_id,
                'access_token': self.access_token
            }
            
            publish_res = requests.post(publish_url, data=publish_payload)
            publish_data = publish_res.json()
            
            if publish_res.status_code == 200 and 'id' in publish_data:
                return True, f"Success! Instagram Post ID: {publish_data['id']}"
            else:
                return False, f"Instagram Publish Error: {json.dumps(publish_data)}"

        except requests.exceptions.RequestException as e:
            return False, f"Network Error: {str(e)}"
        except Exception as e:
            return False, f"System Error: {str(e)}"
