from datetime import datetime

from django.shortcuts import render

from events.models import Event


def landing_page(request):
    upcoming_events = Event.objects.filter(event_starts_at__gte=datetime.utcnow())
    past_events = Event.objects.filter(event_starts_at__lt=datetime.utcnow())
    return render(request, "landing.html", {
        "upcoming_events": upcoming_events,
        "past_events": past_events,
    })
