from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from events.models import Event
from notifications.models import EventSubscription
from vas3k_events.exceptions import BadRequest


def subscribe(request, event_id, topic):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        email = request.POST.get("email")

        if not email and request.user.is_authenticated:
            email = request.user.email

        if not email:
            raise BadRequest(title="Укажите почту", message="А то куда писать-то?")

        if "@" not in email or "." not in email or len(email) > 100:
            raise BadRequest(title="Странная у вас почта", message="Укажите нормальную!")

        EventSubscription.objects.get_or_create(
            event=event,
            email=email,
            topic=topic,
            defaults=dict(
                user=request.user if request.user.is_authenticated else None,
            )
        )

    return render(request, "message.html", {
        "title": "Ок!",
        "message": f"Мы пинганём вас на «{email}»"
    })


@login_required
def unsubscribe(request, event_id, topic):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        EventSubscription.objects.filter(
            event=event,
            topic=topic,
            user=request.user,
        ).delete()

    return render(request, "message.html", {
        "title": "Ладно :(",
        "message": f"Мы не будем вас уведомлять!"
    })