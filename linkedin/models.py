from django.db import models
from django.contrib.auth.models import User

class LinkedInAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linkedin_accounts')
    linkedin_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True)
    access_token = models.TextField()
    connected_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user', 'linkedin_id')
    
    def __str__(self):
        return f"{self.name} ({self.linkedin_id})"