# Dev practices

- **Testing**: pytest (with `pytest-django`), not Django's built-in
  `unittest`-style `TestCase`.
- **Formatting/linting**: Black for formatting, Ruff for linting.
- **Deployment target**: Heroku. Keep this in mind for config choices
  (e.g. `Procfile`, `django-environ` or similar for env vars, Postgres as
  the production DB via Heroku's addon, static file serving via
  WhiteNoise).

## Commands

Set up once: `python -m venv .venv`, activate it, then
`pip install -r requirements-dev.txt`. Copy `.env.example` to `.env` and
fill in `SECRET_KEY`, `DATABASE_URL` (Postgres, local and prod), and
`MMAAPI_API_KEY`. `ANTHROPIC_API_KEY` is only needed if you plan to run
`generate_match_intelligence` — everything else works without it.

- Run the dev server: `python manage.py runserver`
- Apply migrations: `python manage.py migrate`
- Sync events/bouts from the Cito API: `python manage.py sync_upcoming_events`
  (add `--dry-run` to preview without writing — see docs/data.md for the
  API call budget this respects)
- Sync UFC rankings: `python manage.py sync_rankings` (one API call —
  see docs/data.md)
- Generate AI match analyses: `python manage.py generate_match_intelligence`
  (add `--dry-run` to preview, `--force` to regenerate existing ones;
  requires `ANTHROPIC_API_KEY` — see docs/data.md for cost controls)
- Run tests: `pytest`
- Format: `black .`
- Lint: `ruff check .`

## Project/app layout

- `mma_sport/` — Django project package (settings, root urls, wsgi/asgi).
- `events/` — the app for cached event/bout/fighter data and the
  upcoming-events list, event-detail-page, and fighter-profile-page
  features:
  - `models.py` — `Event`, `Bout`, `Fighter`, `Ranking`.
  - `forms.py` — `EventFilterForm` (search/filter for the upcoming
    events list: `q`, `weight_class`, `date_from`, `date_to`; the
    project's first custom form — everything before it used Django's
    built-ins like `UserCreationForm`).
  - `services/cito_client.py` — thin, Django-independent wrapper around
    the Cito API (mmaapi.dev).
  - `management/commands/sync_upcoming_events.py` — the events/bouts sync
    command; `sync_rankings.py` — the rankings sync (single call, no
    pagination — see CLAUDE.md for why).
  - `views.py`, `urls.py` — the upcoming events list (`/`), event detail
    (`/events/<slug>/`), and fighter profile (`/fighters/<slug>/`) pages.
  - `tests/` — pytest-django tests.
- `accounts/` — the app for optional user accounts (signup/login/logout),
  built on Django's built-in `auth.User` model (no models of its own):
  - `views.py` — `SignupView` (uses `UserCreationForm`, logs the user in
    on success); login/logout use `django.contrib.auth.views.LoginView`/
    `LogoutView` directly from `urls.py`.
  - `urls.py` — `/accounts/signup/`, `/accounts/login/`,
    `/accounts/logout/` only (no password-reset routes — out of scope,
    see CLAUDE.md).
  - `tests/`
- `favorites/` — the app for the follow/favorites feature. The first
  (and so far only) place `login_required` gating is used, and the first
  model needing both a `User` FK and an `events.Event` FK together:
  - `models.py` — `Follow` (`user` + `event`, unique per pair).
  - `views.py`, `urls.py` — `FollowToggleView` (POST-only toggle at
    `/events/<slug>/follow/`) and `MyEventsView` (`/my-events/`, upcoming
    follows only).
  - `tests/`
  - `events/views.py`'s `EventDetailView` has one deliberate read-only
    import from this app (`favorites.models.Follow`, to show
    Follow/Unfollow state) — the only cross-app dependency in that
    direction; everything else in `favorites` depends on `events`, not
    the reverse.
- `intelligence/` — the app for AI-generated match analyses. Owns the
  Anthropic integration and the agentic tool-use loop — a distinct
  external dependency and concern from `events`' synced UFC facts:
  - `models.py` — `MatchAnalysis` (`OneToOneField` to `events.Bout`; no
    "predicted winner"/"confidence" field, deliberately).
  - `services/claude_analyst.py` — the `@beta_tool`-decorated lookup
    tools (`get_fighter_profile`, `get_fighter_ranking`) and
    `generate_analysis(bout)`, which drives
    `client.beta.messages.tool_runner(...)`.
  - `management/commands/generate_match_intelligence.py` — budget-aware
    generation (`INTELLIGENCE_WINDOW_DAYS`, `INTELLIGENCE_MAX_ANALYSES_PER_RUN`),
    `--dry-run`, `--force`.
  - `tests/` — service-level tests mock the Anthropic client itself;
    command tests mock `generate_analysis` entirely, so neither ever
    makes a real API call.
  - **Zero cross-app import needed in `events/views.py`** — unlike
    `favorites`' one `Follow` import, `MatchAnalysis` being a
    `OneToOneField` means `events/views.py` only needs
    `.select_related("match_analysis")`; `{% if bout.match_analysis %}`
    in the template handles the rest via Django's normal reverse-OneToOne
    + template silent-failure behavior. See CLAUDE.md for why.
- `templates/` — project-level templates (`base.html`, `events/*.html`,
  `accounts/*.html`, `favorites/*.html`).
- `static/` — project-level static assets (`css/base.css`, `js/timezone.js`).
- `conftest.py` (repo root) — shared pytest fixtures (`make_user`,
  `make_fighter`, `make_event`, `make_bout`, `make_ranking`,
  `make_match_analysis`) used across all apps' test suites. Promoted here
  (rather than living in per-app `tests/conftest.py` files) once a
  feature (`favorites`) first needed fixtures from two different apps'
  domains at once — add new shared fixtures here, not to a per-app
  conftest, unless a fixture is genuinely local to one app.
- New features should generally follow this pattern: a new Django app per
  feature area, with its own `models.py`/`views.py`/`tests/`, templates
  under `templates/<app_name>/`.
