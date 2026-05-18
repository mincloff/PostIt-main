from django.shortcuts import redirect, render
from django.conf import settings
from django.http import HttpResponse
from django.contrib import messages
import requests
from django.utils import timezone
from datetime import timedelta
from .models import MetaAccount

import logging
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# Meta API Version Configuration
META_API_VERSION = "v20.0"
META_API_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

def meta(request):
    return render(request, 'connect_meta.html')

def connect_meta_form(request):
    scopes = ["pages_show_list", "pages_read_engagement", "pages_manage_posts", "instagram_basic", "instagram_manage_messages"]
        
    redirect_uri = settings.META_REDIRECT_URI
    auth_url = (
        f"https://www.facebook.com/v20.0/dialog/oauth?"
        f"client_id={settings.META_APP_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
        f"&response_type=code"
    )
    return redirect(auth_url)

def meta_callback(request):
    code = request.GET.get("code")
    error = request.GET.get("error")
    
    if error:
        messages.error(request, f"Authorization failed: {error}")
        return redirect('meta')
    
    if not code:
        messages.error(request, "Authorization failed - no code received")
        return redirect('meta')

    try:
        # Step 1: Exchange code for short-lived token
        token_url = "https://graph.facebook.com/v20.0/oauth/access_token"
        resp = requests.get(token_url, params={
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": settings.META_REDIRECT_URI,
            "code": code
        })
        
        if resp.status_code != 200:
            messages.error(request, "Failed to fetch access token")
            return redirect('connect_meta_form')
            
        token_data = resp.json()
        short_token = token_data.get("access_token")
        
        if not short_token:
            messages.error(request, "Failed to get access token")
            return redirect('connect_meta_form')

        # Step 2: Exchange short-lived token for long-lived
        long_url = "https://graph.facebook.com/v20.0/oauth/access_token"
        ll_resp = requests.get(long_url, params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": short_token
        })
        
        if ll_resp.status_code != 200:
            messages.error(request, "Failed to get long-lived token")
            return redirect('meta')
            
        ll_data = ll_resp.json()
        long_token = ll_data.get("access_token")
        expires_in = ll_data.get("expires_in", 5184000)
        
        if not long_token:
            messages.error(request, "Failed to get long-lived token")
            return redirect('meta')
        
        addAcc = save_meta_account(request.user, long_token, expires_in)
        
        if addAcc > 0:
            messages.success(request, f"Successfully connected accounts!")
        else:
            messages.warning(request, "No accounts were found or saved.")
            
        return redirect('manage')
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('meta')


def save_meta_account(user, access_token, expires_in):
    """Save Facebook Pages to database"""
    try:
        # Fetch Facebook Pages
        pages_resp = requests.get(
            "https://graph.facebook.com/v20.0/me/accounts",
            params={
                "access_token": access_token,
                "fields": "id,name,username,access_token"
            }
        )
        
        if pages_resp.status_code != 200:
            return 0
            
        pages_data = pages_resp.json()
        saved_count = 0
        
        if "data" in pages_data:
            for page in pages_data["data"]:
                # Use page-specific access token if available
                page_token = page.get("access_token", access_token)
                
                MetaAccount.objects.update_or_create(
                    user=user,
                    account_id=page["id"],
                    defaults={
                        "account_name": page.get("name"),
                        "username": page.get("username"),
                        "access_token": page_token,
                        "expires_at": timezone.now() + timedelta(seconds=expires_in),
                    }
                )
                saved_count += 1
                
        return saved_count
        
    except Exception as e:
        print(f"Error saving Facebook accounts: {e}")
        return 0

