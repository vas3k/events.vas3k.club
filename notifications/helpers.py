import logging

from django.template import loader

from common.markdown.markdown import markdown_text, markdown_tg
from notifications.email.sender import send_transactional_email
from notifications.telegram.sender import send_telegram_message, Chat

log = logging.getLogger()


def send_notifications(email_address, telegram_id, message_title="", message_text=""):
    if email_address:
        try:
            confirmation_template = loader.get_template("email.html")
            send_transactional_email(
                recipient=email_address,
                subject=message_title,
                html=confirmation_template.render({
                    "title": message_title,
                    "message": markdown_text(message_text),
                })
            )
        except Exception as e:
            log.exception(f"Email notification failed: {e}")

    if telegram_id:
        try:
            send_telegram_message(
                chat=Chat(id=telegram_id),
                text=f"<b>{message_title}</b>\n\n"
                     f"{markdown_tg(message_text)}",
            )
        except Exception as e:
            log.exception(f"Telegram notification failed: {e}")
