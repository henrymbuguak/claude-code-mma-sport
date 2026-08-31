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
