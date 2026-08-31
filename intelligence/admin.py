from django.contrib import admin

from intelligence.models import MatchAnalysis


@admin.register(MatchAnalysis)
class MatchAnalysisAdmin(admin.ModelAdmin):
    list_display = ("bout", "model_used", "generated_at")
    search_fields = ("bout__fighter_one__name", "bout__fighter_two__name")
