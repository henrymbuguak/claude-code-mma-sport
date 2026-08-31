from django.db import models


class Fighter(models.Model):
    cito_id = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    nickname = models.CharField(max_length=255, blank=True)
    record = models.CharField(max_length=32, blank=True)
    country = models.CharField(max_length=100, blank=True)
    photo_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Ranking(models.Model):
    fighter = models.ForeignKey(Fighter, on_delete=models.CASCADE, related_name="rankings")
    division = models.CharField(max_length=100)
    rank = models.PositiveSmallIntegerField(null=True, blank=True)
    rank_text = models.CharField(max_length=16, blank=True)
    is_champion = models.BooleanField(default=False)
    raw_data = models.JSONField(blank=True, default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fighter", "division"], name="unique_ranking_per_fighter_division"
            )
        ]
        ordering = ["division", "rank"]

    def __str__(self):
        return f"{self.fighter} — {self.division} ({self.rank_text or self.rank})"


class Event(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        LIVE = "live", "Live"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    cito_id = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    venue_name = models.CharField(max_length=255, blank=True)
    venue_city = models.CharField(max_length=255, blank=True)
    venue_country = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPCOMING)
    poster_image_url = models.URLField(blank=True)
    raw_data = models.JSONField(blank=True, default=dict)
    bouts_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [models.Index(fields=["status", "start_time"])]

    def __str__(self):
        return self.name


class Bout(models.Model):
    class CardSegment(models.TextChoices):
        MAIN_CARD = "main_card", "Main card"
        PRELIMS = "prelims", "Prelims"
        EARLY_PRELIMS = "early_prelims", "Early prelims"
        UNKNOWN = "unknown", "Unknown"

    cito_id = models.CharField(max_length=64, unique=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bouts")
    fighter_one = models.ForeignKey(Fighter, on_delete=models.PROTECT, related_name="+")
    fighter_two = models.ForeignKey(Fighter, on_delete=models.PROTECT, related_name="+")
    weight_class = models.CharField(max_length=100, blank=True)
    card_segment = models.CharField(
        max_length=16, choices=CardSegment.choices, default=CardSegment.UNKNOWN
    )
    bout_order = models.PositiveSmallIntegerField(default=0)
    is_title_fight = models.BooleanField(default=False)
    is_main_event = models.BooleanField(default=False)
    raw_data = models.JSONField(blank=True, default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event", "bout_order"]

    def __str__(self):
        return f"{self.fighter_one} vs {self.fighter_two}"
