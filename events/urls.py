from django.urls import path

from events.views import EventDetailView, FighterDetailView, UpcomingEventListView

app_name = "events"

urlpatterns = [
    path("", UpcomingEventListView.as_view(), name="upcoming_list"),
    path("events/<slug:slug>/", EventDetailView.as_view(), name="event_detail"),
    path("fighters/<slug:slug>/", FighterDetailView.as_view(), name="fighter_detail"),
]
