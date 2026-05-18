# pyrefly: ignore [missing-import]
from django.contrib import admin
from .models import Organization, UserProfile, TokenWallet, TransactionLog

admin.site.register(Organization)
admin.site.register(UserProfile)
admin.site.register(TokenWallet)
admin.site.register(TransactionLog)

# Register your models here.
