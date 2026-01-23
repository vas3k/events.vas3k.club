import logging

import stripe
from authlib.oauth1.rfc5849.errors import MethodNotAllowedError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt

from events.models import TicketType, TicketTypeChecklist, TicketChecklistWithAnswers
from tickets.models import Ticket, TicketChecklistAnswers

from tickets.helpers import parse_stripe_webhook_event, deactivate_payment_link
from notifications.helpers import send_notifications
from users.models import User
from vas3k_events.exceptions import BadRequest, RateLimitException

log = logging.getLogger()


@csrf_exempt
def stripe_webhook(request):
    try:
        event = parse_stripe_webhook_event(
            request=request,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
            api_key=settings.STRIPE_API_KEY
        )
    except BadRequest as ex:
        return HttpResponse(ex.message, status=ex.code)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        customer_email = session["customer_details"]["email"].lower()
        user = User.objects.filter(email=customer_email).first()
        ticket_types_processed = set()

        try:
            session_with_items = stripe.checkout.Session.retrieve(
                session_id,
                expand=["line_items", "line_items.data.price.product"],
                api_key=settings.STRIPE_API_KEY
            )

            # Process each item in the purchase
            if session_with_items.line_items:
                for item in session_with_items.line_items.data:
                    stripe_product_id = item.price.product.id

                    # Find the corresponding ticket
                    try:
                        ticket_type = TicketType.objects.get(stripe_product_id=stripe_product_id)
                    except TicketType.DoesNotExist:
                        log.exception(f"Ticket type for product_id {stripe_product_id} not found")
                        raise BadRequest(f"Ticket type for product_id {stripe_product_id} not found")

                    # Issue a ticket (one for each quantity)
                    for _ in range(item.quantity):
                        Ticket.objects.create(
                            user=user,
                            code=Ticket.objects.filter(event=ticket_type.event).count() + 1,
                            customer_email=customer_email,
                            stripe_payment_id=session.get("payment_intent"),
                            event=ticket_type.event,
                            ticket_type=ticket_type,
                            metadata={
                                "price_paid": item.price.unit_amount / 100,  # Convert from cents
                                "currency": item.price.currency,
                                "purchased_at": session["created"],
                            },
                            session=session,
                        )

                    ticket_types_processed.add(ticket_type)

                    # Check if number of sales is exceeded
                    ticket_sales_count = Ticket.objects.filter(ticket_type=ticket_type).count()
                    TicketType.objects.filter(stripe_product_id=stripe_product_id).update(
                        tickets_sold=ticket_sales_count
                    )
                    if ticket_type.limit_quantity >= 0 and ticket_type.stripe_payment_link_id:
                        if ticket_sales_count >= ticket_type.limit_quantity:
                            deactivate_payment_link(ticket_type.stripe_payment_link_id)

            # Send confirmation emails (unique by ticket code)
            for ticket_type in ticket_types_processed:
                try:
                    send_notifications(
                        email_address=customer_email,
                        telegram_id=user.telegram_id if user else None,
                        message_title=ticket_type.welcome_message_title,
                        message_text=ticket_type.welcome_message_text,
                    )
                except:
                    log.exception(f"Ticket notification failed")

            return HttpResponse("[ok]", status=200)

        except stripe.error.StripeError as e:
            log.error(f"Stripe API error: {str(e)}")
            return HttpResponse(f"Stripe API error: {str(e)}", status=500)

    return HttpResponse("[unknown event]", status=400)


@login_required
def show_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.user != request.user:
        raise PermissionDenied()

    checklist = []
    if ticket.ticket_type.checklists:
        ticket_checklists = TicketTypeChecklist.objects.filter(id__in=ticket.ticket_type.checklists)
        my_answers = {
            t.checklist.id: t for t in TicketChecklistAnswers.objects.filter(ticket=ticket).select_related("checklist")
        }
        answer_stats = TicketChecklistAnswers.event_answer_stats(ticket.event)

        for ticket_checklist in ticket_checklists:
            checklist.append(TicketChecklistWithAnswers(
                option=ticket_checklist,
                answer=my_answers[ticket_checklist.id].answer \
                    if my_answers.get(ticket_checklist.id) else None,
                stats=answer_stats.get(ticket_checklist.id) or {},
            ))

    return render(request, "tickets/show-ticket.html", {
        "ticket": ticket,
        "checklist": checklist,
    })


@login_required
def update_ticket_checklist_answer(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.user != request.user:
        raise PermissionDenied()

    if request.method != "POST":
        raise MethodNotAllowedError()

    checklist = get_object_or_404(TicketTypeChecklist, id=request.POST["checklist_id"])
    answer_value = request.POST["answer_value"]

    # Check limited select {"item": "...", "limit": 20}
    if answer_value and checklist.type == TicketTypeChecklist.TYPE_SELECT:
        if isinstance(checklist.value, list):
            select_item = next((v for v in checklist.value if v.get("item") == answer_value), None)
            if select_item.get("limit"):
                answer_count = TicketChecklistAnswers.objects.filter(
                    ticket=ticket,
                    checklist=checklist,
                    answer=answer_value,
                ).exclude(user=request.user).count()
                if answer_count >= select_item["limit"]:
                    raise RateLimitException(
                        title=f"Превышен лимит на {answer_value}",
                        message=f"К сожалению, только {select_item['limit']} человек может выбрать эту опцию. "
                                f"Попробуйте выбрать другую."
                    )

    # Write user answer to the database
    TicketChecklistAnswers.objects.update_or_create(
        ticket=ticket,
        user=request.user,
        checklist=checklist,
        defaults=dict(
            answer=request.POST["answer_value"],
        )
    )

    return redirect("show_ticket", ticket_id=ticket.id)
