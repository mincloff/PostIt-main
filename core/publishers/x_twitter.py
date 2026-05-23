import requests
import json
import os
from .base import BasePublisher

class XTwitterPublisher(BasePublisher):
    def __init__(self, integration):
        self.access_token = integration.access_token

    def publish(self, text, image_path=None, video_path=None, **kwargs):
        if not self.access_token:
            return False, "Missing Twitter access token."

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        media_id = None
        
        try:
            # Step 1: Upload Media to v1.1
            # Note: The Twitter v1.1 media upload endpoint usually requires OAuth 1.0a User Context.
            # If the integration.access_token is a Bearer Token (OAuth 2.0 User Context), 
            # some media uploads may fail depending on app permissions or endpoint support.
            # We assume the token provided has the necessary privileges.
            
            target_path = image_path or video_path
            
            if target_path and os.path.exists(target_path):
                upload_url = "https://upload.twitter.com/1.1/media/upload.json"
                upload_headers = {'Authorization': f'Bearer {self.access_token}'} # Multipart form data handles its own content-type
                
                with open(target_path, 'rb') as f:
                    files = {'media': f}
                    upload_res = requests.post(upload_url, headers=upload_headers, files=files)
                
                upload_data = upload_res.json()
                if 'media_id_string' in upload_data:
                    media_id = upload_data['media_id_string']
                else:
                    return False, f"Twitter Media Upload Error: {json.dumps(upload_data)}"
            
            # Step 2: Create Tweet via v2 API
            tweet_url = "https://api.twitter.com/2/tweets"
            payload = {"text": text}
            
            if media_id:
                payload["media"] = {"media_ids": [media_id]}

            res = requests.post(tweet_url, headers=headers, json=payload)
            data = res.json()

            if res.status_code == 201 and 'data' in data:
                return True, f"Success! Tweet ID: {data['data']['id']}"
            else:
                return False, f"Twitter API Error: {json.dumps(data)}"

        except requests.exceptions.RequestException as e:
            return False, f"Network Error: {str(e)}"
        except Exception as e:
            return False, f"System Error: {str(e)}"
