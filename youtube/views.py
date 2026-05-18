from django.shortcuts import render, redirect
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import YouTubeAccount
import logging
from django.contrib import messages

from django.http import JsonResponse
from .utils import get_access_token
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials




# Set up logging
logger = logging.getLogger(__name__)

@login_required
def youtube(request):
    return render(request, 'youtube.html')

# Step 1: Redirect user to Google consent screen
@login_required
def youtube_auth_start(request):
    scope = " ".join(settings.YOUTUBE_SCOPES)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.YOUTUBE_CLIENT_ID}"
        f"&redirect_uri={settings.YOUTUBE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return redirect(auth_url)

# Step 2: Callback – exchange code for tokens, store refresh token
@login_required
def youtube_auth_callback(request):
    code = request.GET.get("code")
    error = request.GET.get("error")
    
    if error:
        logger.error(f"OAuth error: {error}")
        return redirect("/manage?error=oauth_denied")
    
    if not code:
        logger.error("No authorization code received")
        return redirect("/manage?error=no_code")

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    try:
        resp = requests.post(token_url, data=data)
        resp.raise_for_status()
        token_data = resp.json()
        
        logger.info(f"Token response: {token_data}")
        
        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")
        
        if not access_token:
            logger.error(f"No access token received: {token_data}")
            return redirect("/manage?error=no_access_token")
        
        # Fetch channel info using YouTube API v3
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # First, let's try to get channel info
        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "mine": "true",
        }
        
        channel_resp = requests.get(channel_url, headers=headers, params=params)
        channel_resp.raise_for_status()
        channel_data = channel_resp.json()
        
        logger.info(f"Channel response: {channel_data}")
        
        # Check if we got channel data
        items = channel_data.get("items", [])
        if not items:
            logger.error(f"No channel found for user. Full response: {channel_data}")
            # Sometimes the user might not have a YouTube channel yet
            # Let's try to create a basic account entry
            channel_id, channel_title = None, "No Channel Found"
        else:
            channel_info = items[0]
            channel_id = channel_info["id"]
            channel_title = channel_info["snippet"]["title"]
            
            logger.info(f"Found channel: {channel_title} (ID: {channel_id})")

        # Save or update the YouTube account
        account, created = YouTubeAccount.objects.update_or_create(
            user=request.user,
            channel_id=channel_id,
            defaults={
                "channel_title": channel_title,
                "refresh_token": refresh_token,
            }
        )
        
        action = "created" if created else "updated"
        logger.info(f"YouTube account {action} for user {request.user.username}")
        
        return redirect("/manage?success=youtube_connected")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during YouTube OAuth: {e}")
        return redirect("/manage?error=api_error")
    except Exception as e:
        logger.error(f"Unexpected error during YouTube OAuth: {e}")
        return redirect("/manage?error=unexpected")


