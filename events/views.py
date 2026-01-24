from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count

from events.forms import EventForm, TicketTypeForm
from events.models import Event, TicketType
from notifications.models import EventSubscription
from tickets.models import Ticket


def show_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    ticket_types = TicketType.objects.filter(event=event)

    my_tickets = []
    participants = []
    my_notifications = []
    if request.user and request.user.is_authenticated:
        tickets = Ticket.objects.filter(event=event).select_related("user")
        participants = {t.user for t in tickets}
        if request.user in participants:
            my_tickets = [t for t in tickets if t.user == request.user]
        my_notifications = EventSubscription.objects.filter(event=event, user=request.user)

    return render(request, "events/show-event.html", {
        "event": event,
        "ticket_types": ticket_types,
        "participants": participants,
        "my_tickets": my_tickets,
        "my_notifications": my_notifications,
    })


@login_required
def create_event(request):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    if request.method == "POST":
        form = EventForm(request.POST)

        if form.is_valid():
            event = form.save(commit=False)
            event.save()

            return redirect("show_event", event_id=event.id)
    else:
        form = EventForm()

    return render(request, "events/create-event.html", {
        "form": form,
    })


@login_required
def edit_event(request, event_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect("edit_event", event_id=event.id)
    else:
        form = EventForm(instance=event)

    return render(request, "events/edit/event.html", {
        "form": form,
        "event": event,
        "section": "event",
    })


@login_required
def edit_event_ticket_types(request, event_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    event = get_object_or_404(Event, id=event_id)
    ticket_types = TicketType.objects.filter(event=event).order_by("created_at")

    return render(request, "events/edit/ticket-types.html", {
        "event": event,
        "section": "ticket-types",
        "ticket_types": ticket_types,
    })


@login_required
def edit_event_tickets_sold(request, event_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    event = get_object_or_404(Event, id=event_id)
    tickets = Ticket.objects.filter(event=event).select_related("user", "ticket_type").order_by("-created_at")
    ticket_stats = Ticket.objects.filter(event=event).values("ticket_type__name").annotate(
        count=Count("id")
    )

    return render(request, "events/edit/tickets-sold.html", {
        "event": event,
        "section": "tickets-sold",
        "tickets": tickets,
        "ticket_stats": ticket_stats,
    })


@login_required
def edit_event_notifications(request, event_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    event = get_object_or_404(Event, id=event_id)
    subscriptions = EventSubscription.objects.filter(event=event).select_related("user").order_by("-created_at")

    return render(request, "events/edit/notifications.html", {
        "event": event,
        "section": "notifications",
        "subscriptions": subscriptions,
    })


@login_required
def edit_ticket_type(request, event_id, ticket_type_id=None):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    event = get_object_or_404(Event, id=event_id)

    if ticket_type_id:
        ticket_type = get_object_or_404(TicketType, id=ticket_type_id, event=event)
    else:
        ticket_type = None

    if request.method == "POST":
        form = TicketTypeForm(request.POST, instance=ticket_type)
        if form.is_valid():
            ticket_type = form.save(commit=False)
            ticket_type.event = event
            ticket_type.save()
            return redirect("edit_event_ticket_types", event_id=event.id)
    else:
        form = TicketTypeForm(instance=ticket_type)

    return render(request, "events/edit/ticket-type.html", {
        "form": form,
        "event": event,
        "ticket_type": ticket_type,
    })


@login_required
def delete_ticket_type(request, event_id, ticket_type_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    if request.method != "POST":
        raise PermissionDenied("Только POST запросы")

    event = get_object_or_404(Event, id=event_id)
    ticket_type = get_object_or_404(TicketType, id=ticket_type_id, event=event)
    ticket_type.delete()
    return redirect("edit_event_ticket_types", event_id=event.id)


@login_required
def delete_notification(request, event_id, subscription_id):
    if not request.user.is_admin:
        raise PermissionDenied("Вы не админ")

    if request.method != "POST":
        raise PermissionDenied("Только POST запросы")

    event = get_object_or_404(Event, id=event_id)
    subscription = get_object_or_404(EventSubscription, id=subscription_id, event=event)
    subscription.delete()
    return redirect("edit_event_notifications", event_id=event.id)
