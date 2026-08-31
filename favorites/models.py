from django.conf import settings
from django.db import models


class Follow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follows"
    )
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "event"], name="unique_follow_per_user_event")
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} follows {self.event}"
