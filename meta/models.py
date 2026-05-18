from django.db import models
from django.contrib.auth.models import User


class MetaAccount(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=200)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)  # Added username field
    access_token = models.TextField()
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Added update timestamp

    class Meta:
        unique_together = ('user', 'account_id')

    def __str__(self):
        display_name = self.account_name or self.username or f"Account {self.account_id}"
        return f"{self.user.username} - {display_name}"
    
    @property
    def is_token_expired(self):
        """Check if the access token has expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def display_name(self):
        """Get the best available display name"""
        return self.account_name or self.username or f"Account {self.account_id}"