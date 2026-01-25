from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from django.db import models

from users.models import User


class Event(models.Model):
    id = models.CharField(max_length=32, primary_key=True, editable=False)

    title = models.CharField(max_length=255)
    description = models.TextField(default="", null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    location_url = models.URLField(null=True, blank=True)
    sale_starts_at = models.DateTimeField(null=True, blank=True)
    sale_ends_at = models.DateTimeField(null=True, blank=True)
    event_starts_at = models.DateTimeField(null=True, blank=True)
    event_ends_at = models.DateTimeField(null=True, blank=True)
    icon = models.URLField(null=True, blank=True)
    image = models.URLField(null=True, blank=True)
    intro = models.TextField(null=True, blank=True)

    managers = models.TextField(null=True, blank=True)  # TODO: make JSON
    contact_url = models.URLField(null=True, blank=True)
    waitlist_url = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_free_event = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    is_sold_out = models.BooleanField(default=False)
    index = models.IntegerField(default=0)

    class Meta:
        db_table = "events"
        ordering = ["index", "-created_at"]

    def manager_users(self):
        if self.managers:
            return User.objects.filter(slug__in=self.managers.split(","))
        return []

    def is_sale_active(self):
        if self.is_sold_out or not self.sale_starts_at:
            return False

        if not self.sale_ends_at:
            return self.sale_starts_at <= datetime.utcnow() and not self.is_sold_out

        return self.sale_starts_at <= datetime.utcnow() <= self.sale_ends_at and not self.is_sold_out

    def is_sale_starts_soon(self):
        if self.is_sold_out or not self.sale_starts_at:
            return False
        return self.sale_starts_at > datetime.utcnow()

    def seconds_until_sale_starts(self):
        if self.is_sold_out:
            return 0

        if self.sale_starts_at and self.sale_starts_at > datetime.utcnow():
            return int((self.sale_starts_at - datetime.utcnow()).total_seconds())
        return 0


class TicketType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.FloatField(default=0)
    currency = models.CharField(max_length=8, default="", null=True, blank=True)
    url = models.URLField(null=True, blank=True)

    stripe_price_id = models.CharField(max_length=255, null=True, blank=True)

    welcome_message_title = models.CharField(max_length=255, null=True, blank=True)
    welcome_message_text = models.TextField(null=True, blank=True)

    tickets_sold = models.IntegerField(default=0)
    limit_quantity = models.IntegerField(default=-1)
    limit_per_user = models.IntegerField(default=-1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    checklists = models.JSONField(default=list, null=True, blank=True)
    special_code = models.CharField(max_length=32, null=True, blank=True)

    is_sold_out = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "ticket_types"
        ordering = ["created_at"]

    def __str__(self):
        return self.name

    def left_tickets_count(self):
        if self.limit_quantity > 0:
            return self.limit_quantity - self.tickets_sold
        return -1


class TicketTypeChecklist(models.Model):
    TYPE_SELECT = "select"
    TYPE_TEXT = "text"
    TYPE_LINK = "link"
    TYPES = [
        (TYPE_SELECT, TYPE_SELECT),
        (TYPE_TEXT, TYPE_TEXT),
        (TYPE_LINK, TYPE_LINK),
    ]

    id = models.CharField(primary_key=True, max_length=32, editable=False)

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=TYPES, default=TYPE_SELECT)
    value = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    is_required = models.BooleanField(default=False)

    class Meta:
        db_table = "ticket_checklists"
        ordering = ["created_at"]


@dataclass
class TicketChecklistWithAnswers:
    option: TicketTypeChecklist
    answer: str
    stats: dict
