from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import urlencode

import nh3
from icalendar import Calendar, Event as VEvent

from events.models import Event


class CalendarEventData:
    """Calendar-ready event data extracted from domain models."""

    __slots__ = ("uid", "summary", "starts_at", "ends_at", "description", "location", "url")

    def __init__(
        self,
        *,
        uid: str,
        summary: str,
        starts_at: datetime,
        ends_at: datetime | None,
        description: str | None,
        location: str | None,
        url: str | None,
    ) -> None:
        self.uid = uid
        self.summary = summary
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.description = description
        self.location = location
        self.url = url

    @classmethod
    def from_event(cls, event: Event) -> CalendarEventData:
        if not event.event_starts_at:
            raise ValueError("Event must have a start date")

        return cls(
            uid=f"event-{event.id}@events.vas3k.club",
            summary=event.title,
            starts_at=event.event_starts_at.replace(tzinfo=timezone.utc),
            ends_at=event.event_ends_at.replace(tzinfo=timezone.utc) if event.event_ends_at else None,
            description=nh3.clean(event.description, tags=set()) if event.description else None,
            location=event.location or None,
            url=event.location_url or None,
        )


class CalendarExporter(ABC):
    def __init__(self, data: CalendarEventData) -> None:
        self._data = data

    @abstractmethod
    def export(self) -> str | bytes: ...


class ICalExporter(CalendarExporter):
    PRODID = "-//vas3k.club//events//RU"

    def export(self) -> bytes:
        start = self._data.starts_at if self._data.ends_at else self._data.starts_at.date()

        vevent = VEvent.new(
            uid=self._data.uid,
            start=start,
            end=self._data.ends_at,
            summary=self._data.summary,
            description=self._data.description,
            location=self._data.location,
            url=self._data.url,
            status="CONFIRMED",
        )

        cal = Calendar.new(prodid=self.PRODID, method="PUBLISH")
        cal.add_component(vevent)
        return cal.to_ical()


class GoogleCalendarExporter(CalendarExporter):
    BASE_URL = "https://calendar.google.com/calendar/render"

    def export(self) -> str:
        fmt = "%Y%m%dT%H%M%SZ" if self._data.ends_at else "%Y%m%d"
        start = self._data.starts_at.strftime(fmt)
        end = self._data.ends_at.strftime(fmt) if self._data.ends_at else start

        params = {
            "action": "TEMPLATE",
            "text": self._data.summary,
            "dates": f"{start}/{end}",
        }

        if self._data.location:
            params["location"] = self._data.location

        if self._data.description:
            params["details"] = self._data.description

        return f"{self.BASE_URL}?{urlencode(params)}"


class OutlookCalendarExporter(CalendarExporter):
    BASE_URL = "https://outlook.live.com/calendar/0/action/compose"

    def export(self) -> str:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        params = {
            "rru": "addevent",
            "path": "/calendar/action/compose",
            "subject": self._data.summary,
            "startdt": self._data.starts_at.strftime(fmt),
        }

        if self._data.ends_at:
            params["enddt"] = self._data.ends_at.strftime(fmt)
        else:
            params["allday"] = "true"

        if self._data.location:
            params["location"] = self._data.location

        if self._data.description:
            params["body"] = self._data.description

        return f"{self.BASE_URL}?{urlencode(params)}"
