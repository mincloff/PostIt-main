import requests
from .base import BasePublisher

class BloggerPublisher(BasePublisher):
    def publish(self, post_text, image_url=None):
        print(f"--- INITIATING GOOGLE BLOGGER API ---")
        
        # 1. Format the AI text into a beautiful HTML blog post
        html_content = f"<div style='font-family: sans-serif; font-size: 16px; line-height: 1.6; color: #333;'>{post_text}</div>"
        
        if image_url:
             # We put the Unsplash image at the top of the blog post
            html_content = f"<img src='{image_url}' alt='Blog Image' style='width: 100%; max-width: 800px; border-radius: 8px; margin-bottom: 20px;'/><br>{html_content}"

        # 2. Prepare the exact Google API Payload
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

        # 3. Fire the API to Google's Servers
        try:
            print("Sending payload to Google...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                post_url = response.json().get('url')
                print(f"SUCCESS: Blog is live at {post_url}")
                return True, post_url
            else:
                error_msg = response.json().get('error', {}).get('message', 'Unknown Google Error')
                print(f"BLOGGER REJECTED: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            print(f"SYSTEM ERROR: {str(e)}")
            return False, str(e)