import requests
import json
import os
from .base import BasePublisher

class TikTokPublisher(BasePublisher):
    def __init__(self, integration):
        self.access_token = integration.access_token

    def publish(self, text, image_path=None, video_path=None, **kwargs):
        if not self.access_token:
            return False, "Missing TikTok access token."

        if not video_path:
            return False, "TikTok requires a video sequence. Text-only or single image uploads are unsupported in this implementation."

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json; charset=UTF-8'
        }

        try:
            if video_path and os.path.exists(video_path):
                # Step 1: Initialize Video Upload (TikTok Direct Post API)
                init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
                video_size = os.path.getsize(video_path)
                
                init_payload = {
                    "post_info": {
                        "title": text,
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                        "video_cover_timestamp_ms": 1000
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": video_size,
                        "chunk_size": video_size, 
                        "total_chunk_count": 1
                    }
                }

                init_res = requests.post(init_url, headers=headers, json=init_payload)
                init_data = init_res.json()

                if 'data' not in init_data or 'upload_url' not in init_data['data']:
                    return False, f"TikTok Video Init Failed: {json.dumps(init_data)}"

                upload_url = init_data['data']['upload_url']
                publish_id = init_data['data']['publish_id']

                # Step 2: Upload Video Data Chunk
                # TikTok requires putting the binary data directly to the upload_url
                with open(video_path, 'rb') as f:
                    upload_headers = {
                        'Content-Type': 'video/mp4', 
                        'Content-Range': f'bytes 0-{video_size-1}/{video_size}'
                    }
                    upload_res = requests.put(upload_url, headers=upload_headers, data=f)
                
                if upload_res.status_code not in [200, 201]:
                    return False, f"TikTok Video Chunk Upload Failed: Status {upload_res.status_code} - {upload_res.text}"

                # Once chunks are uploaded, TikTok processes and publishes automatically based on the publish_id.
                return True, f"Success! TikTok Video Published/Queued. Publish ID: {publish_id}"

        except requests.exceptions.RequestException as e:
            return False, f"Network Error: {str(e)}"
        except Exception as e:
            return False, f"System Error: {str(e)}"
