import requests
from .base import BasePublisher

class BloggerPublisher(BasePublisher):
    def publish(self, post_text, image_url=None):
        html_content = f"<div style='font-family: sans-serif; font-size: 16px; line-height: 1.6; color: #333;'>{post_text}</div>"
        if image_url:
            html_content = f"<img src='{image_url}' alt='Blog Image' style='width: 100%; max-width: 800px; border-radius: 8px; margin-bottom: 20px;'/><br>{html_content}"

        url = f"https://www.googleapis.com/blogger/v3/blogs/{self.account_id}/posts/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "kind": "blogger#post",
            "title": "New Post from PostIt Ultra AI ✨", 
            "content": html_content
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return True, response.json().get('url')
            return False, response.json().get('error', {}).get('message', 'Unknown Error')
        except Exception as e:
            return False, str(e)
