# Data handling

- mmaapi.dev is the source of truth, but responses should be **cached into
  local Django models** rather than fetched live on every request (faster
  pages, less coupling to third-party uptime/rate limits, enables
  search/filter).
- This implies a sync/import mechanism to periodically refresh local data
  from the API — implemented as
  `events/management/commands/sync_upcoming_events.py`, run daily via
  Heroku Scheduler in production (~200 calls/month, well under the free
  tier's 500/month cap). It fetches `/ufc/events/upcoming`, then only
  fetches `/bouts` for an event if it has none cached yet or starts within
  `CITO_SYNC_BOUTS_REFRESH_WINDOW_DAYS` (default 14) — see the command's
  docstring/code for the exact budget logic.
- API keys/credentials for mmaapi.dev must be kept out of source control
  (env vars / `.env`, not committed).
- Match/event times: store in **UTC** in the database, convert to each
  viewer's local timezone for display (global audience — don't hardcode
  US Eastern/Pacific).
- Expected env vars (names may evolve as the project is scaffolded):
  `MMAAPI_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, `DJANGO_DEBUG`,
  `ALLOWED_HOSTS`.

## API reference

[mmaapi.dev](https://mmaapi.dev/) (branded "Cito API") — third-party
UFC/MMA API. Full docs: https://citoapi.com/docs/api/ufc.

- Base URL: `https://api.citoapi.com/api/v1`
- Auth: header `x-api-key: YOUR_API_KEY` on every request.
- Endpoints used: `GET /ufc/events/upcoming` (paginated via `page`/`limit`),
  `GET /ufc/events/{eventIdOrSlug}/bouts`. Also available but not yet used:
  `GET /ufc/events/{eventIdOrSlug}`, `GET /ufc/fighters/{slug}`,
  `GET /ufc/rankings`, `GET /ufc/search`.
- **Free tier: 500 calls/month.** This is a hard constraint — never call
  the API per page view; always go through the cached local models and
  the sync command above.
- Exact response field names aren't fully documented publicly, so
  `sync_upcoming_events.py` parses defensively (tries a few likely key
  variants per field) and stores the full raw payload in each model's
  `raw_data` JSONField as a fallback/debugging aid.
