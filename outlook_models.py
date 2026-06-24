"""Shared Outlook mail/calendar models (COM and future Graph backends)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MailItem:
    """A single mailbox message."""

    entry_id: str
    subject: str
    sender_name: str
    sender_email: str
    received_at: datetime
    store_id: str | None = None


@dataclass(frozen=True)
class CalendarEvent:
    """A calendar appointment in the default calendar folder."""

    entry_id: str
    subject: str
    start: datetime
    end: datetime
    location: str = ""
    global_appointment_id: str | None = None
    is_all_day: bool = False
