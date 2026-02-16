import logging

import stripe
from django.db.models import Q, F

from events.models import TicketTypeChecklist, TicketType, Event
from tickets.models import TicketChecklistAnswers, Ticket
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


def activate_ticket(user, ticket_type, metadata=None, session=None):
    return Ticket.objects.create(
        user=user,
        code=Ticket.objects.filter(event=ticket_type.event).count() + 1,
        customer_email=user.email,
        stripe_payment_id=(session or {}).get("payment_intent"),
        event=ticket_type.event,
        ticket_type=ticket_type,
        metadata=metadata or {},
        session=session or {},
    )


def update_ticket_counters_and_sold_out(ticket_type):
    ticket_sales_count = Ticket.objects.filter(ticket_type=ticket_type).count()

    if ticket_type.limit_quantity >= 0 and ticket_sales_count >= ticket_type.limit_quantity:
        # Check if ticket is sold out
        ticket_type.tickets_sold = ticket_sales_count
        ticket_type.is_sold_out = True

        # Check if the whole event is sold out
        any_active_tickets_left = TicketType.objects.filter(
            event=ticket_type.event,
            special_code__isnull=True,
        ).filter(Q(limit_quantity__lt=0) | Q(tickets_sold__lt=F("limit_quantity")))

        if not any_active_tickets_left:
            Event.objects.filter(id=ticket_type.event_id).update(is_sold_out=True)
    else:
        # just increase counter
        ticket_type.tickets_sold = ticket_sales_count

    ticket_type.save()
