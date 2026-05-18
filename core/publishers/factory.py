from .facebook import FacebookPublisher
from .instagram import InstagramPublisher
from .linkedin import LinkedInPublisher
from .x_twitter import XTwitterPublisher
from .threads import ThreadsPublisher
from .pinterest import PinterestPublisher
from .youtube import YouTubePublisher
from .tiktok import TikTokPublisher
from .reddit import RedditPublisher
from .blogger import BloggerPublisher

PUBLISHER_MAP = {
    'facebook': FacebookPublisher,
    'instagram': InstagramPublisher,
    'linkedin': LinkedInPublisher,
    'x': XTwitterPublisher,
    'threads': ThreadsPublisher,
    'pinterest': PinterestPublisher,
    'youtube': YouTubePublisher,
    'tiktok': TikTokPublisher,
    'reddit': RedditPublisher,
    'blogger': BloggerPublisher,
}

def get_publisher(platform_name, integration_object):
    """
    Given a platform name and an integration object, returns the initialized Strategy class instance.
    """
    publisher_class = PUBLISHER_MAP.get(platform_name.lower())
    if not publisher_class:
        raise ValueError(f"Unsupported platform: {platform_name}")
    return publisher_class(integration_object)
