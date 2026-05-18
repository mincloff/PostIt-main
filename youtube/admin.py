from django.contrib import admin

from .models import YouTubeAccount

@admin.register(YouTubeAccount)
class YouTubeAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel_title', 'channel_id', 'created_at')
    search_fields = ('user__username', 'channel_title', 'channel_id')
    readonly_fields = ('created_at',)
