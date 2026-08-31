from django.contrib import admin

from favorites.models import Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "event__name")
