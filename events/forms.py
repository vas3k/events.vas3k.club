from django import forms
from events.models import Event, TicketType


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "description", "location", "location_url",
            "sale_starts_at", "sale_ends_at", "event_starts_at", "event_ends_at",
            "icon", "image", "intro", "managers", "contact_url", "waitlist_url",
            "is_free_event", "is_visible", "is_sold_out", "index"
        ]
        widgets = {
            "sale_starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "sale_ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "event_starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "event_ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "description": forms.Textarea(attrs={"rows": 4}),
            "intro": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Format datetime fields for datetime-local input
        for field_name in ["sale_starts_at", "sale_ends_at", "event_starts_at", "event_ends_at"]:
            if self.instance and getattr(self.instance, field_name, None):
                dt = getattr(self.instance, field_name)
                if dt:
                    self.initial[field_name] = dt.strftime("%Y-%m-%dT%H:%M")


class TicketTypeForm(forms.ModelForm):
    class Meta:
        model = TicketType
        fields = [
            "name", "description", "price", "currency", "url",
            "stripe_price_id",
            "welcome_message_title", "welcome_message_text",
            "limit_quantity", "limit_per_user", "is_sold_out", "is_visible"
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "welcome_message_text": forms.Textarea(attrs={"rows": 6}),
        }