def disconnectAcc(request, channel_id):
    """Disconnect the YouTube account"""
    try:
        account = YouTubeAccount.objects.get(user=request.user, channel_id=channel_id)
        account_name = account.channel_title or "YouTube Account"
        account.delete()
        messages.success(request, f"Account {account_name}, deleted successfuly")
        return redirect('manage')
    except YouTubeAccount.DoesNotExist:
        messages.error(request, "Account not found")
        return redirect('manage')

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def upload_video_api(request):
    """
    API endpoint to upload video to YouTube channel
    
    Expected form data:
    - channel_id: YouTube channel ID
    - video_file: Video file to upload
    - title: Video title
    - description: Video description
    - tags: Comma-separated tags (optional)
    - privacy_status: 'private', 'public', 'unlisted' (optional, defaults to 'private')
    - category_id: YouTube category ID (optional, defaults to '22' - People & Blogs)
    """
    try:
        # Extract required parameters
        channel_id = request.POST.get('channel_id')
        video_file = request.FILES.get('video_file')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        
        # Optional parameters
        tags = request.POST.get('tags', '')
        privacy_status = request.POST.get('privacy_status', 'private')
        category_id = request.POST.get('category_id', '22')  # Default: People & Blogs
        
        # Validate required fields
        if not channel_id:
            return JsonResponse({"error": "channel_id is required"}, status=400)
        
        if not video_file:
            return JsonResponse({"error": "video_file is required"}, status=400)
            
        if not title:
            return JsonResponse({"error": "title is required"}, status=400)
        
        # Validate privacy status
        valid_privacy_statuses = ['private', 'public', 'unlisted']
        if privacy_status not in valid_privacy_statuses:
            return JsonResponse({
                "error": f"privacy_status must be one of: {', '.join(valid_privacy_statuses)}"
            }, status=400)
        
        # Get YouTube account
        try:
            account = YouTubeAccount.objects.get(user=request.user, channel_id=channel_id)
        except YouTubeAccount.DoesNotExist:
            return JsonResponse({"error": "No YouTube account linked for this channel"}, status=400)

        if not account.refresh_token:
            return JsonResponse({"error": "No refresh token available"}, status=400)

        # Get access token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token",
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error(f"No access token in response: {token_data}")
                return None
                
            # Check if we got a new refresh token and update it
            new_refresh_token = token_data.get("refresh_token")
            if new_refresh_token:
                account.refresh_token = new_refresh_token
                account.save()
                logger.info("Updated refresh token")
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error":f"Error refreshing access token: {e}"})

        creds = {
            "token": access_token, 
            "refresh_token": account.refresh_token,
            "client_id": settings.YOUTUBE_CLIENT_ID, 
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "scopes": settings.YOUTUBE_SCOPES
        }

        credentials = Credentials(**creds)
        youtube = build("youtube", "v3", credentials=credentials)

        # Save uploaded file temporarily
        temp_file_path = None
        try:
            # Create a temporary file path
            temp_file_name = f"temp_upload_{request.user.id}_{channel_id}_{video_file.name}"
            temp_file_path = default_storage.save(temp_file_name, ContentFile(video_file.read()))
            full_temp_path = default_storage.path(temp_file_path)
            
            # Prepare tags list
            tags_list = []
            if tags:
                tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            # Truncate title to 100 characters (YouTube limit)
            truncated_title = title[:100] if len(title) > 100 else title
            
            # Prepare video snippet
            snippet = {
                "title": truncated_title,
                "description": description,
                "categoryId": category_id
            }
            
            # Add tags if provided
            if tags_list:
                snippet["tags"] = tags_list

            # Create media upload object
            media = MediaFileUpload(
                full_temp_path, 
                chunksize=-1, 
                resumable=True,
                mimetype=video_file.content_type or 'video/*'
            )
            
            # Upload video
            request_upload = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": snippet,
                    "status": {"privacyStatus": privacy_status}
                },
                media_body=media
            )
            
            response = request_upload.execute()
            
            logger.info(f"Video uploaded successfully for user {request.user.id}: {response}")
            
            # Return success response with video details
            return JsonResponse({
                "success": True,
                "video_id": response.get('id'),
                "title": response.get('snippet', {}).get('title'),
                "channel_id": response.get('snippet', {}).get('channelId'),
                "privacy_status": response.get('status', {}).get('privacyStatus'),
                "upload_status": response.get('status', {}).get('uploadStatus'),
                "url": f"https://www.youtube.com/watch?v={response.get('id')}" if response.get('id') else None
            })
            
        finally:
            # Clean up temporary file
            if temp_file_path and default_storage.exists(temp_file_path):
                try:
                    default_storage.delete(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary file {temp_file_path}: {cleanup_error}")
        
    except Exception as e:
        logger.error(f"Error uploading video for user {request.user.id}: {str(e)}")
        return JsonResponse({"error": f"Upload failed: {str(e)}"}, status=500)


















# Optional: Add a view to test the connection and refresh channel info
@login_required
def refresh_youtube_info(request):
    """Refresh YouTube channel information for debugging"""
    try:
        account = request.user.youtube_accounts.first()
        if not account or not account.refresh_token:
            return JsonResponse({"error": "No YouTube account or refresh token"}, status=400)
        
        access_token = get_access_token(account)
        if not access_token:
            return JsonResponse({"error": "Could not refresh access token"}, status=400)
        
        headers = {"Authorization": f"Bearer {access_token}"}
        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "mine": "true",
        }
        
        channel_resp = requests.get(channel_url, headers=headers, params=params)
        channel_resp.raise_for_status()
        channel_data = channel_resp.json()
        
        items = channel_data.get("items", [])
        if items:
            channel_info = items[0]
            account.channel_id = channel_info["id"]
            account.channel_title = channel_info["snippet"]["title"]
            account.save()
            
            return JsonResponse({
                "success": True,
                "channel_id": account.channel_id,
                "channel_title": account.channel_title,
                "data": channel_data
            })
        else:
            return JsonResponse({
                "error": "No channel found",
                "response": channel_data
            })
            
    except Exception as e:
        logger.error(f"Error refreshing YouTube info: {e}")
        return JsonResponse({"error": str(e)}, status=500)