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
`MMAAPI_API_KEY`.

- Run the dev server: `python manage.py runserver`
- Apply migrations: `python manage.py migrate`
- Sync events/bouts from the Cito API: `python manage.py sync_upcoming_events`
  (add `--dry-run` to preview without writing — see docs/data.md for the
  API call budget this respects)
- Run tests: `pytest`
- Format: `black .`
- Lint: `ruff check .`

## Project/app layout

- `mma_sport/` — Django project package (settings, root urls, wsgi/asgi).
- `events/` — the app for cached event/bout/fighter data and the
  upcoming-events list, event-detail-page, and fighter-profile-page
  features:
  - `models.py` — `Event`, `Bout`, `Fighter`.
  - `services/cito_client.py` — thin, Django-independent wrapper around
    the Cito API (mmaapi.dev).
  - `management/commands/sync_upcoming_events.py` — the sync command.
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
- `templates/` — project-level templates (`base.html`, `events/*.html`,
  `accounts/*.html`, `favorites/*.html`).
- `static/` — project-level static assets (`css/base.css`, `js/timezone.js`).
- `conftest.py` (repo root) — shared pytest fixtures (`make_user`,
  `make_fighter`, `make_event`, `make_bout`) used across all apps' test
  suites. Promoted here (rather than living in per-app `tests/conftest.py`
  files) once a feature (`favorites`) first needed fixtures from two
  different apps' domains at once — add new shared fixtures here, not to
  a per-app conftest, unless a fixture is genuinely local to one app.
- New features should generally follow this pattern: a new Django app per
  feature area, with its own `models.py`/`views.py`/`tests/`, templates
  under `templates/<app_name>/`.
