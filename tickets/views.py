import logging

from authlib.oauth1.rfc5849.errors import MethodNotAllowedError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, F
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt

from events.models import TicketType, TicketTypeChecklist, TicketChecklistWithAnswers, Event
from tickets.stripe import stripe
from tickets.models import Ticket, TicketChecklistAnswers

from tickets.helpers import parse_stripe_webhook_event
from notifications.helpers import send_notifications
from users.models import User
from vas3k_events.exceptions import BadRequest, RateLimitException, NotFound

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
        metadata = session["metadata"]
        user = User.objects.filter(Q(id=metadata.get("user_id")) | Q(slug=metadata.get("user_slug"))).first()
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
                    stripe_price_id = item.price.id

                    # Find the corresponding ticket
                    ticket_type = TicketType.objects.filter(stripe_price_id=stripe_price_id).first()
                    if not ticket_type:
                        log.error(f"Ticket type for price_id {stripe_price_id} not found")
                        raise BadRequest(f"Ticket type for price_id {stripe_price_id} not found")

                    # Issue a ticket (one for each quantity)
                    for _ in range(item.quantity):
                        Ticket.objects.create(
                            user=user,
                            code=Ticket.objects.filter(event=ticket_type.event).count() + 1,
                            customer_email=user.email,
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
                    if ticket_type.limit_quantity >= 0 and ticket_sales_count >= ticket_type.limit_quantity:
                        # Check if ticket is sold out
                        TicketType.objects.filter(stripe_price_id=stripe_price_id).update(
                            tickets_sold=ticket_sales_count,
                            is_sold_out=True
                        )

                        # Check if the whole event is sold out
                        any_active_tickets_left = TicketType.objects.filter(
                            event=ticket_type.event,
                        ).filter(Q(limit_quantity__lt=0) | Q(tickets_sold__lt=F("limit_quantity")))
                        if not any_active_tickets_left:
                            Event.objects.filter(id=ticket_type.event_id).update(is_sold_out=True)
                    else:
                        # just increase counter
                        TicketType.objects.filter(stripe_price_id=stripe_price_id).update(
                            tickets_sold=ticket_sales_count
                        )

            # Send confirmation emails (unique by ticket code)
            for ticket_type in ticket_types_processed:
                try:
                    send_notifications(
                        email_address=user.email,
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
def buy_tickets(request):
    ticket_type_id = request.POST.get("ticket_type_id")

    try:
        ticket_type_amount = int(request.POST.get(f"ticket_type_amount_{ticket_type_id}") or 1)
    except ValueError:
        raise BadRequest()

    ticket_type = TicketType.objects.filter(id=ticket_type_id).first()
    if not ticket_type:
        raise NotFound(
            title="Билет не выбран",
            message="Выберите хоть один билет для покупки"
        )

    if ticket_type.is_sold_out:
        raise RateLimitException(
            title="Эти билеты закончились",
            message="К сожалению, билеты этого типа уже закончились. Попробуйте купить другие."
        )

    if ticket_type.limit_per_user > 0 and ticket_type_amount > ticket_type.limit_per_user:
        raise BadRequest(
            title=f"Максимум {ticket_type.limit_per_user} билетов в одни руки!",
            message="Выберите меньшее количество билетов"
        )

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            allow_promotion_codes=True,
            line_items=[{
                "price": ticket_type.stripe_price_id,
                "quantity": ticket_type_amount,
            }],
            customer_email=request.user.email,
            metadata={
                "user_id": request.user.id,
                "user_slug": request.user.slug
            },
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
    except stripe.error.StripeError as e:
        log.error(f"Stripe API error: {str(e)}")
        return render(request, "error.html", {
            "title": "Ошибка при покупке билетов",
            "message": str(e),
        })

    return HttpResponseRedirect(session.url)


@login_required
def update_ticket_checklist_answer(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.user != request.user:
        raise PermissionDenied()

    if request.method != "POST":
        raise MethodNotAllowedError()

    checklist = get_object_or_404(TicketTypeChecklist, id=request.POST["checklist_id"])
    answer_value = request.POST.get("answer_value") or ""

    if not answer_value:
        TicketChecklistAnswers.objects.filter(
            ticket=ticket,
            user=request.user,
            checklist=checklist,
        ).delete()
        return redirect("show_ticket", ticket_id=ticket.id)

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
