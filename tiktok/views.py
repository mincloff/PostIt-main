import requests
import secrets
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
from .models import TikTokAccount
from django.contrib import messages
from urllib.parse import unquote

import time
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .utils import gen_access_token

def tiktok(request):
    return render(request, 'tiktok.html')

@login_required
def connect_tiktok(request):
    """Redirect to TikTok OAuth authorization"""
    # Generate CSRF state token
    csrf_state = secrets.token_urlsafe(32)
    cache.set(f"tiktok_state_{request.user.id}", csrf_state, 600)  # 10 min expiry
    
    base_url = "https://www.tiktok.com/v2/auth/authorize/"
    params = {
        "client_key": settings.TIKTOK_CLIENT_ID,
        "redirect_uri": settings.TIKTOK_REDIRECT_URI,
        "scope": "user.info.basic,video.upload,video.publish",
        "response_type": "code",
        "state": csrf_state
    }
    auth_url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return redirect(auth_url)

@login_required
def tiktok_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    if not code:
        messages.error(request, "Authorization denied or failed.")
        return redirect('tiktok')

    stored_state = cache.get(f"tiktok_state_{request.user.id}")
    if stored_state != state:
        messages.error(request, "Invalid state parameter. Possible CSRF attack.")
        return redirect('tiktok')
    cache.delete(f"tiktok_state_{request.user.id}")

    # v2 token exchange
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    payload = {
        "client_key": settings.TIKTOK_CLIENT_ID,       # use the *Client Key* from TikTok dev portal
        "client_secret": settings.TIKTOK_CLIENT_SECRET, # not your random app secret from somewhere else
        "code": unquote(code),
        "grant_type": "authorization_code",
        "redirect_uri": settings.TIKTOK_REDIRECT_URI,   # must EXACTLY match what you used on authorize
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_resp = requests.post(token_url, data=payload, headers=headers, timeout=15)
    token_json = token_resp.json()

    if "access_token" not in token_json:
        # log server-side to see error/error_description/log_id from TikTok
        print("TikTok token error:", token_resp.text)
        messages.error(request, token_json.get("error_description") or "Failed to obtain access token.")
        return redirect('tiktok')

    access_token = token_json["access_token"]
    refresh_token = token_json.get("refresh_token")
    open_id = token_json.get("open_id")

    # v2 user info (GET)
    user_url = "https://open.tiktokapis.com/v2/user/info/"
    user_resp = requests.get(
        user_url,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "open_id,union_id,avatar_url,display_name"},
        timeout=15,
    )
    user_json = user_resp.json()
    user_data = (user_json.get("data") or {}).get("user") or {}

    if not user_data:
        print("TikTok user info error:", user_resp.text)
        messages.error(request, "Failed to fetch user info from TikTok.")
        return redirect('tiktok')

    TikTokAccount.objects.update_or_create(
        user=request.user,
        tiktok_id=open_id,
        defaults={
            "username": user_data.get('display_name', '').replace(' ', '').lower(),
            "display_name": user_data.get("display_name", ""),
            "avatar_url": user_data.get("avatar_url", ""),
            "refresh_token": refresh_token,
        },
    )
    messages.success(request, "TikTok account connected successfully.")
    return redirect('manage')


@login_required
def disconnect_tiktok(request, tiktok_id):
    """Disconnect TikTok account"""
    try:
        tiktok_account = TikTokAccount.objects.get(tiktok_id=tiktok_id, user=request.user)
        tiktok_account.delete()
        messages.success(request, "TikTok account disconnected successfully.")   
        return redirect('manage')
    except TikTokAccount.DoesNotExist:
        messages.error(request, "TikTok account not found.")   
        return redirect('manage')
    


