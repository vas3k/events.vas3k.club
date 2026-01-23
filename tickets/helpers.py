import logging

import stripe
from django.conf import settings

from vas3k_events.exceptions import BadRequest

log = logging.getLogger(__name__)


def parse_stripe_webhook_event(request, webhook_secret, **kwargs):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not payload or not sig_header:
        raise BadRequest(code=400, message="[invalid payload]")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret, **kwargs
        )
    except ValueError:
        raise BadRequest(code=400, message="[invalid payload]")
    except stripe.error.SignatureVerificationError:
        raise BadRequest(code=400, message="[invalid signature]")

    return event


def deactivate_payment_link(payment_link_id):
    try:
        stripe.PaymentLink.modify(
            payment_link_id,
            active=False,
            api_key=settings.STRIPE_API_KEY
        )
        log.info(f"Payment link {payment_link_id} has been deactivated due to sales limit")
        return True
    except stripe.error.StripeError as e:
        log.error(f"Failed to deactivate payment link {payment_link_id}: {str(e)}")
        return False
