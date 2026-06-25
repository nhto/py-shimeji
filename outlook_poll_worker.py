"""Background fetch of Outlook mail/calendar as plain Python data."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from config import get_outlook_source
from outlook_backend import create_outlook_backend
from outlook_models import CalendarEvent, MailItem


@dataclass(frozen=True)
class OutlookPollResult:
    """Snapshot returned from one poll cycle."""

    mail_items: list[MailItem]
    calendar_events: list[CalendarEvent]
    poll_mail: bool
    poll_calendar: bool
    email: str | None
    unread_count: int | None
    source: str


class OutlookPollWorker(QThread):
    """Fetch mail and/or calendar without blocking the UI thread."""

    poll_complete = pyqtSignal(object)
    poll_failed = pyqtSignal()

    def __init__(
        self,
        *,
        poll_mail: bool,
        poll_calendar: bool,
        source: str | None = None,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._poll_mail = poll_mail
        self._poll_calendar = poll_calendar
        self._source = source or get_outlook_source()

    def run(self) -> None:
        backend = create_outlook_backend(self._source)
        try:
            if self._source == "graph":
                connected = backend.connect(interactive=False)
            else:
                connected = backend.is_available()

            if not connected:
                self.poll_failed.emit()
                return

            mail_items: list[MailItem] = []
            calendar_events: list[CalendarEvent] = []
            if self._poll_mail:
                mail_items = backend.list_unread_messages(max_count=20)
            if self._poll_calendar:
                calendar_events = backend.list_upcoming_events(within_hours=24)

            email = backend.get_current_user_email()
            unread_count = backend.get_unread_inbox_count()
            self.poll_complete.emit(
                OutlookPollResult(
                    mail_items=mail_items,
                    calendar_events=calendar_events,
                    poll_mail=self._poll_mail,
                    poll_calendar=self._poll_calendar,
                    email=email,
                    unread_count=unread_count,
                    source=self._source,
                )
            )
        except Exception:
            self.poll_failed.emit()
        finally:
            backend.close()
