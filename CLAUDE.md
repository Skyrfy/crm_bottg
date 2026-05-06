# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py makemigrations
python manage.py migrate

# Run Django dev server (API + mini app)
python manage.py runserver

# Run Telegram bot (long polling, separate process)
python manage.py runbot

# Create superuser for /admin/ panel
python manage.py createsuperuser
```

No test runner, linter, or CI/CD is configured.

## Environment Variables (.env)

```
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DB_NAME=crm_bot
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
BOT_TOKEN=              # From @BotFather
MENTOR_TELEGRAM_ID=     # Numeric Telegram ID of the mentor
MENTOR_USERNAME=        # Telegram @username of the mentor
```

The mini app requires HTTPS — use ngrok or VS Code Dev Tunnels in development. Trusted origins are configured in `mentor_crm/settings.py` via `CSRF_TRUSTED_ORIGINS`.

## Architecture

This is a **Telegram Mini App CRM** for a mentor managing students across programming groups (C++, Python, Rust, Blockchain). It has three concurrent components:

### 1. Telegram Bot (`bot/management/commands/runbot.py`)
Aiogram 3 long-polling bot. Two entry points:
- **Students** — `/start` auto-registers them as a `Student` record and notifies the mentor.
- **Mentor** — Menu-driven FSM for broadcasting messages to student groups and distributing unassigned students.

### 2. Django REST API (`bot/api_views.py`, `bot/api_urls.py`)
All endpoints are under `/api/`. Authentication is via the `X-Telegram-Init-Data` header containing the Telegram WebApp `initData` payload, verified by HMAC-SHA256 in `bot/auth.py`. The auth logic identifies a caller as either the configured mentor or a registered student.

Key endpoints:
- `GET /api/me/` — returns role + profile
- `GET /api/students/` — mentor only
- `GET/POST /api/deadlines/` — mentor creates, students read their assigned ones
- `GET /api/assignments/` — filtered by role
- `POST /api/assignments/{id}/submit|approve|reject/`

### 3. Telegram Mini App frontend (`webapp/`)
Vanilla JS, no build step. Entry at `webapp/index.html` — calls `/api/me/` and redirects to `webapp/mentor.html` or `webapp/student.html`. The Telegram WebApp SDK (`tg.js`) provides the `initData` token injected into every API request header via `api.js`.

### Data Models (`bot/models.py`)
- `Student` — Telegram user with assigned group
- `Deadline` — topic, description, due date; created by mentor
- `DeadlineAssignment` — junction: which student got which deadline; status: `pending → submitted → approved/rejected`
- `Submission` — student's text/file answer (multiple allowed per assignment for revisions)

When a deadline is created or an assignment is approved/rejected, `bot/notifications.py` sends async Telegram messages via the bot.
