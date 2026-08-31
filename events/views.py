from django.db.models import Prefetch, Q
from django.views.generic import DetailView, ListView

from events.models import Bout, Event, Fighter
from favorites.models import Follow

CARD_SEGMENT_LABELS = [
    (Bout.CardSegment.MAIN_CARD, "Main Card"),
    (Bout.CardSegment.PRELIMS, "Preliminary Card"),
    (Bout.CardSegment.EARLY_PRELIMS, "Early Prelims"),
    (Bout.CardSegment.UNKNOWN, "Other Bouts"),
]


class UpcomingEventListView(ListView):
    model = Event
    template_name = "events/upcoming_event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        main_card = (
            Bout.objects.filter(card_segment=Bout.CardSegment.MAIN_CARD)
            .select_related("fighter_one", "fighter_two")
            .order_by("bout_order")
        )
        return (
            Event.objects.filter(status=Event.Status.UPCOMING)
            .order_by("start_time")
            .prefetch_related(Prefetch("bouts", queryset=main_card, to_attr="main_card_bouts"))
        )


class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        all_bouts = Bout.objects.select_related("fighter_one", "fighter_two").order_by("bout_order")
        return Event.objects.prefetch_related(
            Prefetch("bouts", queryset=all_bouts, to_attr="all_bouts")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bouts_by_segment = {}
        for bout in self.object.all_bouts:
            bouts_by_segment.setdefault(bout.card_segment, []).append(bout)
        context["bout_groups"] = [
            (label, bouts_by_segment[segment])
            for segment, label in CARD_SEGMENT_LABELS
            if segment in bouts_by_segment
        ]
        context["is_following"] = (
            self.request.user.is_authenticated
            and Follow.objects.filter(user=self.request.user, event=self.object).exists()
        )
        return context


class FighterDetailView(DetailView):
    model = Fighter
    template_name = "events/fighter_detail.html"
    context_object_name = "fighter"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fighter = self.object
        upcoming_bouts = list(
            Bout.objects.filter(
                Q(fighter_one=fighter) | Q(fighter_two=fighter),
                event__status=Event.Status.UPCOMING,
            )
            .select_related("event", "fighter_one", "fighter_two")
            .order_by("event__start_time")
        )
        for bout in upcoming_bouts:
            bout.opponent = (
                bout.fighter_two if bout.fighter_one_id == fighter.id else bout.fighter_one
            )
        context["upcoming_bouts"] = upcoming_bouts
        return context
