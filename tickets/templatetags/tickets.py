from django import template

from tickets.helpers import is_checklist_completed

register = template.Library()

@register.filter
def checklist_completed(value, user):
    return is_checklist_completed(value, user)
