from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect

from events.forms import EventForm
from events.models import Event, TicketType
from notifications.models import EventSubscription
from tickets.models import Ticket


def show_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    ticket_types = TicketType.objects.filter(event=event)

    my_tickets = []
    participants = []
    my_notifications = []
    if request.user and request.user.is_authenticated():
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

            return redirect("event_detail", event_id=event.id)
    else:
        form = EventForm(instance=event)

    return render(request, "events/edit-event.html", {
        "form": form,
        "event": event,
    })
