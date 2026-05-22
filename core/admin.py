# pyrefly: ignore [missing-import]
from django.contrib import admin
from .models import Organization, PlatformIntegration, SocialPost, TokenWallet, TransactionLog

# Register the basic models
admin.site.register(Organization)
admin.site.register(SocialPost)
admin.site.register(TokenWallet)
admin.site.register(TransactionLog)

# Register Platform Integration with a nice layout
@admin.register(PlatformIntegration)
class PlatformIntegrationAdmin(admin.ModelAdmin):
    list_display = ('organization', 'platform', 'account_id', 'is_active')
    list_filter = ('platform', 'is_active')