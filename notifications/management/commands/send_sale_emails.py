import logging

from django.conf import settings
from django.core.management import BaseCommand

from events.models import Event
from notifications.helpers import send_notifications
from notifications.models import EventSubscription

log = logging.getLogger(__name__)

TEXT = """Приветы!

Вы оставляли нам свой имейл, чтобы мы уведомили вас о начале продажи билетов на %(event_name)s.

Так вот мы спешим вам рассказать, что продажа началась. Скорее кликайте кнопочку и записывайтесь!

[.button 🔥 Опа опа опа](%(event_link)s) 
"""

class Command(BaseCommand):
    help = "Send sale announcement emails + telegrams"

    def add_arguments(self, parser):
        parser.add_argument("--event-id", type=str, required=False)
        parser.add_argument("--production", type=bool, required=False, default=False)
        parser.add_argument("--auto-confirm", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        production = options.get("production")
        event_id = options.get("event_id")

        event = Event.objects.get(id=event_id)

        print(f"Event: {event.id}: {event.title}")
        print(f"Mode: {'PRODUCTION' if production else 'DEBUG'}")

        # Select subscribers
        if production:
            subscribers = EventSubscription.objects.filter(event=event, topic__in=["all", "sale"]).all()
        else:
            subscribers = EventSubscription.objects.filter(email="me@vas3k.ru").all()

        # Confirm?
        auto_confirm = options.get("auto_confirm")
        if not auto_confirm:
            confirm = input(f"Confirm sending sale notifications '{event.title}' to {len(subscribers)} subscribers? [y/N]: ")
            if confirm != "y":
                self.stdout.write(f"Not confirmed. Exiting...")
                return

        # Send emails + telegrams
        for subscriber in subscribers:
            self.stdout.write(f"Sending message to user: {subscriber.email}")

            # send a letter
            try:
                send_notifications(
                    email_address=subscriber.email,
                    telegram_id=subscriber.user.telegram_id if subscriber.user else None,
                    message_title=f"Продажа билетов на {event.title} началась!",
                    message_text=TEXT.format(
                        event_name=event.title,
                        event_link=f"{settings.APP_HOST}/{event.id}/",
                    ),
                )
            except Exception as ex:
                log.exception("Failed to send email to %s", subscriber.email)
                self.stdout.write(f"Sending to {subscriber.email} failed: {ex}")
                continue

        self.stdout.write("Done 🥙")
