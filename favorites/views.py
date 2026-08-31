from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from events.models import Event
from favorites.models import Follow


class FollowToggleView(LoginRequiredMixin, View):
    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        follow, created = Follow.objects.get_or_create(user=request.user, event=event)
        if not created:
            follow.delete()
        return redirect("events:event_detail", slug=event.slug)


class MyEventsView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "favorites/my_events.html"
    context_object_name = "events"

    def get_queryset(self):
        return Event.objects.filter(
            followers__user=self.request.user, status=Event.Status.UPCOMING
        ).order_by("start_time")