@login_required
@csrf_exempt
def upload_tiktok_video(request):
    """
    Upload a video directly to TikTok using v2 API
    
    Expected POST data:
    - tiktok_account_id: ID of the TikTokAccount to use
    - video_file: The video file to upload
    - title: Video title/caption
    - description: Video description (optional, can be combined with title)
    - tags: Comma-separated hashtags (without #)
    - privacy_level: "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY" (optional, default PUBLIC)
    - disable_duet: boolean (optional)
    - disable_stitch: boolean (optional)
    - disable_comment: boolean (optional)
    """
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get TikTok account
        tiktok_account_id = request.POST.get('tiktok_account_id')
        if not tiktok_account_id:
            return JsonResponse({'error': 'tiktok_account_id is required'}, status=400)
        
        tiktok_account = get_object_or_404(
            TikTokAccount, 
            tiktok_id=tiktok_account_id, 
            user=request.user
        )
        
        # Get video file
        video_file = request.FILES.get('video_file')
        if not video_file:
            return JsonResponse({'error': 'video_file is required'}, status=400)
        
        # Validate video file
        if video_file.size > 287 * 1024 * 1024:  # 287MB limit for TikTok
            return JsonResponse({'error': 'Video file too large. Maximum size is 287MB'}, status=400)
        
        # Get video metadata
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        tags = request.POST.get('tags', '')
        privacy_level = request.POST.get('privacy_level', 'PUBLIC_TO_EVERYONE')
        disable_duet = request.POST.get('disable_duet', 'false').lower() == 'true'
        disable_stitch = request.POST.get('disable_stitch', 'false').lower() == 'true'
        disable_comment = request.POST.get('disable_comment', 'false').lower() == 'true'
        
        # Prepare caption with hashtags
        caption_parts = []
        if title:
            caption_parts.append(title)
        if description:
            caption_parts.append(description)
        
        # Add hashtags
        if tags:
            hashtags = ['#' + tag.strip().replace('#', '') for tag in tags.split(',') if tag.strip()]
            caption_parts.append(' '.join(hashtags))
        
        caption = ' '.join(caption_parts)[:2200]  # TikTok caption limit
        
        # Get fresh access token
        access_token = gen_access_token(tiktok_account.refresh_token)
        if not access_token:
            return JsonResponse({'error': 'Failed to refresh access token'}, status=401)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; charset=UTF-8'
        }
        
        # Step 1: Query Creator Info first to verify permissions
        creator_info_url = 'https://open.tiktokapis.com/v2/user/info/'
        creator_response = requests.get(
            creator_info_url,
            headers={'Authorization': f'Bearer {access_token}'},
            params={'fields': 'open_id,union_id,avatar_url,display_name'},
            timeout=30
        )
        
        if creator_response.status_code != 200:
            return JsonResponse({
                'error': 'Failed to verify account permissions',
                'details': 'Please ensure the TikTok account has granted video.publish and video.upload permissions',
                'status_code': creator_response.status_code
            }, status=400)
        
        # Step 2: Initialize video upload with corrected structure
        init_url = 'https://open.tiktokapis.com/v2/post/publish/video/init/'
        
        # Read video content
        video_content = video_file.read()
        video_size = len(video_content)
        
        # Calculate chunk size:
        # - For small videos (< 10MB), use single chunk upload (chunk_size = video_size)
        # - For larger videos, use 10MB chunks (TikTok recommends 5-64MB, but 10MB is reliable)
        # - Never exceed 64MB per chunk
        if video_size < 10 * 1024 * 1024:  # Less than 10MB
            chunk_size = video_size  # Single chunk upload
            total_chunks = 1
        else:
            chunk_size = 10 * 1024 * 1024  # 10MB chunks
            total_chunks = (video_size + chunk_size - 1) // chunk_size
        
        init_data = {
            'post_info': {
                'title': caption if caption else 'Video',
                'privacy_level': privacy_level,
                'disable_duet': disable_duet,
                'disable_stitch': disable_stitch,
                'disable_comment': disable_comment,
                'video_cover_timestamp_ms': 1000,
                'brand_content_toggle': False,
                'brand_organic_toggle': False
            },
            'source_info': {
                'source': 'FILE_UPLOAD',
                'video_size': video_size,
                'chunk_size': chunk_size,
                'total_chunk_count': total_chunks
            }
        }
        
        init_response = requests.post(
            init_url,
            headers=headers,
            json=init_data,
            timeout=30
        )
        
        if init_response.status_code != 200:
            error_data = init_response.json() if init_response.text else {}
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            
            # Check for specific permission errors
            if 'integration guidelines' in error_message.lower() or 'scope' in error_message.lower():
                return JsonResponse({
                    'error': 'Permission Error',
                    'details': 'This TikTok account needs to re-authorize with video posting permissions. Please reconnect the account with video.publish and video.upload scopes.',
                    'log_id': error_data.get('error', {}).get('log_id'),
                    'action_required': 'reauthorize'
                }, status=403)
            
            return JsonResponse({
                'error': 'Failed to initialize upload',
                'details': error_message,
                'log_id': error_data.get('error', {}).get('log_id')
            }, status=400)
        
        init_result = init_response.json()
        
        if 'data' not in init_result:
            return JsonResponse({
                'error': 'Invalid response from TikTok',
                'details': init_result
            }, status=400)
        
        publish_id = init_result['data']['publish_id']
        upload_url = init_result['data']['upload_url']
        
        # Step 3: Upload video chunks with proper headers
        # Note: We use the declared chunk_size for splitting, but actual chunks may be smaller
        for chunk_num in range(total_chunks):
            start = chunk_num * chunk_size
            # The actual chunk size can be smaller than declared, especially for last chunk
            end = min(start + chunk_size, video_size)
            chunk_data = video_content[start:end]
            actual_chunk_size = len(chunk_data)
            
            # Upload chunk with proper headers
            upload_headers = {
                'Content-Type': 'video/mp4',
                'Content-Length': str(actual_chunk_size)
            }
            
            # Add Content-Range header for chunked uploads
            # Format: bytes start-end/total
            upload_headers['Content-Range'] = f'bytes {start}-{end-1}/{video_size}'
            
            chunk_response = requests.put(
                upload_url,
                headers=upload_headers,
                data=chunk_data,
                timeout=120  # Increased timeout for larger chunks
            )
            
            if chunk_response.status_code not in [200, 201, 206]:
                return JsonResponse({
                    'error': f'Failed to upload video chunk {chunk_num + 1}/{total_chunks}',
                    'status': chunk_response.status_code,
                    'details': chunk_response.text[:500] if chunk_response.text else 'No details',
                    'chunk_info': {
                        'chunk_num': chunk_num,
                        'start': start,
                        'end': end,
                        'actual_size': actual_chunk_size,
                        'declared_chunk_size': chunk_size
                    }
                }, status=400)
        
        # Step 4: Check upload status and publish
        max_retries = 60  # Increased retries for longer processing
        retry_count = 0
        
        while retry_count < max_retries:
            status_url = 'https://open.tiktokapis.com/v2/post/publish/status/fetch/'
            status_response = requests.post(
                status_url,
                headers=headers,
                json={'publish_id': publish_id},
                timeout=30
            )
            
            if status_response.status_code != 200:
                return JsonResponse({
                    'error': 'Failed to check upload status',
                    'details': status_response.json() if status_response.text else 'No details'
                }, status=400)
            
            status_data = status_response.json()
            
            if 'data' in status_data:
                status = status_data['data'].get('status')
                
                if status == 'PUBLISH_COMPLETE':
                    # Success! Get the published video ID
                    published_ids = status_data['data'].get('publicaly_available_post_id', [])
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Video uploaded successfully',
                        'publish_id': publish_id,
                        'video_id': published_ids[0] if published_ids else None,
                        'video_ids': published_ids,
                        'status': status
                    })
                
                elif status in ['FAILED', 'PUBLISH_FAILED']:
                    fail_reason = status_data['data'].get('fail_reason', 'Unknown error')
                    return JsonResponse({
                        'error': 'Video upload failed',
                        'reason': fail_reason,
                        'details': status_data
                    }, status=400)
                
                elif status in ['PROCESSING_UPLOAD', 'PROCESSING_DOWNLOAD', 'SENDING_TO_REVIEW', 'PUBLISHING']:
                    # Still processing, wait and retry
                    time.sleep(3)  # Slightly longer wait between checks
                    retry_count += 1
                    continue
                
                else:
                    # Unknown status, but might still be processing
                    time.sleep(3)
                    retry_count += 1
                    continue
            
            retry_count += 1
            time.sleep(3)
        
        # If we've exhausted retries, return the last known status
        return JsonResponse({
            'warning': 'Upload is taking longer than expected',
            'publish_id': publish_id,
            'message': 'Video is still being processed. Use the status endpoint to check progress.',
            'last_status': status if 'status' in locals() else 'UNKNOWN'
        }, status=202)
        
    except TikTokAccount.DoesNotExist:
        return JsonResponse({'error': 'TikTok account not found'}, status=404)
    
    except requests.RequestException as e:
        return JsonResponse({
            'error': 'Network error occurred',
            'details': str(e)
        }, status=500)
    
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': 'An unexpected error occurred',
            'details': str(e),
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)


