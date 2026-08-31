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
  `GET /ufc/events/{eventIdOrSlug}/bouts`, `GET /ufc/rankings` (see below —
  **not** paginated the way the events endpoint is). Also available but
  not yet used: `GET /ufc/events/{eventIdOrSlug}`, `GET /ufc/fighters/{slug}`,
  `GET /ufc/search`.
- **Free tier: 500 calls/month.** This is a hard constraint — never call
  the API per page view; always go through the cached local models and
  the sync commands above.
- Exact response field names aren't fully documented publicly, so
  `sync_upcoming_events.py`/`sync_rankings.py` parse defensively (try a
  few likely key variants per field) and store the full raw payload in
  each model's `raw_data` JSONField as a fallback/debugging aid.

### `GET /ufc/rankings`

Confirmed live (2026-08-31): **`page` is silently ignored** —
`page=1` and `page=2` return byte-identical data — only `limit` controls
response size. `sync_rankings.py` therefore makes exactly **one** call
per run with a generous `limit` (250; the real dataset was 176 rows
across 11 divisions at the time of writing) rather than looping — do not
reintroduce a pagination loop without re-confirming this has changed
upstream.

Real response shape (verified via a live call, not guessed):
```json
{"success": true, "data": [
  {"division": "Bantamweight", "rank": null, "rankText": "C",
   "fighterSlug": "petr-yan", "isChampion": true, "championStatus": "champion",
   "fighter": {"nickname": "No Mercy", "record": {"text": "20-5-0 (W-L-D)"},
               "country": "Russia", "headshotUrl": "..."}},
  {"division": "Bantamweight", "rank": 1, "rankText": "1",
   "fighterSlug": "merab-dvalishvili", "isChampion": false, "...": "..."}
]}
```
`rank` is `null` for the champion of each division (`isChampion`/`rankText: "C"`
carry that signal instead) — `events.models.Ranking.rank` is nullable
for exactly this reason, and the sync's upsert keys on `(fighter, division)`,
not `rank`. Ranking lookups (in `intelligence/services/claude_analyst.py`)
go by fighter slug, not by matching `division` against `Bout.weight_class` —
that field has unreliable "Title"-suffixed values (e.g. "Featherweight Title")
that don't cleanly match the plain division strings here.

## AI Match Intelligence (Anthropic/Claude)

`intelligence/services/claude_analyst.py` generates a short, neutral
analysis per bout via `client.beta.messages.tool_runner(...)` — a real
agentic loop, not a single pre-stuffed-context call (see CLAUDE.md for
why that trade-off was made deliberately). Two tools
(`get_fighter_profile`, `get_fighter_ranking`) read from the local
`Fighter`/`Ranking` tables Claude decides to call itself.

- **Model**: `INTELLIGENCE_MODEL` (default `claude-opus-5`).
- **Cost controls**: `INTELLIGENCE_WINDOW_DAYS` (default 7 — only bouts
  on events starting within this window are eligible) and
  `INTELLIGENCE_MAX_ANALYSES_PER_RUN` (default 10 — hard cap per command
  run, the primary spend guardrail regardless of how many tool-call
  round-trips or output tokens any single analysis uses).
- **Rough cost estimate** (not a guarantee): at Claude Opus 5 pricing
  (~$5/$25 per MTok), a 2-tool-call analysis (~1.5K input tokens across
  turns, ~300 output) costs roughly $0.01–0.02. At the default cap run
  daily, that's ~$3–6/month worst case.
- **`ANTHROPIC_API_KEY`** is only read lazily inside `claude_analyst.py`,
  never at Django startup — browsing, tests, and `runserver` all work
  with zero Anthropic key configured; only running
  `generate_match_intelligence` requires one.
- Already-analyzed bouts are skipped on subsequent runs unless `--force`
  is passed.
