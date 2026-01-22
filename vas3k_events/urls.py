from django.urls import path

from authn.views import log_out, login_club, club_callback, log_in
from events.views import show_event, edit_event, create_event
from landing.views import landing_page
from notifications.views import subscribe, unsubscribe
from tickets.views import show_ticket, update_ticket_checklist_answer, stripe_webhook
from users.views import profile

urlpatterns = [
    path("", landing_page, name="index"),

    path(r"me/", profile, name="profile"),
    path(r"login/", log_in, name="login"),
    path(r"logout/", log_out, name="logout"),
    path(r"auth/login/club/", login_club, name="login_club"),
    path(r"auth/club_callback/", club_callback, name="club_callback"),

    path(r"stripe/webhook/", stripe_webhook, name="stripe_webhook"),

    path(r"ticket/<str:ticket_id>/", show_ticket, name="show_ticket"),
    path(r"ticket/<str:ticket_id>/checklist/answers/",
         update_ticket_checklist_answer, name="update_ticket_checklist_answer"),

    path(r"notifications/subscribe/<str:event_id>/<str:topic>/", subscribe, name="subscribe"),
    path(r"notifications/unsubscribe/<str:event_id>/<str:topic>/", unsubscribe, name="unsubscribe"),

    path(r"create/", create_event, name="create_event"),
    path(r"<slug:event_id>/", show_event, name="show_event"),
    path(r"<slug:event_id>/edit/", edit_event, name="edit_event"),
]
