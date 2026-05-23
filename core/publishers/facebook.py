import requests
import json
from .base import BasePublisher

class FacebookPublisher(BasePublisher):
    def __init__(self, integration):
        self.access_token = integration.access_token
        self.page_id = integration.platform_id

    def publish(self, text, image_path=None, video_path=None, **kwargs):
        if not self.access_token or not self.page_id:
            return False, "Missing access token or page ID."

        base_url = f"https://graph.facebook.com/v19.0/{self.page_id}"
        
        try:
            if video_path:
                url = f"{base_url}/videos"
                payload = {'description': text, 'access_token': self.access_token}
                with open(video_path, 'rb') as f:
                    files = {'source': f}
                    response = requests.post(url, data=payload, files=files)
            elif image_path:
                url = f"{base_url}/photos"
                payload = {'message': text, 'access_token': self.access_token}
                with open(image_path, 'rb') as f:
                    files = {'source': f}
                    response = requests.post(url, data=payload, files=files)
            else:
                url = f"{base_url}/feed"
                payload = {'message': text, 'access_token': self.access_token}
                response = requests.post(url, data=payload)

            response_data = response.json()
            if response.status_code == 200 and 'id' in response_data:
                return True, f"Success! Facebook Post ID: {response_data['id']}"
            else:
                return False, f"Facebook API Error: {json.dumps(response_data)}"

        except requests.exceptions.RequestException as e:
            return False, f"Network Error: {str(e)}"
        except Exception as e:
            return False, f"System Error: {str(e)}"
