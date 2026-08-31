from django.db import models


class MatchAnalysis(models.Model):
    bout = models.OneToOneField(
        "events.Bout", on_delete=models.CASCADE, related_name="match_analysis"
    )
    analysis_text = models.TextField()
    model_used = models.CharField(max_length=64)
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis for {self.bout}"
