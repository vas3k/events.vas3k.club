from django import forms
from .models import Event, TicketType


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "description", "location", "location_url",
            "sale_starts_at", "sale_ends_at", "event_starts_at", "event_ends_at",
            "icon", "image", "intro", "managers", "contact_url", "waitlist_url",
            "is_visible", "is_sold_out", "index"
        ]


class TicketTypeForm(forms.ModelForm):
    class Meta:
        model = TicketType
        fields = [
            "name", "description", "price", "currency", "url",
            "stripe_product_id", "stripe_payment_link_id",
            "welcome_message_title", "welcome_message_text",
            "limit_quantity", "is_visible"
        ]
