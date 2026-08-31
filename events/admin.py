from django.contrib import admin

from events.models import Bout, Event, Fighter


@admin.register(Fighter)
class FighterAdmin(admin.ModelAdmin):
    list_display = ("name", "nickname", "record", "country", "updated_at")
    search_fields = ("name", "nickname", "slug")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "status", "venue_name", "bouts_synced_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")


@admin.register(Bout)
class BoutAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "event",
        "weight_class",
        "card_segment",
        "bout_order",
        "is_title_fight",
    )
    list_filter = ("card_segment", "is_title_fight")
