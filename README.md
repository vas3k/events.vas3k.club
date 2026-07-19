# events.vas3k.club

Website to announce and sell tickets for Vas3k Club community events.

**Live:** [https://events.vas3k.club](https://events.vas3k.club)

Stack: Django 6, PostgreSQL, Stripe, Docker. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

## Local development

1. Copy `.env` and fill in the values you need (at minimum `SECRET_KEY` and Postgres settings).
2. Start the app:

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

Without Docker:

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Postgres must be running and reachable via the `POSTGRES_*` vars in `.env`.

## Environment

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret |
| `DEBUG` | Set to `false` in production |
| `APP_HOST` | Public URL (e.g. `https://events.vas3k.club`) |
| `POSTGRES_*` | Database connection |
| `STRIPE_*` | Payments (`API_KEY`, `PUBLIC_KEY`, `WEBHOOK_SECRET`) |
| `EMAIL_*` | Outgoing mail |
| `TELEGRAM_TOKEN` / `TELEGRAM_BOT_URL` | Notifications |
| `CLUB_OPENID_CONFIG_SECRET` | Club OpenID auth |
| `SENTRY_DSN` | Error tracking (optional) |

## Production

```bash
docker compose -f docker-compose.production.yml up --build -d
```

Serves via gunicorn on port `8815`. Cron jobs run in a separate container from `etc/crontab`.
