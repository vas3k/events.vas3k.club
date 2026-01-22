from django import template
from django.utils import formats

register = template.Library()


@register.simple_tag(takes_context=True)
def pretty_date_range(context, date_from, date_to):
    # If both are None, return empty string
    if not date_from and not date_to:
        return ""

    # If only date_from exists, show single date
    if date_from and not date_to:
        return formats.date_format(date_from, "j E Y")  # e.g., "15 May 2025"

    # If only date_to exists, show single date
    if not date_from and date_to:
        return formats.date_format(date_to, "j E Y")  # e.g., "20 June 2025"

    # Both dates exist - format as range
    from_day = int(formats.date_format(date_from, "j"))
    to_day = int(formats.date_format(date_to, "j"))
    from_month = formats.date_format(date_from, "E")
    to_month = formats.date_format(date_to, "E")
    from_year = int(formats.date_format(date_from, "Y"))
    to_year = int(formats.date_format(date_to, "Y"))

    # Same month and year
    if date_from.month == date_to.month and date_from.year == date_to.year:
        return f"{from_day}-{to_day} {from_month} {from_year}"

    # Same year, different months
    elif date_from.year == date_to.year:
        return f"{from_day:02d} {from_month} – {to_day:02d} {to_month} {from_year}"

    # Different years
    else:
        return f"{from_day:02d} {from_month} – {to_day:02d} {to_month} {to_year}"


@register.filter
def dict_get(value, key):
    return value.get(key)
