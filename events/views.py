from django.db.models import Prefetch, Q
from django.views.generic import DetailView, ListView

from events.forms import EventFilterForm
from events.models import Bout, Event, Fighter
from favorites.models import Follow

CARD_SEGMENT_LABELS = [
    (Bout.CardSegment.MAIN_CARD, "Main Card"),
    (Bout.CardSegment.PRELIMS, "Preliminary Card"),
    (Bout.CardSegment.EARLY_PRELIMS, "Early Prelims"),
    (Bout.CardSegment.UNKNOWN, "Other Bouts"),
]

FILTER_PARAM_NAMES = ["q", "weight_class", "date_from", "date_to"]


class UpcomingEventListView(ListView):
    model = Event
    template_name = "events/upcoming_event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        self.filter_form = EventFilterForm(self.request.GET or None)
        self.filters_active = any(self.request.GET.get(name) for name in FILTER_PARAM_NAMES)

        cleaned = {}
        if self.filter_form.is_bound:
            self.filter_form.is_valid()
            cleaned = self.filter_form.cleaned_data

        queryset = Event.objects.filter(status=Event.Status.UPCOMING).order_by("start_time")

        q = cleaned.get("q")
        weight_class = cleaned.get("weight_class")
        joins_bouts = False
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(bouts__fighter_one__name__icontains=q)
                | Q(bouts__fighter_two__name__icontains=q)
            )
            joins_bouts = True
        if weight_class:
            queryset = queryset.filter(bouts__weight_class=weight_class)
            joins_bouts = True
        if cleaned.get("date_from"):
            queryset = queryset.filter(start_time__date__gte=cleaned["date_from"])
        if cleaned.get("date_to"):
            queryset = queryset.filter(start_time__date__lte=cleaned["date_to"])
        if joins_bouts:
            queryset = queryset.distinct()

        main_card = (
            Bout.objects.filter(card_segment=Bout.CardSegment.MAIN_CARD)
            .select_related("fighter_one", "fighter_two")
            .order_by("bout_order")
        )
        return queryset.prefetch_related(
            Prefetch("bouts", queryset=main_card, to_attr="main_card_bouts")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["filters_active"] = self.filters_active
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        all_bouts = Bout.objects.select_related(
            "fighter_one", "fighter_two", "match_analysis"
        ).order_by("bout_order")
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
