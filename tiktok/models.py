# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User

class TikTokAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tiktok_accounts')
    tiktok_id = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    avatar_url = models.URLField(blank=True, null=True)
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'tiktok_id')
    
    def __str__(self):
        return f"@{self.username} - {self.user.username}"