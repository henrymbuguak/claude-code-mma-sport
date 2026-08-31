from django.urls import path

from favorites.views import FollowToggleView, MyEventsView

app_name = "favorites"

urlpatterns = [
    path("my-events/", MyEventsView.as_view(), name="my_events"),
    path("events/<slug:slug>/follow/", FollowToggleView.as_view(), name="follow_toggle"),
]
