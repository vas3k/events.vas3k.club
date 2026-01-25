import csv

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from events.models import Event
from tickets.models import Ticket, TicketChecklistAnswers


@login_required
def export_tickets_csv(request, event_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    event = get_object_or_404(Event, id=event_id)
    tickets = Ticket.objects.filter(event=event).select_related("user", "ticket_type", "event").order_by("-created_at")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="tickets_{event.id}.csv"'

    # Use UTF-8 BOM for Excel compatibility
    response.write("\ufeff")

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        "Email",
        "Имя",
        "Код билета",
        "Тип билета",
        "Событие",
        "Дата покупки",
        "Email покупателя",
        "Цена",
        "Валюта",
    ])

    # Write data rows
    for ticket in tickets:
        # Get email - always include it as unique identifier
        email = ""
        if ticket.user:
            email = ticket.user.email or ""
        elif ticket.customer_email:
            email = ticket.customer_email

        # Get full name
        full_name = ticket.user.full_name if ticket.user and ticket.user.full_name else ""

        # Get price and currency from metadata
        price_paid = ""
        currency = ""
        if ticket.metadata:
            price_paid = ticket.metadata.get("price_paid", "")
            currency = ticket.metadata.get("currency", "")

        # Format created date
        created_date = ticket.created_at.strftime("%d.%m.%Y %H:%M") if ticket.created_at else ""

        writer.writerow([
            email,
            full_name,
            ticket.code,
            ticket.ticket_type.name if ticket.ticket_type else "",
            event.title,
            created_date,
            ticket.customer_email or "",
            price_paid,
            currency.upper() if currency else "",
        ])

    return response


@login_required
def export_checklists_csv(request, event_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    event = get_object_or_404(Event, id=event_id)
    answers = TicketChecklistAnswers.objects.filter(
        ticket__event=event
    ).select_related("user", "ticket", "ticket__ticket_type", "checklist").order_by("checklist__name", "created_at")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="checklists_{event.id}.csv"'

    # Use UTF-8 BOM for Excel compatibility
    response.write("\ufeff")

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        "Email",
        "Имя",
        "Чеклист",
        "Тип чеклиста",
        "Ответ",
        "Код билета",
        "Тип билета",
        "Событие",
        "Дата ответа",
    ])

    # Write data rows
    for answer in answers:
        # Get email
        email = ""
        if answer.user:
            email = answer.user.email or ""
        elif answer.ticket.customer_email:
            email = answer.ticket.customer_email

        # Get full name
        full_name = answer.user.full_name if answer.user and answer.user.full_name else ""

        # Get answer value
        answer_value = ""
        if answer.answer:
            if isinstance(answer.answer, str):
                answer_value = answer.answer
            else:
                answer_value = str(answer.answer)

        # Format created date
        created_date = answer.created_at.strftime("%d.%m.%Y %H:%M") if answer.created_at else ""

        writer.writerow([
            email,
            full_name,
            answer.checklist.name if answer.checklist else "",
            answer.checklist.type if answer.checklist else "",
            answer_value,
            answer.ticket.code if answer.ticket else "",
            answer.ticket.ticket_type.name if answer.ticket and answer.ticket.ticket_type else "",
            event.title,
            created_date,
        ])

    return response