def disconnect_account(request, account_id):
    """Disconnect a specific account"""
    try:
        account = MetaAccount.objects.get(account_id=account_id, user=request.user)
        account_name = account.account_name or account.username
        account.delete()
        messages.success(request, f"Disconnected account: {account_name}")
    except MetaAccount.DoesNotExist:
        messages.error(request, "Account not found")
    
    return redirect('manage')


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def post_to_meta_platforms(request):
    """
    API endpoint to post content to Facebook and Instagram simultaneously
    
    Expected form data:
    - account_id: Meta account ID
    - title: Post title (used for Facebook, optional for Instagram)
    - description: Post description/caption
    - tags: Comma-separated hashtags (optional)
    - media_files: Multiple image/video files (optional)
    - platforms: Comma-separated platforms ('facebook', 'instagram') - defaults to both
    - post_type: 'photo', 'video', 'album', 'text' (auto-detected if not provided)
    """
    try:
        # Extract parameters
        account_id = request.POST.get('account_id')
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        tags = request.POST.get('tags', '')
        platforms = request.POST.get('platforms', 'facebook,instagram')
        post_type = request.POST.get('post_type', 'auto')
        
        # Get media files
        media_files = request.FILES.getlist('media_files')
        
        # Validate required fields
        if not account_id:
            return JsonResponse({"error": "account_id is required"}, status=400)
        
        if not description and not media_files:
            return JsonResponse({"error": "Either description or media files are required"}, status=400)
        
        # Parse platforms
        platform_list = [p.strip().lower() for p in platforms.split(',') if p.strip()]
        valid_platforms = ['facebook', 'instagram']
        platform_list = [p for p in platform_list if p in valid_platforms]
        
        if not platform_list:
            return JsonResponse({"error": f"At least one valid platform required: {', '.join(valid_platforms)}"}, status=400)
        
        # Get Meta account
        try:
            account = MetaAccount.objects.get(user=request.user, account_id=account_id)
        except MetaAccount.DoesNotExist:
            return JsonResponse({"error": "No Meta account found for this account_id"}, status=400)
        
        # Check if token is expired
        if account.is_token_expired:
            return JsonResponse({"error": "Access token has expired. Please re-authenticate."}, status=401)
        
        # Process tags
        hashtags = []
        if tags:
            hashtags = [f"#{tag.strip().replace('#', '')}" for tag in tags.split(',') if tag.strip()]
        
        # Auto-detect post type if not specified
        if post_type == 'auto':
            if not media_files:
                post_type = 'text'
            elif len(media_files) == 1:
                file = media_files[0]
                if file.content_type.startswith('image/'):
                    post_type = 'photo'
                elif file.content_type.startswith('video/'):
                    post_type = 'video'
                else:
                    post_type = 'photo'  # default
            else:
                post_type = 'album'
        
        # Upload media files and get URLs
        media_urls = []
        temp_file_paths = []
        
        try:
            for media_file in media_files:
                # Save file temporarily
                temp_file_name = f"temp_meta_{request.user.id}_{account_id}_{int(time.time())}_{media_file.name}"
                temp_file_path = default_storage.save(temp_file_name, ContentFile(media_file.read()))
                temp_file_paths.append(temp_file_path)
                
                # Upload to Meta platforms
                media_result = upload_media_to_meta(account.access_token, temp_file_path, media_file.content_type)
                if media_result:
                    media_urls.append({
                        'id': media_result.get('id'),
                        'type': media_result.get('type'),
                        'path': media_result.get('path')
                    })
            
            # Post to each platform
            results = {}
            
            if 'facebook' in platform_list:
                fb_result = post_to_facebook(
                    account.access_token,
                    account_id,
                    title,
                    description,
                    hashtags,
                    media_urls,
                    post_type
                )
                results['facebook'] = fb_result
            
            if 'instagram' in platform_list:
                ig_result = post_to_instagram(
                    account.access_token,
                    account_id,
                    description,
                    hashtags,
                    media_urls,
                    post_type
                )
                results['instagram'] = ig_result
            
            logger.info(f"Meta post successful for user {request.user.id}: {results}")
            
            return JsonResponse({
                "success": True,
                "results": results,
                "post_type": post_type,
                "platforms": platform_list,
                "media_count": len(media_files)
            })
            
        finally:
            # Clean up temporary files
            for temp_path in temp_file_paths:
                if temp_path and default_storage.exists(temp_path):
                    try:
                        default_storage.delete(temp_path)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temporary file {temp_path}: {cleanup_error}")
    
    except Exception as e:
        logger.error(f"Error posting to Meta platforms for user {request.user.id}: {str(e)}")
        return JsonResponse({"error": f"Post failed: {str(e)}"}, status=500)


def upload_media_to_meta(access_token, file_path, content_type):
    """Upload media file to Meta and return the media ID and file path for videos"""
    try:
        full_path = default_storage.path(file_path)
        
        # Determine if it's photo or video
        media_type = 'image' if content_type.startswith('image/') else 'video'
        
        if media_type == 'image':
            # For images, upload to photos endpoint with published=false
            url = f"{META_API_BASE_URL}/me/photos"
            
            with open(full_path, 'rb') as f:
                files = {'source': f}
                data = {
                    'access_token': access_token,
                    'published': 'false'  # Don't publish immediately
                }
                
                response = requests.post(url, files=files, data=data)
                
            if response.status_code == 200:
                result = response.json()
                return {'id': result.get('id'), 'type': 'image', 'path': full_path}
            else:
                logger.error(f"Image upload failed: {response.text}")
                return None
        else:
            # For videos, return the file path - we'll upload directly when posting
            return {'id': None, 'type': 'video', 'path': full_path}
            
    except Exception as e:
        logger.error(f"Error uploading media to Meta: {str(e)}")
        return None


