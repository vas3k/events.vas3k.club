import logging

import nh3
import requests
from authlib.integrations.django_client import OAuth
from django.conf import settings

log = logging.getLogger(__name__)

oauth = OAuth()
oauth.register(**settings.CLUB_OPENID_CONFIG)


def parse_membership(token):
    try:
        return requests.get(
            url=f"{oauth.club.api_base_url}/user/me.json",
            headers={
                "Authorization": f"{token['token_type']} {token['access_token']}"
            }
        ).json()
    except Exception as ex:
        log.exception(ex)
        return None


def parse_badge(token):
    try:
        html = requests.get(
            url=f"{oauth.club.api_base_url}/user/me.badge.html",
            headers={
                "Authorization": f"{token['token_type']} {token['access_token']}"
            }
        ).text
        return nh3.clean(html)
    except Exception as ex:
        log.exception(ex)
        return None
