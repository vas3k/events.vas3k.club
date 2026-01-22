from uuid import uuid4

from django.db import models

class EventSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True)
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE)
    email = models.EmailField(null=True, blank=True)
    topic = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_subscription"
        unique_together = [("event", "email", "topic")]