def post_to_facebook(access_token, account_id, title, description, hashtags, media_urls, post_type):
    """Post content to Facebook"""
    try:
        # Prepare message
        message_parts = []
        if title:
            message_parts.append(title)
        if description:
            message_parts.append(description)
        if hashtags:
            message_parts.append(' '.join(hashtags))
        
        message = '\n\n'.join(message_parts)
        
        # Handle different post types
        if post_type == 'video' and media_urls:
            # Video post - upload directly to page's videos endpoint
            video_path = media_urls[0].get('path')
            if not video_path:
                return {
                    "success": False,
                    "error": "Video file path not found"
                }
            
            url = f"{META_API_BASE_URL}/{account_id}/videos"
            
            with open(video_path, 'rb') as f:
                files = {'source': f}
                data = {
                    'access_token': access_token,
                    'description': message,
                    'published': 'true'
                }
                
                response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get('id'),
                    "message": "Video posted successfully to Facebook"
                }
            else:
                logger.error(f"Facebook video post failed: {response.text}")
                return {
                    "success": False,
                    "error": response.text
                }
        
        # For photo and text posts
        url = f"{META_API_BASE_URL}/{account_id}/feed"
        
        data = {
            'access_token': access_token,
            'message': message
        }
        
        if post_type == 'photo' and media_urls:
            # Single photo post - use attached_media format
            photo_id = media_urls[0].get('id')
            if photo_id:
                data['attached_media[0]'] = f'{{"media_fbid":"{photo_id}"}}'
        elif post_type == 'album' and len(media_urls) > 1:
            # Multiple photos - create album
            return create_facebook_album(access_token, account_id, message, media_urls)
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "post_id": result.get('id'),
                "message": "Posted successfully to Facebook"
            }
        else:
            logger.error(f"Facebook post failed: {response.text}")
            return {
                "success": False,
                "error": response.text
            }
            
    except Exception as e:
        logger.error(f"Error posting to Facebook: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def create_facebook_album(access_token, account_id, message, media_urls):
    """Create a Facebook photo album for multiple images"""
    try:
        # Create album first
        album_url = f"{META_API_BASE_URL}/{account_id}/albums"
        album_data = {
            'access_token': access_token,
            'name': 'Posted via API',
            'message': message
        }
        
        album_response = requests.post(album_url, data=album_data)
        
        if album_response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to create album: {album_response.text}"
            }
        
        album_id = album_response.json().get('id')
        
        # Add photos to album
        photo_ids = []
        for media in media_urls:
            if media['type'] == 'image':
                photo_url = f"{META_API_BASE_URL}/{album_id}/photos"
                photo_data = {
                    'access_token': access_token,
                    'url': media['url']
                }
                
                photo_response = requests.post(photo_url, data=photo_data)
                if photo_response.status_code == 200:
                    photo_ids.append(photo_response.json().get('id'))
        
        return {
            "success": True,
            "album_id": album_id,
            "photo_ids": photo_ids,
            "message": f"Album created with {len(photo_ids)} photos"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def post_to_instagram(access_token, account_id, description, hashtags, media_urls, post_type):
    """Post content to Instagram"""
    try:
        # Get Instagram Business Account ID
        ig_account_id = get_instagram_business_account_id(access_token, account_id)
        if not ig_account_id:
            return {
                "success": False,
                "error": "Instagram Business Account not found or not linked. Please ensure your Instagram Business/Creator account is connected to this Facebook Page in Meta Business Suite.",
                "action_required": "link_instagram_account"
            }
        
        # Prepare caption
        caption_parts = []
        if description:
            caption_parts.append(description)
        if hashtags:
            caption_parts.append(' '.join(hashtags))
        
        caption = '\n\n'.join(caption_parts)
        
        if post_type == 'text' or not media_urls:
            return {
                "success": False,
                "error": "Instagram requires media content. Text-only posts are not supported."
            }
        
        # Instagram Content Publishing API requires publicly accessible URLs
        # For now, return an informative error since local file paths won't work
        # A proper solution would require hosting the media on a CDN first
        return {
            "success": False,
            "error": "Instagram posting requires media to be hosted on a publicly accessible URL. Direct file uploads are not currently supported for Instagram through this API.",
            "action_required": "host_media_externally"
        }
        
    except Exception as e:
        logger.error(f"Error posting to Instagram: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def get_instagram_business_account_id(access_token, facebook_page_id):
    """Get Instagram Business Account ID from Facebook Page ID"""
    try:
        url = f"{META_API_BASE_URL}/{facebook_page_id}"
        params = {
            'fields': 'instagram_business_account',
            'access_token': access_token
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('instagram_business_account', {}).get('id')
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting Instagram Business Account ID: {str(e)}")
        return None


def create_instagram_single_media_post(access_token, ig_account_id, media_url, caption, media_type):
    """Create a single media Instagram post"""
    try:
        # Step 1: Create media object
        create_url = f"{META_API_BASE_URL}/{ig_account_id}/media"
        create_data = {
            'caption': caption,
            'access_token': access_token
        }
        
        # Add media URL based on type
        if media_type == 'IMAGE':
            create_data['image_url'] = media_url
        else:
            create_data['video_url'] = media_url
            create_data['media_type'] = 'REELS'  # v20.0 recommends using REELS for video content
        
        create_response = requests.post(create_url, data=create_data)
        
        if create_response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to create Instagram media: {create_response.text}"
            }
        
        creation_id = create_response.json().get('id')
        
        # Step 2: Check media status (for videos, wait for processing)
        if media_type == 'VIDEO':
            # Poll for video processing status
            max_attempts = 30
            for attempt in range(max_attempts):
                status_url = f"{META_API_BASE_URL}/{creation_id}"
                status_params = {
                    'fields': 'status_code',
                    'access_token': access_token
                }
                status_response = requests.get(status_url, params=status_params)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('status_code') == 'FINISHED':
                        break
                    elif status_data.get('status_code') == 'ERROR':
                        return {
                            "success": False,
                            "error": "Video processing failed"
                        }
                
                time.sleep(2)  # Wait 2 seconds before checking again
        
        # Step 3: Publish the media
        publish_url = f"{META_API_BASE_URL}/{ig_account_id}/media_publish"
        publish_data = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        
        publish_response = requests.post(publish_url, data=publish_data)
        
        if publish_response.status_code == 200:
            result = publish_response.json()
            return {
                "success": True,
                "post_id": result.get('id'),
                "message": "Posted successfully to Instagram"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to publish Instagram media: {publish_response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def create_instagram_carousel_post(access_token, ig_account_id, media_urls, caption):
    """Create an Instagram carousel post with multiple media"""
    try:
        # Step 1: Create media objects for each item
        media_ids = []
        
        for media in media_urls:
            media_type = 'IMAGE' if media['type'] == 'image' else 'VIDEO'
            create_url = f"{META_API_BASE_URL}/{ig_account_id}/media"
            create_data = {
                'is_carousel_item': 'true',
                'access_token': access_token
            }
            
            # Add media URL based on type
            if media_type == 'IMAGE':
                create_data['image_url'] = media['url']
            else:
                create_data['video_url'] = media['url']
                create_data['media_type'] = 'REELS'  # v20.0 uses REELS for video
            
            create_response = requests.post(create_url, data=create_data)
            
            if create_response.status_code == 200:
                media_id = create_response.json().get('id')
                media_ids.append(media_id)
                
                # For videos in carousel, check processing status
                if media_type == 'VIDEO':
                    max_attempts = 30
                    for attempt in range(max_attempts):
                        status_url = f"{META_API_BASE_URL}/{media_id}"
                        status_params = {
                            'fields': 'status_code',
                            'access_token': access_token
                        }
                        status_response = requests.get(status_url, params=status_params)
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data.get('status_code') == 'FINISHED':
                                break
                            elif status_data.get('status_code') == 'ERROR':
                                logger.error(f"Video processing failed for carousel item")
                                break
                        
                        time.sleep(2)
            else:
                logger.error(f"Failed to create carousel item: {create_response.text}")
        
        if not media_ids:
            return {
                "success": False,
                "error": "Failed to create any carousel media items"
            }
        
        # Step 2: Create carousel container
        container_url = f"{META_API_BASE_URL}/{ig_account_id}/media"
        container_data = {
            'media_type': 'CAROUSEL',
            'children': ','.join(media_ids),
            'caption': caption,
            'access_token': access_token
        }
        
        container_response = requests.post(container_url, data=container_data)
        
        if container_response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to create carousel container: {container_response.text}"
            }
        
        container_id = container_response.json().get('id')
        
        # Step 3: Publish the carousel
        publish_url = f"{META_API_BASE_URL}/{ig_account_id}/media_publish"
        publish_data = {
            'creation_id': container_id,
            'access_token': access_token
        }
        
        publish_response = requests.post(publish_url, data=publish_data)
        
        if publish_response.status_code == 200:
            result = publish_response.json()
            return {
                "success": True,
                "post_id": result.get('id'),
                "message": f"Carousel posted successfully to Instagram with {len(media_ids)} items"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to publish carousel: {publish_response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }