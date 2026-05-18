

import requests
import base64
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from .models import XAccount
from django.shortcuts import render
from django.contrib import messages

import json
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import InMemoryUploadedFile
from .utils import gen_access_token

def x(request):
    return render(request, 'x.html')

@login_required
def connect_x(request):
    """Redirect to X/Twitter OAuth authorization"""
    base_url = "https://twitter.com/i/oauth2/authorize"
    params = {
        "response_type": "code",
        "client_id": settings.X_CLIENT_ID,
        "redirect_uri": settings.X_REDIRECT_URI,
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": str(request.user.id),
        "code_challenge": "challenge",
        "code_challenge_method": "plain"
    }
    auth_url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return redirect(auth_url)

@login_required
def x_callback(request):
    """Handle X/Twitter OAuth callback"""
    code = request.GET.get('code')
    # state = request.GET.get('state')
    
    if not code:
        messages.error(request, "Authorization failed or was cancelled.")
        return redirect('x')
    
    # Exchange code for tokens
    token_url = "https://api.twitter.com/2/oauth2/token"
    auth = base64.b64encode(
        f"{settings.X_CLIENT_ID}:{settings.X_CLIENT_SECRET}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": settings.X_CLIENT_ID,
        "redirect_uri": settings.X_REDIRECT_URI,
        "code_verifier": "challenge"
    }
    
    token_response = requests.post(token_url, headers=headers, data=data)
    token_data = token_response.json()
    
    if 'access_token' not in token_data:
        messages.error(request, "Failed to get tokens from X, API limit reached.")
        return redirect('x')
    
    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']
    
    # Get user info from X
    user_url = "https://api.twitter.com/2/users/me"
    user_headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(user_url, headers=user_headers)
    user_info = user_response.json().get("data", {})
    
    if not user_info:
        messages.error(request, "Failed to get X user info.")
        return redirect('x')
    
    # Save or update X account
    x_account, created = XAccount.objects.update_or_create(
        user=request.user,
        x_id=user_info['id'],
        defaults={
            'username': user_info['username'],
            'name': user_info.get('name', ''),
            'refresh_token': refresh_token
        }
    )
    
    if x_account:
        messages.success(request, f"X account with username @{user_info['username']} connected successfully.")
    else:
        messages.error(request, "Some error occurred, please try again.")

    return redirect('manage')

@login_required
def disconnect_x(request, x_id):
    """Disconnect X account"""
    try:
        x_account = XAccount.objects.get(x_id=x_id, user=request.user)
        x_account.delete()
        messages.success(request, "X account disconnected successfully.")
        return redirect('manage')
    except XAccount.DoesNotExist:
        messages.error(request, "Some error occurred, please try again.")
        return redirect('manage')


