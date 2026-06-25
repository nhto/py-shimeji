"""Background fetch of Outlook mail/calendar as plain Python data."""

from __future__ import annotations

import logging
import urllib.error
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QThread, pyqtSignal

from config import get_outlook_source, outlook_graph_configured
from outlook_backend import create_outlook_backend
from outlook_models import CalendarEvent, MailItem

_logger = logging.getLogger(__name__)


class OutlookPollFailureReason(str, Enum):
    """Why a background Outlook poll could not complete."""

    CONNECTION_LOST = "connection_lost"
    AUTH_EXPIRED = "auth_expired"
    NOT_CONFIGURED = "not_configured"
    COM_ERROR = "com_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OutlookPollFailure:
    """Failure details emitted from a poll cycle."""

    reason: OutlookPollFailureReason
    message: str | None = None


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


def format_poll_failure_tray_hint(failure: OutlookPollFailure) -> str:
    """Return a short tray notification for a poll failure."""
    if failure.message:
        return failure.message

    hints = {
        OutlookPollFailureReason.CONNECTION_LOST: (
            "Outlook is unreachable. Notifications pause until it reconnects."
        ),
        OutlookPollFailureReason.AUTH_EXPIRED: (
            "Microsoft sign-in expired. Tray → Outlook → Connect to sign in again."
        ),
        OutlookPollFailureReason.NOT_CONFIGURED: (
            "Graph is not configured. Set AZURE_CLIENT_ID or use Classic Outlook."
        ),
        OutlookPollFailureReason.COM_ERROR: (
            "Outlook COM error. Try restarting classic Outlook."
        ),
        OutlookPollFailureReason.UNKNOWN: (
            "Outlook poll failed. Check logs for details."
        ),
    }
    return hints.get(failure.reason, hints[OutlookPollFailureReason.UNKNOWN])


def _failure_from_disconnect(*, source: str) -> OutlookPollFailure:
    if source == "graph":
        if not outlook_graph_configured():
            return OutlookPollFailure(
                reason=OutlookPollFailureReason.NOT_CONFIGURED,
                message="Azure app is not configured (AZURE_CLIENT_ID missing).",
            )
        return OutlookPollFailure(
            reason=OutlookPollFailureReason.AUTH_EXPIRED,
            message="Could not sign in to Microsoft Graph.",
        )
    return OutlookPollFailure(
        reason=OutlookPollFailureReason.CONNECTION_LOST,
        message="Classic Outlook is not available.",
    )


def _failure_from_exception(exc: BaseException, *, source: str) -> OutlookPollFailure:
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 401:
        return OutlookPollFailure(
            reason=OutlookPollFailureReason.AUTH_EXPIRED,
            message="Microsoft sign-in expired.",
        )

    if source != "graph":
        try:
            import pywintypes

            if isinstance(exc, pywintypes.com_error):
                return OutlookPollFailure(
                    reason=OutlookPollFailureReason.COM_ERROR,
                    message=str(exc) or "Outlook COM error.",
                )
        except ImportError:
            pass

    message = str(exc).strip()
    if "AZURE_CLIENT_ID" in message:
        return OutlookPollFailure(
            reason=OutlookPollFailureReason.NOT_CONFIGURED,
            message=message,
        )

    return OutlookPollFailure(
        reason=OutlookPollFailureReason.UNKNOWN,
        message=message[:200] if message else None,
    )


class OutlookPollWorker(QThread):
    """Fetch mail and/or calendar without blocking the UI thread."""

    poll_complete = pyqtSignal(object)
    poll_failed = pyqtSignal(object)

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

    def _emit_failure(self, failure: OutlookPollFailure) -> None:
        _logger.warning(
            "Outlook poll failed (%s): %s",
            failure.reason.value,
            failure.message or failure.reason.value,
        )
        self.poll_failed.emit(failure)

    def run(self) -> None:
        if self.isInterruptionRequested():
            return

        com_initialized = False
        if self._source != "graph":
            try:
                import pythoncom

                pythoncom.CoInitialize()
                com_initialized = True
            except ImportError:
                pass

        backend = create_outlook_backend(self._source)
        try:
            if self.isInterruptionRequested():
                return

            if self._source == "graph":
                connected = backend.connect(interactive=False)
            else:
                connected = backend.is_available()

            if not connected:
                if not self.isInterruptionRequested():
                    self._emit_failure(_failure_from_disconnect(source=self._source))
                return

            if self.isInterruptionRequested():
                return

            mail_items: list[MailItem] = []
            calendar_events: list[CalendarEvent] = []
            if self._poll_mail:
                mail_items = backend.list_unread_messages(max_count=20)
            if self.isInterruptionRequested():
                return
            if self._poll_calendar:
                calendar_events = backend.list_upcoming_events(within_hours=24)
            if self.isInterruptionRequested():
                return

            email = backend.get_current_user_email()
            unread_count = backend.get_unread_inbox_count()
            if self.isInterruptionRequested():
                return

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
        except Exception as exc:
            if self.isInterruptionRequested():
                return
            failure = _failure_from_exception(exc, source=self._source)
            _logger.exception(
                "Outlook poll raised (%s)",
                failure.reason.value,
            )
            self.poll_failed.emit(failure)
        finally:
            backend.close()
            if com_initialized:
                import pythoncom

                pythoncom.CoUninitialize()
