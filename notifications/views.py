from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from events.models import Event
from notifications.models import EventSubscription


@login_required
def subscribe(request, event_id, topic):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        email = request.POST.get("email") or request.user.email

        EventSubscription.objects.get_or_create(
            event=event,
            email=email,
            topic=topic,
            defaults=dict(
                user=request.user,
            )
        )

    return redirect("show_event", event.id)


@login_required
def unsubscribe(request, event_id, topic):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        EventSubscription.objects.filter(
            event=event,
            topic=topic,
            user=request.user,
        ).delete()

    return redirect("show_event", event.id)
