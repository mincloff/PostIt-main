from django.db import models
from django.contrib.auth.models import User

class ThreadsAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'account_id')
    
    def __str__(self):
        return f"@{self.username}"
