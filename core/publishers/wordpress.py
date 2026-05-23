import requests
import json
import os
import mimetypes
from .base import BasePublisher

class WordPressPublisher(BasePublisher):
    def __init__(self, integration):
        self.access_token = integration.access_token
        # Assume platform_id contains the WP domain (e.g., example.com)
        self.domain = integration.platform_id.rstrip('/') if integration.platform_id else ""
        if self.domain and not self.domain.startswith('http'):
            self.domain = f'https://{self.domain}'

    def publish(self, text, image_path=None, video_path=None, **kwargs):
        if not self.access_token or not self.domain:
            return False, "Missing access token or WordPress domain (stored in platform_id)."

        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }

        try:
            media_id = None
            media_type = None

            target_path = image_path or video_path
            media_data = {}
            
            if target_path and os.path.exists(target_path):
                # Step 1: Upload Media
                media_url = f"{self.domain}/wp-json/wp/v2/media"
                
                filename = os.path.basename(target_path)
                content_type, _ = mimetypes.guess_type(target_path)
                
                media_headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': content_type or 'application/octet-stream'
                }
                
                with open(target_path, 'rb') as f:
                    media_res = requests.post(media_url, headers=media_headers, data=f)
                
                media_data = media_res.json()
                if media_res.status_code in [200, 201] and 'id' in media_data:
                    media_id = media_data['id']
                    media_type = 'video' if video_path else 'image'
                else:
                    return False, f"WordPress Media Upload Error: {json.dumps(media_data)}"

            # Step 2: Create Post
            post_url = f"{self.domain}/wp-json/wp/v2/posts"
            
            # If it's a video, append shortcode or URL to the content body
            content = text
            if media_id and media_type == 'video':
                video_url = media_data.get('source_url', '')
                content += f'\n\n<!-- wp:video {{"id":{media_id}}} --><figure class="wp-block-video"><video controls src="{video_url}"></video></figure><!-- /wp:video -->'

            post_payload = {
                'title': text[:50] + '...' if len(text) > 50 else text, # Auto-generate title
                'content': content,
                'status': 'publish'
            }

            if media_id and media_type == 'image':
                post_payload['featured_media'] = media_id

            post_res = requests.post(post_url, headers=headers, json=post_payload)
            post_data = post_res.json()

            if post_res.status_code in [200, 201] and 'id' in post_data:
                return True, f"Success! WordPress Post ID: {post_data['id']}"
            else:
                return False, f"WordPress Publish Error: {json.dumps(post_data)}"

        except requests.exceptions.RequestException as e:
            return False, f"Network Error: {str(e)}"
        except Exception as e:
            return False, f"System Error: {str(e)}"
