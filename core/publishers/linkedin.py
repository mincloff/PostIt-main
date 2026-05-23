import requests
import json
import os
from .base import BasePublisher

class LinkedInPublisher(BasePublisher):
    def __init__(self, integration):
        self.access_token = integration.access_token
        # LinkedIn URN could be a person or organization.
        self.author_id = integration.platform_id 

    def publish(self, text, image_path=None, video_path=None, **kwargs):
        if not self.access_token or not self.author_id:
            return False, "Missing access token or author ID."

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json'
        }

        try:
            asset_urn = None
            media_category = "NONE"

            if image_path and os.path.exists(image_path):
                # Step 1: Register Upload
                register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
                register_payload = {
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": self.author_id,
                        "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
                    }
                }
                reg_res = requests.post(register_url, headers=headers, json=register_payload)
                reg_data = reg_res.json()
                
                if 'value' not in reg_data:
                    return False, f"LinkedIn Asset Registration Failed: {json.dumps(reg_data)}"
                    
                upload_url = reg_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                asset_urn = reg_data['value']['asset']

                # Step 2: Upload Image
                with open(image_path, 'rb') as img_file:
                    upload_headers = {'Authorization': f'Bearer {self.access_token}'}
                    upload_res = requests.put(upload_url, headers=upload_headers, data=img_file)
                    
                    if upload_res.status_code not in [200, 201]:
                        return False, f"LinkedIn Image Upload Failed: {upload_res.text}"
                
                media_category = "IMAGE"

            elif video_path and os.path.exists(video_path):
                # For videos, the recipe is different
                register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
                register_payload = {
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                        "owner": self.author_id,
                        "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
                    }
                }
                reg_res = requests.post(register_url, headers=headers, json=register_payload)
                reg_data = reg_res.json()
                
                if 'value' not in reg_data:
                    return False, f"LinkedIn Video Registration Failed: {json.dumps(reg_data)}"
                    
                upload_url = reg_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                asset_urn = reg_data['value']['asset']

                with open(video_path, 'rb') as vid_file:
                    upload_headers = {'Authorization': f'Bearer {self.access_token}'}
                    upload_res = requests.put(upload_url, headers=upload_headers, data=vid_file)
                    
                    if upload_res.status_code not in [200, 201]:
                        return False, f"LinkedIn Video Upload Failed: {upload_res.text}"
                
                media_category = "VIDEO"

            # Step 3: Create Post
            post_url = "https://api.linkedin.com/v2/ugcPosts"
            post_payload = {
                "author": self.author_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": media_category
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }

            if asset_urn:
                post_payload['specificContent']['com.linkedin.ugc.ShareContent']['media'] = [
                    {"status": "READY", "media": asset_urn}
                ]

            post_res = requests.post(post_url, headers=headers, json=post_payload)
            post_data = post_res.json()

            if post_res.status_code == 201 and 'id' in post_data:
                return True, f"Success! LinkedIn Post URN: {post_data['id']}"
            else:
                return False, f"LinkedIn Publish Error: {json.dumps(post_data)}"

        except requests.exceptions.RequestException as e:
            return False, f"Network Error: {str(e)}"
        except Exception as e:
            return False, f"System Error: {str(e)}"
