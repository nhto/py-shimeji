"""Open Outlook mail/calendar items and meeting links from speech-bubble actions."""

from __future__ import annotations

import logging
import sys
import urllib.parse

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from config import OUTLOOK_SOURCE_COM, get_outlook_source
from outlook_models import CalendarEvent, MailItem

_logger = logging.getLogger(__name__)


def open_url(url: str) -> None:
    """Open an http(s) URL in the default browser or registered handler."""
    stripped = url.strip()
    if not stripped:
        return
    if not QDesktopServices.openUrl(QUrl(stripped)):
        _logger.warning("Could not open URL: %s", stripped)


def graph_mail_read_url(message_id: str) -> str:
    """Build an Outlook on the web deep link for a Graph message id."""
    encoded = urllib.parse.quote(message_id, safe="")
    return (
        f"https://outlook.office.com/mail/deeplink/read/{encoded}"
        f"?ItemID={encoded}&exvsurl=1"
    )


def graph_calendar_event_url(event_id: str) -> str:
    """Build an Outlook on the web deep link for a Graph calendar event id."""
    encoded = urllib.parse.quote(event_id, safe="")
    return f"https://outlook.office.com/calendar/item/{encoded}"


def _display_via_com(entry_id: str, store_id: str | None = None) -> bool:
    if sys.platform != "win32" or not entry_id:
        return False
    from outlook_com_client import OutlookComClient

    client = OutlookComClient()
    try:
        return client.display_item_by_entry_id(entry_id, store_id=store_id)
    finally:
        client.close()


def open_mail(mail: MailItem) -> None:
    """Show a mail message in classic Outlook or Outlook on the web."""
    if get_outlook_source() == OUTLOOK_SOURCE_COM and _display_via_com(
        mail.entry_id,
        mail.store_id,
    ):
        return
    open_url(graph_mail_read_url(mail.entry_id))


def open_calendar_event(event: CalendarEvent) -> None:
    """Show a calendar event in classic Outlook or Outlook on the web."""
    if get_outlook_source() == OUTLOOK_SOURCE_COM and _display_via_com(event.entry_id):
        return
    open_url(graph_calendar_event_url(event.entry_id))


def join_meeting(event: CalendarEvent) -> None:
    """Open the Teams (or other) join URL for an online meeting."""
    open_url(event.online_meeting_url)
