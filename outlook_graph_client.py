"""Microsoft Graph client for New Outlook / Microsoft 365 mailboxes."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from outlook_graph_auth import GRAPH_SCOPES, acquire_graph_token, outlook_graph_configured
from outlook_models import CalendarEvent, MailItem

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

_logger = logging.getLogger(__name__)


def _parse_graph_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _sender_from_message(message: dict[str, Any]) -> tuple[str, str]:
    sender = message.get("from", {})
    if not isinstance(sender, dict):
        sender = {}
    email_address = sender.get("emailAddress", {})
    if not isinstance(email_address, dict):
        email_address = {}
    name = str(email_address.get("name") or "(unknown)")
    address = str(email_address.get("address") or "(unknown)")
    return name, address


class OutlookGraphClient:
    """Read mailbox and calendar via Microsoft Graph."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._email: str | None = None

    def is_configured(self) -> bool:
        return outlook_graph_configured()

    def is_available(self) -> bool:
        """Return True when a cached Graph token can be used without prompting."""
        return self.connect(interactive=False)

    def connect(self, *, interactive: bool = True) -> bool:
        """Acquire a Graph access token silently or via browser sign-in."""
        if not outlook_graph_configured():
            return False

        token = acquire_graph_token(interactive=interactive)
        if token is None:
            self._access_token = None
            return False

        self._access_token = str(token["access_token"])
        self._email = self._fetch_current_user_email()
        return True

    def get_current_user_email(self) -> str | None:
        if self._email:
            return self._email
        if not self._access_token and not self.connect(interactive=False):
            return None
        self._email = self._fetch_current_user_email()
        return self._email

    def get_unread_inbox_count(self) -> int | None:
        if not self._access_token and not self.connect(interactive=False):
            return None
        payload = self._get("/me/mailFolders/inbox?$select=unreadItemCount")
        if payload is None:
            return None
        try:
            return int(payload.get("unreadItemCount", 0))
        except (TypeError, ValueError):
            return None

    def list_unread_messages(self, max_count: int = 10) -> list[MailItem]:
        if max_count <= 0:
            return []
        if not self._access_token and not self.connect(interactive=False):
            return []

        top = max(1, min(max_count, 50))
        query = urllib.parse.urlencode(
            {
                "$filter": "isRead eq false",
                "$top": str(top),
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,receivedDateTime",
            }
        )
        payload = self._get(f"/me/messages?{query}")
        if payload is None:
            return []

        messages = payload.get("value", [])
        if not isinstance(messages, list):
            return []

        result: list[MailItem] = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            mail = self._mail_item_from_graph(message)
            if mail is not None:
                result.append(mail)
        return result

    def list_upcoming_events(self, within_hours: int = 24) -> list[CalendarEvent]:
        if within_hours <= 0:
            return []
        if not self._access_token and not self.connect(interactive=False):
            return []

        now = datetime.now(timezone.utc)
        end = now + timedelta(hours=within_hours)
        query = urllib.parse.urlencode(
            {
                "startDateTime": now.isoformat().replace("+00:00", "Z"),
                "endDateTime": end.isoformat().replace("+00:00", "Z"),
                "$orderby": "start/dateTime",
                "$select": "id,subject,start,end,location,isAllDay,iCalUId",
            }
        )
        payload = self._get(f"/me/calendarView?{query}")
        if payload is None:
            return []

        events = payload.get("value", [])
        if not isinstance(events, list):
            return []

        result: list[CalendarEvent] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            parsed = self._calendar_event_from_graph(event)
            if parsed is not None:
                result.append(parsed)
        result.sort(key=lambda item: item.start)
        return result

    def close(self) -> None:
        self._access_token = None
        self._email = None

    def _fetch_current_user_email(self) -> str | None:
        payload = self._get("/me?$select=mail,userPrincipalName")
        if payload is None:
            return None
        mail = payload.get("mail")
        if isinstance(mail, str) and mail.strip():
            return mail.strip()
        upn = payload.get("userPrincipalName")
        if isinstance(upn, str) and upn.strip():
            return upn.strip()
        return None

    def _get(self, path: str) -> dict[str, Any] | None:
        if not self._access_token:
            return None

        url = f"{GRAPH_BASE_URL}{path}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
            payload = json.loads(body)
            return payload if isinstance(payload, dict) else None
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                self._access_token = None
            _logger.warning("Graph request failed: %s %s", exc.code, path)
            return None
        except Exception:
            _logger.exception("Graph request failed: %s", path)
            return None

    def _mail_item_from_graph(self, message: dict[str, Any]) -> MailItem | None:
        entry_id = str(message.get("id") or "").strip()
        if not entry_id:
            return None
        subject = str(message.get("subject") or "(no subject)")
        sender_name, sender_email = _sender_from_message(message)
        received_raw = str(message.get("receivedDateTime") or "")
        received_at = (
            _parse_graph_datetime(received_raw)
            if received_raw
            else datetime.now()
        )
        return MailItem(
            entry_id=entry_id,
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            received_at=received_at,
        )

    def _calendar_event_from_graph(self, event: dict[str, Any]) -> CalendarEvent | None:
        entry_id = str(event.get("id") or "").strip()
        if not entry_id:
            return None

        start_info = event.get("start", {})
        end_info = event.get("end", {})
        if not isinstance(start_info, dict):
            start_info = {}
        if not isinstance(end_info, dict):
            end_info = {}

        start_raw = str(start_info.get("dateTime") or "")
        end_raw = str(end_info.get("dateTime") or "")
        if not start_raw:
            return None

        location_info = event.get("location", {})
        location = ""
        if isinstance(location_info, dict):
            location = str(location_info.get("displayName") or "")

        return CalendarEvent(
            entry_id=entry_id,
            subject=str(event.get("subject") or "(no subject)"),
            start=_parse_graph_datetime(start_raw),
            end=_parse_graph_datetime(end_raw) if end_raw else _parse_graph_datetime(start_raw),
            location=location,
            global_appointment_id=str(event.get("iCalUId") or "") or None,
            is_all_day=bool(event.get("isAllDay", False)),
        )
