from django.db import models
from django.contrib.auth.models import User

class XAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='x_accounts')
    x_id = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'x_id')
    
    def __str__(self):
        return f"@{self.username} - {self.user.username}"