from celery import shared_task
from .models import SocialPost
from core.publishers import get_publisher
import inspect
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_universal_publish(post_id):
    try:
        post = SocialPost.objects.get(id=post_id)
    except SocialPost.DoesNotExist:
        logger.error(f"Post {post_id} not found.")
        return "Post not found."

    org = post.organization
    platforms = [p.strip() for p in post.target_platforms.split(',') if p.strip()]
    
    if not platforms:
        logger.warning(f"No platforms selected for post {post_id}")
        return "No platforms selected."

    success_count = 0
    fail_count = 0
    failed_platforms = []

    for platform in platforms:
        platform = platform.lower()
        integration = org.integrations.filter(platform=platform, is_active=True).first()
        if not integration:
            msg = f"No active integration found."
            logger.error(f"Failed to publish post {post_id} to {platform}: {msg}")
            failed_platforms.append(f"{platform.capitalize()}: {msg}")
            fail_count += 1
            continue
            
        try:
            publisher = get_publisher(platform, integration)
        except ValueError:
            msg = "Publisher not implemented."
            logger.error(f"Failed to publish post {post_id} to {platform}: {msg}")
            failed_platforms.append(f"{platform.capitalize()}: {msg}")
            fail_count += 1
            continue

        image_path = post.image_file.path if post.image_file else None
        video_path = post.video_file.path if post.video_file else None

        kwargs = {'image_url': post.image_url}
        if image_path: kwargs['image_path'] = image_path
        if video_path: kwargs['video_path'] = video_path
        
        sig = inspect.signature(publisher.publish)
        valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())}

        try:
            success, response = publisher.publish(post.generated_text, **valid_kwargs)
            if success:
                logger.info(f"Successfully published post {post_id} to {platform}")
                success_count += 1
            else:
                logger.error(f"Failed to publish post {post_id} to {platform}: {response}")
                failed_platforms.append(f"{platform.capitalize()}: {response}")
                fail_count += 1
        except Exception as e:
            logger.error(f"System error publishing post {post_id} to {platform}: {str(e)}")
            failed_platforms.append(f"{platform.capitalize()}: System error ({str(e)})")
            fail_count += 1

    if success_count > 0 and fail_count == 0:
        post.status = 'published'
        post.error_message = None
    elif success_count > 0:
        post.status = 'published' # Partially published
        post.error_message = "\n".join(failed_platforms)
    else:
        post.status = 'failed'
        post.error_message = "\n".join(failed_platforms)
        
    post.save()
    
    return f"Publishing complete. Successes: {success_count}, Failures: {fail_count}"

@shared_task
def sweep_scheduled_posts():
    due_posts = SocialPost.objects.filter(
        status='scheduled',
        scheduled_time__lte=timezone.now()
    )
    
    count = 0
    for post in due_posts:
        post.status = 'processing'
        post.save()
        process_universal_publish.delay(post.id)
        count += 1
        
    return f"Triggered {count} scheduled posts."
