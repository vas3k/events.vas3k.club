from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from events.models import Event, TicketType
from tickets.models import Ticket
from users.models import User


class Command(BaseCommand):
    help = "Sync users from vas3k.club by slug list. This shit is vibe-coded."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slugs",
            required=True,
            help="Comma separated list of user slugs to sync (e.g. vas3k,alice,bob)",
        )
        parser.add_argument(
            "--event-id",
            default=None,
            help="If set, create one ticket for each synced user for this event id",
        )

    def handle(self, *args, **options):
        token = getattr(settings, "CLUB_SERVICE_TOKEN", "") or ""
        if not token:
            raise CommandError("CLUB_SERVICE_TOKEN is not set in settings/env")

        raw_slugs = options["slugs"] or ""
        slugs = [s.strip() for s in raw_slugs.split(",") if s.strip()]
        if not slugs:
            raise CommandError("No slugs provided")

        event_id = options.get("event_id")
        event = Event.objects.filter(id=event_id).first() if event_id else None
        ticket_type = None
        next_code = None
        if event_id and not event:
            raise CommandError(f"Event with id={event_id} not found")
        if event:
            ticket_type = (
                TicketType.objects.filter(event=event, is_visible=True).order_by("created_at").first()
                or TicketType.objects.filter(event=event).order_by("created_at").first()
            )
            if not ticket_type:
                ticket_type = TicketType.objects.create(
                    event=event,
                    name=event.title,
                    price=0,
                    is_visible=True,
                )
            next_code = Ticket.objects.filter(event=event).count() + 1

        base_url = getattr(settings, "CLUB_BASE_URL", "https://vas3k.club")

        ok = 0
        failed = 0
        tickets_created = 0

        for slug in slugs:
            try:
                user_json = self._fetch_user_json(base_url=base_url, slug=slug, token=token)
                user = self._upsert_user(user_json=user_json, fallback_slug=slug)
                if event and not Ticket.objects.filter(event=event, user=user).exists():
                    Ticket.objects.create(
                        user=user,
                        code=str(next_code),
                        customer_email=user.email,
                        event=event,
                        ticket_type=ticket_type,
                        metadata={"source": "sync_event_users"},
                    )
                    next_code += 1
                    tickets_created += 1
                ok += 1
                self.stdout.write(f"OK {user.slug} ({user.email})")
            except Exception as ex:
                failed += 1
                self.stderr.write(f"FAIL {slug}: {ex}")

        if failed:
            raise CommandError(f"Synced {ok} users, {failed} failed")

        tail = f", created {tickets_created} tickets for {event.id}" if event else ""
        self.stdout.write(self.style.SUCCESS(f"Synced {ok} users{tail}"))

    @staticmethod
    def _fetch_user_json(*, base_url: str, slug: str, token: str) -> dict:
        # API: https://vas3k.club/user/SLUG.json?service_token=TOKEN
        url = urljoin(base_url.rstrip("/") + "/", f"user/{slug}.json")
        resp = requests.get(url, params={"service_token": token}, timeout=20)
        if resp.status_code != 200:
            raise CommandError(f"HTTP {resp.status_code} from club API: {resp.text[:300]}")

        try:
            data = resp.json()
        except Exception as ex:
            raise CommandError(f"Invalid JSON from club API: {ex}. Body: {resp.text[:300]}")

        if not isinstance(data, dict):
            raise CommandError(f"Unexpected JSON type from club API: {type(data)}")

        return data

    @staticmethod
    @transaction.atomic
    def _upsert_user(*, user_json: dict, fallback_slug: str) -> User:
        # Match auth flow style: treat payload as {"user": {...}} (or plain user dict).
        user_data = user_json.get("user") or user_json

        slug = (user_data.get("slug") or fallback_slug or "").strip()
        email = (user_data.get("email") or "").strip()
        if not slug or not email:
            raise CommandError(f"Missing slug/email in club payload for {fallback_slug}")

        # Store everything needed for later, but never store badge here.
        profile_cache = dict(user_json or {})
        profile_cache.pop("badge", None)
        profile_cache.pop("badge_html", None)
        profile_cache.pop("badge_cache", None)

        telegram = user_data.get("telegram") or {}
        telegram_id = telegram.get("id") if isinstance(telegram, dict) else None

        user = User.objects.filter(Q(email=email) | Q(slug=slug)).first()
        if user:
            user.slug = slug
            user.email = email
            user.full_name = user_data.get("full_name") or user.full_name
            user.avatar = user_data.get("avatar") or user.avatar
            user.telegram_id = telegram_id
            user.profile_cache = profile_cache
            user.save()
            return user

        return User.objects.create_user(
            username=slug,
            email=email,
            full_name=user_data.get("full_name"),
            telegram_id=telegram_id,
            avatar=user_data.get("avatar"),
            profile_cache=profile_cache,
        )

