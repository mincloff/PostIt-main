from django.db import models
from django.contrib.auth.models import User

class YouTubeAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="youtube_accounts")
    channel_id = models.CharField(max_length=255, blank=True, null=True)
    channel_title = models.CharField(max_length=255, blank=True, null=True)
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'channel_id')

    def __str__(self):
        return f"{self.user.username} - {self.channel_title or 'YouTube Account'}"
