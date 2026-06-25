"""Factory for Outlook COM vs Microsoft Graph backends."""

from __future__ import annotations

from typing import Protocol

from config import get_outlook_source
from outlook_com_client import OutlookComClient
from outlook_graph_client import OutlookGraphClient
from outlook_models import CalendarEvent, MailItem


class OutlookBackend(Protocol):
    def get_current_user_email(self) -> str | None: ...
    def get_unread_inbox_count(self) -> int | None: ...
    def list_unread_messages(self, max_count: int = 10) -> list[MailItem]: ...
    def list_upcoming_events(self, within_hours: int = 24) -> list[CalendarEvent]: ...
    def close(self) -> None: ...


def create_outlook_backend(source: str | None = None) -> OutlookComClient | OutlookGraphClient:
    selected = (source or get_outlook_source()).strip().lower()
    if selected == "graph":
        return OutlookGraphClient()
    return OutlookComClient()
