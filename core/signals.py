import uuid # <-- NEW: Import Python's built-in unique ID generator
# pyrefly: ignore [missing-import]
from django.db.models.signals import post_save
# pyrefly: ignore [missing-import]
from django.dispatch import receiver
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
from .models import Organization, UserProfile, TokenWallet

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