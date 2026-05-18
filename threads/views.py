from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import ThreadsAccount
from .utils import (
    THREADS_SCOPES, 
    exchange_code_for_token, 
    get_long_lived_token, 
    get_user_info
)
from django.shortcuts import render

import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .utils import get_access_token
import requests


def threads(request):
    return render(request, 'threads.html')

@login_required
def threads_connect(request):
    """Initiate Threads OAuth"""
    auth_url = "https://threads.net/oauth/authorize"
    
    params = {
        'client_id': settings.THREADS_APP_ID,
        'redirect_uri': settings.THREADS_REDIRECT_URI,
        'scope': ','.join(THREADS_SCOPES),
        'response_type': 'code',
    }
    
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{auth_url}?{query_string}"
    
    return redirect(full_url)

@login_required
def threads_callback(request):
    """Handle OAuth callback"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        messages.error(request, f"Connection failed: {error}")
        return redirect('threads')
    
    if not code:
        messages.error(request, "No authorization code received")
        return redirect('threads')
    
    try:
        # Exchange code for token
        token_data = exchange_code_for_token(code)
        if not token_data:
            raise Exception("Failed to get access token")
        
        access_token = token_data.get('access_token')
        user_id = token_data.get('user_id')
        
        # Get long-lived token
        long_token_data = get_long_lived_token(access_token)
        if long_token_data:
            long_lived_token = long_token_data.get('access_token')
        else:
            long_lived_token = access_token  # Fallback to short-lived token
        
        # Get user info
        user_info = get_user_info(long_lived_token, user_id)
        if not user_info:
            raise Exception("Failed to get user information")
        
        # Create or update account
        ThreadsAccount.objects.update_or_create(
            user=request.user,
            account_id=user_id,
            defaults={
                'name': user_info.get('name', ''),
                'username': user_info.get('username', ''),
                'token': long_lived_token
            }
        )
        
        messages.success(request, f"Successfully connected @{user_info.get('username')}")
        return redirect('manage')
        
    except Exception as e:
        messages.error(request, f"Connection failed: {str(e)}")
        return redirect('threads')

@login_required
def threads_disconnect(request, account_id):
    """Disconnect Threads account"""
    try:
        account = ThreadsAccount.objects.get(user=request.user, account_id=account_id)
        username = account.username
        account.delete()
        messages.success(request, f"Disconnected @{username}")
    except ThreadsAccount.DoesNotExist:
        messages.error(request, "No Threads account connected")
    
    return redirect('manage')

@csrf_exempt
@login_required
def post_to_threads(request):
    """API endpoint to post to Threads with optional media"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Parse form data
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        tags = request.POST.get('tags', '')  # Comma-separated or JSON array
        threads_account_id = request.POST.get('threads_account_id')
        
        # Get Threads account
        if not threads_account_id:
            return JsonResponse({'error': 'threads_account_id is required'}, status=400)
        
        try:
            threads_account = ThreadsAccount.objects.get(
                account_id=threads_account_id, 
                user=request.user
            )
        except ThreadsAccount.DoesNotExist:
            return JsonResponse({'error': 'Threads account not found'}, status=404)
        
        access_token = threads_account.token
        
        # Process tags
        hashtags = ''
        if tags:
            try:
                tags_list = json.loads(tags) if tags.startswith('[') else tags.split(',')
                tags_list = [tag.strip().replace('#', '') for tag in tags_list if tag.strip()]
                hashtags = ' '.join([f"#{tag}" for tag in tags_list])
            except:
                hashtags = ''
        
        # Compose post text
        post_text = f"{title}\n\n{description}\n\n{hashtags}".strip()
        
        # Handle media uploads
        media_files = request.FILES.getlist('media')
        
        if len(media_files) == 0:
            # Text-only post
            post_id = create_text_post(threads_account.account_id, post_text, access_token)
            
        elif len(media_files) == 1:
            # Single image post
            media_url = request.POST.get('media_url')
            if not media_url:
                return JsonResponse({'error': 'media_url required for image posts'}, status=400)
            
            post_id = create_single_image_post(
                threads_account.account_id, 
                post_text, 
                media_url, 
                access_token
            )
            
        else:
            # Carousel post (multiple images)
            media_urls = request.POST.getlist('media_urls')
            if len(media_urls) != len(media_files):
                return JsonResponse({'error': 'media_urls must match number of media files'}, status=400)
            
            post_id = create_carousel_post(
                threads_account.account_id,
                post_text,
                media_urls,
                access_token
            )
        
        if post_id:
            # Get post permalink
            permalink = get_post_permalink(post_id, access_token)
            
            return JsonResponse({
                'success': True,
                'post_id': post_id,
                'permalink': permalink,
                'message': 'Posted successfully to Threads'
            })
        else:
            return JsonResponse({'error': 'Failed to create post'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def create_text_post(user_id, text, access_token):
    """Create a text-only Threads post"""
    try:
        # Step 1: Create media container
        create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
        
        params = {
            'media_type': 'TEXT',
            'text': text,
            'access_token': access_token
        }
        
        response = requests.post(create_url, params=params)
        
        if response.status_code != 200:
            return None
            
        container_id = response.json().get('id')
        
        # Step 2: Publish the container
        return publish_container(user_id, container_id, access_token)
        
    except Exception as e:
        print(f"Error creating text post: {str(e)}")
        return None


def create_single_image_post(user_id, text, image_url, access_token):
    """Create a single image Threads post"""
    try:
        # Step 1: Create media container
        create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
        
        params = {
            'media_type': 'IMAGE',
            'image_url': image_url,
            'text': text,
            'access_token': access_token
        }
        
        response = requests.post(create_url, params=params)
        
        if response.status_code != 200:
            return None
            
        container_id = response.json().get('id')
        
        # Wait for container to be ready
        if not wait_for_container(container_id, access_token):
            return None
        
        # Step 2: Publish the container
        return publish_container(user_id, container_id, access_token)
        
    except Exception as e:
        print(f"Error creating image post: {str(e)}")
        return None


def create_carousel_post(user_id, text, image_urls, access_token):
    """Create a carousel (multiple images) Threads post"""
    try:
        # Step 1: Create item containers for each image
        item_container_ids = []
        
        for image_url in image_urls[:10]:  # Threads supports max 10 items in carousel
            create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
            
            params = {
                'media_type': 'IMAGE',
                'image_url': image_url,
                'is_carousel_item': 'true',
                'access_token': access_token
            }
            
            response = requests.post(create_url, params=params)
            
            if response.status_code == 200:
                container_id = response.json().get('id')
                item_container_ids.append(container_id)
            else:
                print(f"Failed to create carousel item: {response.text}")
        
        if len(item_container_ids) < 2:
            return None  # Need at least 2 items for carousel
        
        # Wait for all containers to be ready
        for container_id in item_container_ids:
            if not wait_for_container(container_id, access_token):
                return None
        
        # Step 2: Create carousel container
        create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
        
        params = {
            'media_type': 'CAROUSEL',
            'children': ','.join(item_container_ids),
            'text': text,
            'access_token': access_token
        }
        
        response = requests.post(create_url, params=params)
        
        if response.status_code != 200:
            return None
            
        carousel_container_id = response.json().get('id')
        
        # Wait for carousel container to be ready
        if not wait_for_container(carousel_container_id, access_token):
            return None
        
        # Step 3: Publish the carousel
        return publish_container(user_id, carousel_container_id, access_token)
        
    except Exception as e:
        print(f"Error creating carousel post: {str(e)}")
        return None


def wait_for_container(container_id, access_token, max_attempts=30):
    """Wait for media container to be ready for publishing"""
    import time
    
    check_url = f"https://graph.threads.net/v1.0/{container_id}"
    
    for _ in range(max_attempts):
        params = {
            'fields': 'status,error_message',
            'access_token': access_token
        }
        
        response = requests.get(check_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            
            if status == 'FINISHED':
                return True
            elif status == 'ERROR':
                print(f"Container error: {data.get('error_message')}")
                return False
            # If status is 'IN_PROGRESS', continue waiting
        
        time.sleep(2)
    
    return False


def publish_container(user_id, container_id, access_token):
    """Publish a media container to Threads"""
    try:
        publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        
        params = {
            'creation_id': container_id,
            'access_token': access_token
        }
        
        response = requests.post(publish_url, params=params)
        
        if response.status_code == 200:
            return response.json().get('id')
        
        return None
        
    except Exception as e:
        print(f"Error publishing container: {str(e)}")
        return None


def get_post_permalink(post_id, access_token):
    """Get the permalink for a published post"""
    try:
        url = f"https://graph.threads.net/v1.0/{post_id}"
        
        params = {
            'fields': 'permalink',
            'access_token': access_token
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json().get('permalink')
        
        return None
        
    except Exception as e:
        print(f"Error getting permalink: {str(e)}")
        return None

