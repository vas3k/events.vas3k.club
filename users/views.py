from django.shortcuts import render, redirect

from tickets.models import Ticket


def profile(request):
    if not request.user.is_authenticated:
        return redirect("login")

    tickets = Ticket.objects.filter(user=request.user).select_related("event", "ticket_type").order_by("-created_at")

    return render(request, "users/profile.html", {"tickets": tickets})
