# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
import uuid

class Organization(models.Model):
    """Handles the Multi-Tenant/Reseller structure"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_organizations')
    is_reseller = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Reseller: {self.is_reseller})"

class UserProfile(models.Model):
    """Links a user to their reseller/organization"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

class TokenWallet(models.Model):
    """The Prepaid Wallet System"""
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='wallet')
    balance = models.IntegerField(default=0)
    total_spent = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def has_sufficient_tokens(self, cost):
        """The Pre-Check Vault Logic"""
        return self.balance >= cost

    def deduct_tokens(self, cost):
        if self.has_sufficient_tokens(cost):
            self.balance -= cost
            self.total_spent += cost
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.organization.name} Wallet - Balance: {self.balance}"

class TransactionLog(models.Model):
    """Ledger Transparency for the Dashboard"""
    wallet = models.ForeignKey(TokenWallet, on_delete=models.CASCADE, related_name='logs')
    action_type = models.CharField(max_length=100) # e.g., 'AI_TEXT_GEN', 'TOP_UP'
    tokens_deducted = models.IntegerField()
    status = models.CharField(max_length=50, choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} ({self.tokens_deducted} tokens) - {self.status}"

class SocialPost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='posts')
    original_prompt = models.TextField()
    generated_text = models.TextField()
    target_platforms = models.CharField(max_length=255)

    image_url = models.URLField(max_length=500, blank=True, null=True)
    image_file = models.FileField(upload_to='uploads/images/', blank=True, null=True)
    video_file = models.FileField(upload_to='uploads/videos/', blank=True, null=True)
    
    # --- NEW: Scheduling Fields ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False) # We will keep this for backwards compatibility for now

    def __str__(self):
        return f"{self.get_status_display()} - {self.created_at.strftime('%Y-%m-%d')}"
class PlatformIntegration(models.Model):
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('x', 'X (Twitter)'),
        ('threads', 'Threads'),
        ('pinterest', 'Pinterest'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('reddit', 'Reddit'),
        ('blogger', 'Blogger'),
        ('wordpress', 'WordPress'),
        ('tumblr', 'Tumblr'),
        ('discord', 'Discord'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='integrations')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    access_token = models.TextField(help_text="The secure API access token")
    account_id = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., Facebook Page ID or Instagram Business ID")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'platform') # One entry per platform per organization

    def __str__(self):
        return f"{self.organization.name} - {self.get_platform_display()}"