@login_required
def get_upload_status(request, publish_id):
    """
    Check the status of a video upload
    """
    try:
        tiktok_account_id = request.GET.get('tiktok_account_id')
        if not tiktok_account_id:
            return JsonResponse({'error': 'tiktok_account_id is required'}, status=400)
        
        tiktok_account = get_object_or_404(
            TikTokAccount,
            tiktok_id=tiktok_account_id,  # Fixed: using tiktok_id instead of id
            user=request.user
        )
        
        access_token = gen_access_token(tiktok_account.refresh_token)
        if not access_token:
            return JsonResponse({'error': 'Failed to refresh access token'}, status=401)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        status_url = 'https://open.tiktokapis.com/v2/post/publish/status/fetch/'
        status_response = requests.post(
            status_url,
            headers=headers,
            json={'publish_id': publish_id},
            timeout=30
        )
        
        if status_response.status_code != 200:
            return JsonResponse({
                'error': 'Failed to check upload status',
                'details': status_response.json() if status_response.text else 'No details'
            }, status=400)
        
        status_data = status_response.json()
        
        if 'data' in status_data:
            return JsonResponse({
                'success': True,
                'status': status_data['data'].get('status'),
                'video_id': status_data['data'].get('publicaly_available_post_id', []),
                'fail_reason': status_data['data'].get('fail_reason'),
                'data': status_data['data']
            })
        
        return JsonResponse({
            'error': 'Invalid response from TikTok',
            'details': status_data
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'error': 'An error occurred',
            'details': str(e)
        }, status=500)