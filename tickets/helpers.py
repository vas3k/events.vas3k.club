import logging

import stripe
from django.conf import settings

from events.models import TicketTypeChecklist
from tickets.models import TicketChecklistAnswers
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


def is_checklist_completed(ticket, user):
    if not ticket.ticket_type.checklists:
        return True

    required_checklist_items = TicketTypeChecklist.objects.filter(
        id__in=ticket.ticket_type.checklists, is_required=True
    ).all()
    if not required_checklist_items:
        return True

    checklist_answers = TicketChecklistAnswers.objects.filter(user=user, ticket=ticket).all()
    if set([a.checklist_id for a in checklist_answers]) == set([c.id for c in required_checklist_items]):
        return True
    return False
