import requests
from django.conf import settings


class CitoAPIError(Exception):
    pass


class CitoClient:
    def __init__(self, base_url=None, api_key=None, timeout=10):
        self.base_url = base_url or settings.CITO_API_BASE_URL
        self.api_key = api_key or settings.CITO_API_KEY
        self.timeout = timeout
        self.calls_made = 0

    def _get(self, path, params=None):
        response = requests.get(
            f"{self.base_url}{path}",
            headers={"x-api-key": self.api_key},
            params=params,
            timeout=self.timeout,
        )
        self.calls_made += 1
        if not response.ok:
            raise CitoAPIError(f"{response.status_code} on {path}: {response.text[:200]}")
        return response.json()

    def get_upcoming_events(self, page=1, limit=50):
        return self._get("/ufc/events/upcoming", {"page": page, "limit": limit})

    def get_event_bouts(self, event_id_or_slug):
        return self._get(f"/ufc/events/{event_id_or_slug}/bouts")
