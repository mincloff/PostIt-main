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

@receiver(social_account_added)
@receiver(social_account_updated)
def capture_social_token(sender, request, sociallogin, **kwargs):
    user = sociallogin.account.user
    provider = sociallogin.account.provider
    
    # Map the Allauth provider to our internal platform choices
    platforms_to_update = []
    if provider == 'google':
        platforms_to_update = ['blogger', 'youtube']
    elif provider == 'facebook':
        platforms_to_update = ['facebook', 'instagram']
        
    # Get the token that Allauth just captured
    token_obj = SocialToken.objects.filter(account=sociallogin.account).first()
    if not token_obj:
        return
        
    # Get the user's organization (assuming the first one for now)
    # Get the user's organization (Check owned first, then profile)
    org = user.owned_organizations.first()
    
    if not org and hasattr(user, 'profile'):
        org = user.profile.organization
        
    if not org:
        print("WARNING: Could not find an organization for this user.")
        return
        
    # Save the token into our master API vault
    for platform in platforms_to_update:
        PlatformIntegration.objects.update_or_create(
            organization=org,
            platform=platform,
            defaults={
                'account_id': sociallogin.account.uid,
                'access_token': token_obj.token
            }
        )