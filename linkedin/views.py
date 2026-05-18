import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import LinkedInAccount
from django.contrib import messages
from django.shortcuts import render

import logging
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def linkedin(request):
    return render(request, 'linkedin.html')

@login_required
def linkedin_connect(request):
    """Initiate LinkedIn OAuth flow"""
    auth_url = "https://www.linkedin.com/oauth/v2/authorization"
    params = {
        'response_type': 'code',
        'client_id': settings.LINKEDIN_CLIENT_ID,
        'redirect_uri': settings.LINKEDIN_REDIRECT_URI,
        'scope': 'openid profile email w_member_social',
        'state': request.user.id
    }
    
    url = f"{auth_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return redirect(url)


@login_required
def linkedin_callback(request):
    """Handle LinkedIn OAuth callback"""
    code = request.GET.get('code')
    
    if not code:
        messages.error(request, 'No authorization code received')
        return redirect('linkedin')
    
    # Exchange code for tokens
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': settings.LINKEDIN_CLIENT_ID,
        'client_secret': settings.LINKEDIN_CLIENT_SECRET,
        'redirect_uri': settings.LINKEDIN_REDIRECT_URI
    }
    
    token_response = requests.post(token_url, data=token_data)
    
    if token_response.status_code != 200:
        messages.error(request, 'Failed to obtain access token')
        return redirect('linkedin')
    
    token_info = token_response.json()
    access_token = token_info.get('access_token')
    
    # Get user profile info
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
    
    if profile_response.status_code != 200:
        messages.error(request, 'Failed to fetch user profile')
        return redirect('linkedin')
    
    profile_data = profile_response.json()
    
    # Store LinkedIn account
    LinkedInAccount.objects.update_or_create(
        user=request.user,
        linkedin_id=profile_data.get('sub'),
        defaults={
            'name': profile_data.get('name', ''),
            'username': profile_data.get('email', '').split('@')[0],
            'access_token': access_token,
            'is_active': True
        }
    )
    
    messages.success(request, 'LinkedIn account connected successfully')
    return redirect('manage')


@login_required
def linkedin_disconnect(request, linkedin_id):
    """Disconnect LinkedIn account"""
    try:
        account = LinkedInAccount.objects.get(linkedin_id=linkedin_id, user=request.user)
        account.delete()
        messages.success(request, 'LinkedIn account disconnected successfully')
        return redirect('manage')
    except LinkedInAccount.DoesNotExist:
        messages.error(request, 'LinkedIn account not found')
        return redirect('manage')




@login_required
@csrf_exempt
@require_http_methods(["POST"])
def post_to_linkedin(request):
    """
    API endpoint to post content to LinkedIn
    
    Expected form data:
    - linkedin_id: LinkedIn account ID
    - title: Post title (optional)
    - description: Post description/text content (required)
    - tags: Comma-separated hashtags (optional)
    - media_file: Single image or video file (optional)
    """
    try:
        # Extract parameters
        linkedin_id = request.POST.get('linkedin_id')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        tags = request.POST.get('tags', '').strip()
        
        # Get single media file
        media_file = request.FILES.get('media_file')
        
        # Validate required fields
        if not linkedin_id:
            return JsonResponse({"error": "linkedin_id is required"}, status=400)
        
        if not description:
            return JsonResponse({"error": "description is required"}, status=400)
        
        # Get LinkedIn account
        try:
            account = LinkedInAccount.objects.get(
                user=request.user, 
                linkedin_id=linkedin_id,
                is_active=True
            )
        except LinkedInAccount.DoesNotExist:
            return JsonResponse({"error": "No active LinkedIn account found"}, status=400)
        
        # Build post content
        post_text_parts = []
        
        if title:
            post_text_parts.append(title)
        
        post_text_parts.append(description)
        
        # Process hashtags
        if tags:
            hashtags = []
            for tag in tags.split(','):
                tag = tag.strip()
                if tag:
                    if not tag.startswith('#'):
                        tag = f"#{tag}"
                    hashtags.append(tag)
            
            if hashtags:
                post_text_parts.append(' '.join(hashtags))
        
        post_text = '\n\n'.join(post_text_parts)
        
        # Determine post type and create accordingly
        if media_file:
            # Image or video post
            if media_file.content_type.startswith('image/'):
                result = create_linkedin_image_post(account, post_text, media_file, title)
            elif media_file.content_type.startswith('video/'):
                result = create_linkedin_video_post(account, post_text, media_file, title)
            else:
                return JsonResponse({"error": "Unsupported media type. Only images and videos are supported."}, status=400)
        else:
            # Text-only post
            result = create_linkedin_text_post(account, post_text)
        
        if result['success']:
            logger.info(f"LinkedIn post successful for user {request.user.id}")
            return JsonResponse(result)
        else:
            logger.error(f"LinkedIn post failed for user {request.user.id}: {result['error']}")
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error posting to LinkedIn for user {request.user.id}: {str(e)}")
        return JsonResponse({"error": f"Post failed: {str(e)}"}, status=500)


