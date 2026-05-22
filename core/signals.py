import uuid
# pyrefly: ignore [missing-import]
from django.db.models.signals import post_save
# pyrefly: ignore [missing-import]
from django.dispatch import receiver
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
from .models import Organization, UserProfile, TokenWallet, PlatformIntegration
# pyrefly: ignore [missing-import]
from allauth.socialaccount.signals import social_account_added, social_account_updated
# pyrefly: ignore [missing-import]
from allauth.socialaccount.models import SocialToken

@receiver(post_save, sender=User)
def create_user_infrastructure(sender, instance, created, **kwargs):
    if created:
        # 1. Build their default Organization
        org = Organization.objects.create(
            name=f"{instance.username}'s Workspace",
            owner=instance
        )
        
        # --- NEW: Generate a random 8-character referral code ---
        random_code = str(uuid.uuid4()).replace('-', '')[:8].upper()
        
        # 2. Build their Profile and link it
        UserProfile.objects.create(
            user=instance,
            organization=org,
            referral_code=random_code # <-- Pass the unique code here
        )
        
        # 3. Build their Wallet and give them a Welcome Bonus
        TokenWallet.objects.create(
            organization=org,
            balance=10000 
        )

import requests
# pyrefly: ignore [missing-import]
from django.dispatch import receiver
# pyrefly: ignore [missing-import]
from allauth.socialaccount.signals import social_account_added, social_account_updated
# pyrefly: ignore [missing-import]
from allauth.socialaccount.models import SocialToken
from .models import PlatformIntegration

@receiver(social_account_added)
@receiver(social_account_updated)
def capture_social_token(sender, request, sociallogin, **kwargs):
    user = sociallogin.account.user
    provider = sociallogin.account.provider
    
    token_obj = SocialToken.objects.filter(account=sociallogin.account).first()
    if not token_obj:
        return
        
    org = user.owned_organizations.first()
    if not org and hasattr(user, 'profile'):
        org = user.profile.organization
        
    if not org:
        print("WARNING: No organization found.")
        return

    # --- UNIVERSAL TOKEN CATCHER ---
    # Map Allauth provider names to our internal platform names
    PROVIDER_MAP = {
        'google': ['youtube', 'blogger'], 
        'facebook': ['facebook', 'instagram'], 
        'linkedin_oauth2': ['linkedin'],
        'twitter_oauth2': ['x'],
        'tiktok': ['tiktok'],
        'wordpress': ['wordpress'],
        'tumblr': ['tumblr'],
        'discord': ['discord'],
    }
    
    platforms = PROVIDER_MAP.get(provider, [])
    
    for platform in platforms:
        account_id = None
        # Platform specific logic for fetching IDs
        if provider == 'google' and platform == 'blogger':
            try:
                headers = {"Authorization": f"Bearer {token_obj.token}"}
                resp = requests.get("https://www.googleapis.com/blogger/v3/users/self/blogs", headers=headers)
                if resp.status_code == 200:
                    blogs = resp.json().get('items', [])
                    if blogs:
                        account_id = blogs[0]['id']
            except Exception as e:
                print(f"Failed to fetch Blogger ID: {e}")
                
        # Save the token
        PlatformIntegration.objects.update_or_create(
            organization=org,
            platform=platform,
            defaults={
                'account_id': account_id,
                'access_token': token_obj.token,
                'is_active': True
            }
        )
        print(f"SUCCESS: Saved token for {platform}")