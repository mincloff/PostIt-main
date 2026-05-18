import requests
from .base import BasePublisher

class BloggerPublisher(BasePublisher):
    def publish(self, post_text, image_url=None):
        # Official Google Blogger v3 API (/posts/ endpoint)
        url = f"https://www.googleapis.com/blogger/v3/blogs/{self.account_id}/posts/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Ensure text is wrapped in basic HTML <div> tags
        html_content = f"<div>{post_text}</div>"
        if image_url:
            html_content += f'<br><img src="{image_url}" alt="Post Image"/>'
            
        # PLACEHOLDER: exact JSON payload
        payload = {
            "kind": "blogger#post",
            "blog": {
                "id": self.account_id
            },
            "title": "New Post",
            "content": html_content
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return True, data.get("id", "success_id")
        except Exception as e:
            return False, str(e)
