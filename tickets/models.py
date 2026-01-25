from collections import defaultdict
from uuid import uuid4

from django.db import models


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    code = models.CharField(max_length=16, default="[X]")
    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    stripe_payment_id = models.CharField(max_length=255, null=True, blank=True)

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, blank=True)
    ticket_type = models.ForeignKey("events.TicketType", on_delete=models.CASCADE, related_name="sales")
    metadata = models.JSONField(default=dict, null=True, blank=True)
    session = models.JSONField(default=dict, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    transfer_code = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "tickets"
        ordering = ["-created_at"]

    def has_checklist(self):
        return bool(self.ticket_type.checklists)


class TicketChecklistAnswers(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    ticket = models.ForeignKey("tickets.Ticket", on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    checklist = models.ForeignKey("events.TicketTypeChecklist", on_delete=models.CASCADE)

    answer = models.JSONField(default=str, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ticket_checklist_answers"
        ordering = ["created_at"]
        unique_together = [("ticket", "user", "checklist")]

    @classmethod
    def event_answer_stats(cls, event):
        answers = TicketChecklistAnswers.objects.filter(ticket__event=event)
        stats = defaultdict(lambda: defaultdict(int))
        for answer in answers:
            stats[answer.checklist.id][str(answer.answer)] += 1
        return stats
