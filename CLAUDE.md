# mma-sport

## Project overview

A customer-facing product that lets fans see information about upcoming MMA
matches (starting with UFC). The initial focus (MVP) is a browsable list of
upcoming events/matches.

- **Audience**: end customers (MMA/UFC fans), not internal/admin users.
- **Stack**: Python 3.12, Django 6.1 (latest stable of each as of project
  start).
- **Frontend**: Django templates (server-rendered), per the MVP default —
  no separate JS frontend framework unless that changes later.
- **Match data source**: [mmaapi.dev](https://mmaapi.dev/) — a third-party
  UFC/MMA API. Match, event, and fighter data should be fetched from this
  API rather than entered manually or scraped, unless that changes later.

## MVP scope

- Upcoming events/matches list (primary feature for v1) — **implemented**,
  see the `events` app.
- Event detail page (full fight card by segment, venue/poster details) —
  **implemented**, see `events.views.EventDetailView`.
- Fighter profile page (`/fighters/<slug>/`) — **implemented**, see
  `events.views.FighterDetailView`. Shows upcoming bouts only — no
  past-fight/result data is synced (the sync command only pulls the
  `/ufc/events/upcoming` endpoint), so there is no "fight history" section.
- Follow/favorite events (`/my-events/`) — **implemented**, see the
  `favorites` app. This is the "favorites" half of the accounts section's
  original "notifications/favorites" promise. Real notification
  *delivery* (email/push) is still explicitly deferred — no working
  `EMAIL_BACKEND` exists (same blocker as password reset). Don't treat
  favorites as "notifications done" — it's a personal follow list only,
  no reminders are sent.

## Post-MVP features

- Search/filter for the upcoming events list (search by event/fighter
  name, filter by weight class, filter by date range) —
  **implemented**, see `events.forms.EventFilterForm` and
  `events.views.UpcomingEventListView`. This was **not** part of the
  original MVP scope above — it's a query-layer enhancement added
  afterward on top of the existing public upcoming-events list. Fully
  anonymous, no login required, consistent with the rest of event
  browsing.
- AI-Powered Match Intelligence — a short, neutral written analysis per
  upcoming bout, generated via a real Claude agentic tool-use loop
  (`client.beta.messages.tool_runner`) that looks up each fighter's
  cached record and current UFC ranking before writing. **Implemented**,
  see the `intelligence` app and `events.models.Ranking`
  (`/ufc/rankings`, synced via `events.management.commands.sync_rankings`
  — the project's first use of that previously-unused endpoint).
  - **Framing, deliberately**: neutral commentary only — no odds, no win
    percentages, no declared winner. `MatchAnalysis` has no "predicted
    winner"/"confidence" field at all, so the schema itself can't drift
    toward betting-style content. Every generated analysis carries an
    on-page disclaimer.
  - **Only `generate_match_intelligence` needs `ANTHROPIC_API_KEY`** —
    unlike `CITO_API_KEY`, it's never read at Django startup, only lazily
    inside `intelligence/services/claude_analyst.py`. Browsing, tests, and
    `runserver` all work fine with zero Anthropic key configured.
  - Cost-controlled via `INTELLIGENCE_WINDOW_DAYS` (near-term bouts only)
    and `INTELLIGENCE_MAX_ANALYSES_PER_RUN` (hard cap per run) — see
    docs/data.md for the real per-analysis cost estimate.
  - `sync_rankings` makes exactly **one** API call per run — the
    `/ufc/rankings` endpoint doesn't actually support `page`-based
    pagination (confirmed live: `page=1` and `page=2` return identical
    data), only `limit`, so a single generous-limit call gets every
    division. Don't reintroduce a pagination loop for it without
    re-confirming that's changed upstream.

## User accounts

- **Implemented** — see the `accounts` app (signup/login/logout only).
  Uses Django's plain built-in `auth.User` model, username-based login
  (not email, not a custom user model).
- Accounts are **optional**: browsing upcoming matches must work fully for
  anonymous/unauthenticated users — no browsing view has `login_required`.
  The `favorites` app (follow/unfollow, "My Events") is the first and
  only place `login_required` gating exists in the project.
- Accounts unlock extras such as favorites (implemented) — don't gate
  core browsing behind login.
- Password reset is **explicitly out of scope for now**: the project has
  no working email sending configured (`EMAIL_BACKEND` isn't set at all;
  a non-standard `MAILERS` dict exists but nothing in Django reads it).
  Add real email delivery (e.g. SendGrid) before building password reset
  or real event-reminder notifications.

## Documentation

Detailed guidance lives in `docs/` — read the relevant file before working
in that area:

- [docs/data.md](docs/data.md) — mmaapi.dev integration, caching strategy,
  timezone handling, env vars.
- [docs/design.md](docs/design.md) — visual identity (colors, typography),
  responsive design, accessibility target.
- [docs/dev-practices.md](docs/dev-practices.md) — testing, formatting,
  deployment, commands, project layout.

## Conventions

_No project-specific conventions established yet beyond the above — this
section should be filled in as the codebase takes shape (naming, etc.)._