def create_linkedin_text_post(account, text):
    """Create a text-only LinkedIn post"""
    try:
        url = "https://api.linkedin.com/v2/ugcPosts"
        
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        data = {
            "author": f"urn:li:person:{account.linkedin_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            post_id = response.headers.get('X-RestLi-Id')
            return {
                "success": True,
                "post_id": post_id,
                "message": "Text post created successfully on LinkedIn"
            }
        else:
            return {
                "success": False,
                "error": f"LinkedIn API error: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def create_linkedin_image_post(account, text, image_file, title):
    """Create an image post on LinkedIn"""
    try:
        # Step 1: Register upload
        asset_urn = register_linkedin_upload(account, "feedshare-image")
        if not asset_urn['success']:
            return asset_urn
        
        upload_url = asset_urn['upload_url']
        asset_id = asset_urn['asset_id']
        
        # Step 2: Upload image
        upload_result = upload_media_to_linkedin(upload_url, image_file, account.access_token)
        if not upload_result['success']:
            return upload_result
        
        # Step 3: Create post with image
        url = "https://api.linkedin.com/v2/ugcPosts"
        
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        media_data = {
            "status": "READY",
            "media": asset_id
        }
        
        if title:
            media_data["title"] = {"text": title}
        
        data = {
            "author": f"urn:li:person:{account.linkedin_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": [media_data]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            post_id = response.headers.get('X-RestLi-Id')
            return {
                "success": True,
                "post_id": post_id,
                "message": "Image post created successfully on LinkedIn"
            }
        else:
            return {
                "success": False,
                "error": f"LinkedIn API error: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def create_linkedin_video_post(account, text, video_file, title):
    """Create a video post on LinkedIn"""
    try:
        # Step 1: Register upload
        asset_urn = register_linkedin_upload(account, "feedshare-video")
        if not asset_urn['success']:
            return asset_urn
        
        upload_url = asset_urn['upload_url']
        asset_id = asset_urn['asset_id']
        
        # Step 2: Upload video
        upload_result = upload_media_to_linkedin(upload_url, video_file, account.access_token)
        if not upload_result['success']:
            return upload_result
        
        # Step 3: Create post with video
        url = "https://api.linkedin.com/v2/ugcPosts"
        
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        media_data = {
            "status": "READY",
            "media": asset_id
        }
        
        if title:
            media_data["title"] = {"text": title}
        
        data = {
            "author": f"urn:li:person:{account.linkedin_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "VIDEO",
                    "media": [media_data]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            post_id = response.headers.get('X-RestLi-Id')
            return {
                "success": True,
                "post_id": post_id,
                "message": "Video post created successfully on LinkedIn"
            }
        else:
            return {
                "success": False,
                "error": f"LinkedIn API error: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def register_linkedin_upload(account, recipe_type):
    """Register an upload with LinkedIn to get upload URL"""
    try:
        url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        data = {
            "registerUploadRequest": {
                "recipes": [f"urn:li:digitalmediaRecipe:{recipe_type}"],
                "owner": f"urn:li:person:{account.linkedin_id}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            upload_mechanism = result['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']
            
            return {
                "success": True,
                "upload_url": upload_mechanism['uploadUrl'],
                "asset_id": result['value']['asset']
            }
        else:
            return {
                "success": False,
                "error": f"Failed to register upload: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def upload_media_to_linkedin(upload_url, media_file, access_token):
    """Upload media file to LinkedIn"""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream"
        }
        
        # Read file content
        media_file.seek(0)  # Reset file pointer
        file_content = media_file.read()
        
        # LinkedIn requires PUT request for binary uploads
        response = requests.put(
            upload_url,
            headers=headers,
            data=file_content
        )
        
        # LinkedIn returns 201 for successful uploads
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "message": "Media uploaded successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to upload media: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }