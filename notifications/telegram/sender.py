import logging
from collections import namedtuple

import telegram
from asgiref.sync import async_to_sync
from django.conf import settings
from django.template import loader
from telegram.constants import ParseMode

from common.regexp import IMAGE_RE

log = logging.getLogger()

bot = telegram.Bot(token=settings.TELEGRAM_TOKEN) if settings.TELEGRAM_TOKEN else None
Chat = namedtuple("Chat", ["id"])

NORMAL_TEXT_LIMIT = 4096
PHOTO_TEXT_LIMIT = 1024


def send_telegram_message(
    chat: Chat,
    text: str,
    parse_mode: ParseMode = ParseMode.HTML,
    disable_preview: bool = True,
    **kwargs
):
    if not bot:
        log.warning("No telegram token. Skipping")
        return

    if not chat:
        log.warning("No chat id. Skipping")
        return

    log.info(f"Telegram: sending message to chat_id {chat.id}, starting with {text[:10]}...")

    images_in_message = IMAGE_RE.findall(text)

    try:
        if len(images_in_message) == 1 and len(text) < PHOTO_TEXT_LIMIT:
            return async_to_sync(bot.send_photo)(
                chat_id=chat.id,
                photo=images_in_message[0],
                caption=text[:PHOTO_TEXT_LIMIT],
                parse_mode=parse_mode,
                **kwargs
            )
        else:
            return async_to_sync(bot.send_message)(
                chat_id=chat.id,
                text=text[:NORMAL_TEXT_LIMIT],
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
                **kwargs
            )
    except telegram.error.TelegramError as ex:
        log.warning(f"Telegram error: {ex}")


def render_html_message(template, **data):
    template = loader.get_template(f"messages/{template}")
    return template.render({
        **data,
        "settings": settings
    })