@csrf_exempt
@login_required
def post_to_x(request):
    """API endpoint to post to X/Twitter with optional media"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Parse form data
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        tags = request.POST.get('tags', '')
        x_account_id = request.POST.get('x_account_id')
        
        # Get X account
        if not x_account_id:
            return JsonResponse({'error': 'x_account_id is required'}, status=400)
        
        try:
            x_account = XAccount.objects.get(x_id=x_account_id, user=request.user)
        except XAccount.DoesNotExist:
            return JsonResponse({'error': 'X account not found'}, status=404)
        
        # Get access token from refresh token
        tokens = gen_access_token(x_account.refresh_token)
        access_token = tokens["access_token"]
        if not tokens["access_token"]:
            return JsonResponse({'error': 'Failed to generate access token'}, status=401)
        x_account.refresh_token = tokens["refresh_token"]
        x_account.save()
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Process tags
        if tags:
            try:
                # Try parsing as JSON array first
                tags_list = json.loads(tags) if tags.startswith('[') else tags.split(',')
                tags_list = [tag.strip().replace('#', '') for tag in tags_list if tag.strip()]
                hashtags = ' '.join([f"#{tag}" for tag in tags_list])
            except:
                hashtags = ''
        else:
            hashtags = ''
        
        # Compose tweet text
        tweet_text = f"{title}\n\n{description}\n\n{hashtags}".strip()
        
        # Handle media uploads if present
        media_ids = []
        media_files = request.FILES.getlist('media_files')
        
        if media_files:
            for media_file in media_files:
                media_id = upload_media_to_x(media_file, access_token)
                if media_id:
                    media_ids.append(media_id)
                else:
                    return JsonResponse({'error': f'Failed to upload media: {media_file.name}'}, status=400)
        
        # Post tweet
        tweet_url = "https://api.twitter.com/2/tweets"
        tweet_data = {"text": tweet_text}
        
        if media_ids:
            tweet_data["media"] = {"media_ids": media_ids}
        
        response = requests.post(
            tweet_url,
            headers={**headers, "Content-Type": "application/json"},
            json=tweet_data
        )
        
        if response.status_code == 201:
            tweet_data = response.json()
            tweet_id = tweet_data['data']['id']
            tweet_url = f"https://twitter.com/{x_account.username}/status/{tweet_id}"
            
            return JsonResponse({
                'success': True,
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'message': 'Posted successfully to X'
            })
        else:
            error_data = response.json()
            return JsonResponse({
                'error': 'Failed to post tweet',
                'details': error_data
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def upload_media_to_x(media_file: InMemoryUploadedFile, access_token: str):
    """Helper function to upload media to X/Twitter using chunked upload"""
    try:
        import time
        
        # Determine media type and category
        content_type = media_file.content_type
        if content_type.startswith('image/'):
            media_category = 'tweet_image'
        elif content_type.startswith('video/'):
            media_category = 'tweet_video'
        elif content_type.startswith('image/gif'):
            media_category = 'tweet_gif'
        else:
            print(f"Unsupported media type: {content_type}")
            return None
        
        # Read the file content
        media_data = media_file.read()
        file_size = len(media_data)
        
        # Step 1: Initialize upload
        init_url = "https://upload.twitter.com/1.1/media/upload.json"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        init_params = {
            'command': 'INIT',
            'total_bytes': file_size,
            'media_type': content_type,
            'media_category': media_category
        }
        
        init_response = requests.post(init_url, headers=headers, data=init_params)
        
        if init_response.status_code not in [200, 201, 202]:
            print(f"Media init error: {init_response.status_code} - {init_response.text}")
            return None
            
        media_id = init_response.json().get('media_id_string')
        if not media_id:
            print(f"No media_id in init response: {init_response.text}")
            return None
        
        # Step 2: Upload media data in chunks (5MB chunks for large files)
        chunk_size = 5 * 1024 * 1024  # 5MB
        segment_index = 0
        
        for i in range(0, file_size, chunk_size):
            chunk = media_data[i:i + chunk_size]
            
            append_params = {
                'command': 'APPEND',
                'media_id': media_id,
                'segment_index': segment_index
            }
            
            files = {'media': chunk}
            append_response = requests.post(
                init_url,
                headers=headers,
                data=append_params,
                files=files
            )
            
            # APPEND returns 204 on success (no content)
            if append_response.status_code not in [200, 202, 204]:
                print(f"Media append error at segment {segment_index}: {append_response.status_code} - {append_response.text}")
                return None
            
            segment_index += 1
        
        # Step 3: Finalize upload
        finalize_params = {
            'command': 'FINALIZE',
            'media_id': media_id
        }
        
        finalize_response = requests.post(
            init_url,
            headers=headers,
            data=finalize_params
        )
        
        # FINALIZE can return 200, 201, or 202
        if finalize_response.status_code not in [200, 201, 202]:
            print(f"Media finalize error: {finalize_response.status_code} - {finalize_response.text}")
            return None
        
        finalize_data = finalize_response.json()
        
        # Check if processing is needed (for videos and animated GIFs)
        if 'processing_info' in finalize_data:
            processing_info = finalize_data['processing_info']
            state = processing_info.get('state')
            
            # Poll for completion
            max_attempts = 60  # Up to 2 minutes for video processing
            check_after_secs = processing_info.get('check_after_secs', 2)
            
            for attempt in range(max_attempts):
                time.sleep(check_after_secs)
                
                status_params = {
                    'command': 'STATUS',
                    'media_id': media_id
                }
                
                status_response = requests.get(
                    init_url,
                    headers=headers,
                    params=status_params
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    if 'processing_info' in status_data:
                        state = status_data['processing_info'].get('state')
                        
                        if state == 'succeeded':
                            return media_id
                        elif state == 'failed':
                            error = status_data['processing_info'].get('error', {})
                            print(f"Media processing failed: {error}")
                            return None
                        
                        # Update check interval
                        check_after_secs = status_data['processing_info'].get('check_after_secs', 2)
                    else:
                        # No processing_info means it's done
                        return media_id
                else:
                    print(f"Status check failed: {status_response.status_code}")
            
            print("Media processing timeout")
            return None
        
        return media_id
        
    except Exception as e:
        print(f"Media upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

