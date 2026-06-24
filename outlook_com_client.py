"""Thin COM wrapper around classic Outlook desktop (Windows only)."""

from __future__ import annotations

import datetime
import subprocess
import sys
import time
from typing import Any

from outlook_com_constants import (
    MK_E_UNAVAILABLE,
    OL_APPOINTMENT_ITEM,
    OL_FOLDER_CALENDAR,
    OL_FOLDER_INBOX,
    OL_MAIL_ITEM,
    PR_SENDER_SMTP_ADDRESS,
    PR_SMTP_ADDRESS,
)
from outlook_models import CalendarEvent, MailItem

_OUTLOOK_START_TIMEOUT_SEC = 45
_CALENDAR_SCAN_LIMIT = 500


def _format_restrict_datetime(value: datetime.datetime) -> str:
    """Format a local datetime for Outlook Items.Restrict date literals."""
    return value.strftime("%m/%d/%Y %I:%M %p")


def _com_to_datetime(value: Any) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if hasattr(value, "timestamp"):
        return datetime.datetime.fromtimestamp(value.timestamp())
    return datetime.datetime.fromisoformat(str(value))


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _outlook_exe_path() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE",
        ) as key:
            return winreg.QueryValue(key, None)
    except OSError:
        return None


def is_outlook_installed() -> bool:
    """Return True when classic Outlook is installed on this machine."""
    return _outlook_exe_path() is not None


def _attach_outlook_application() -> Any:
    import pywintypes
    import win32com.client

    try:
        return win32com.client.GetActiveObject("Outlook.Application")
    except pywintypes.com_error as exc:
        if exc.hresult != MK_E_UNAVAILABLE:
            raise

    outlook_path = _outlook_exe_path()
    if outlook_path is None:
        raise RuntimeError("Outlook is not installed")

    subprocess.Popen([outlook_path], close_fds=True)
    deadline = time.monotonic() + _OUTLOOK_START_TIMEOUT_SEC
    while time.monotonic() < deadline:
        time.sleep(1)
        try:
            return win32com.client.GetActiveObject("Outlook.Application")
        except pywintypes.com_error as exc:
            if exc.hresult != MK_E_UNAVAILABLE:
                raise

    return win32com.client.Dispatch("Outlook.Application")


class OutlookComClient:
    """Read-only access to the signed-in Outlook profile via COM."""

    def __init__(self) -> None:
        self._outlook: Any | None = None
        self._namespace: Any | None = None
        self._com_initialized = False

    def is_available(self) -> bool:
        """Return True when Outlook COM can be reached."""
        return self._connect()

    def get_current_user_email(self) -> str | None:
        """Return the SMTP address for the current Outlook profile, if known."""
        if not self._connect():
            return None
        assert self._namespace is not None
        try:
            user = self._namespace.CurrentUser
            smtp = user.PropertyAccessor.GetProperty(PR_SMTP_ADDRESS)
            if smtp:
                return _safe_str(smtp)
            address = getattr(user, "Address", None)
            if address and "@" in _safe_str(address):
                return _safe_str(address)
        except Exception:
            return None
        return None

    def get_unread_inbox_count(self) -> int | None:
        """Return the unread message count for the default inbox."""
        if not self._connect():
            return None
        assert self._namespace is not None
        try:
            inbox = self._namespace.GetDefaultFolder(OL_FOLDER_INBOX)
            return int(inbox.Items.Restrict("[UnRead] = True").Count)
        except Exception:
            self._reset_connection()
            return None

    def list_unread_messages(self, max_count: int = 10) -> list[MailItem]:
        """Return up to max_count unread messages from the default inbox."""
        if max_count <= 0 or not self._connect():
            return []
        assert self._namespace is not None

        try:
            inbox = self._namespace.GetDefaultFolder(OL_FOLDER_INBOX)
            restricted = inbox.Items.Restrict("[UnRead] = True")
            restricted.Sort("[ReceivedTime]", True)
            return self._collect_mail_items(restricted, max_count)
        except Exception:
            self._reset_connection()
            return []

    def list_upcoming_events(self, within_hours: int = 24) -> list[CalendarEvent]:
        """Return appointments starting within the next within_hours from now."""
        if within_hours <= 0 or not self._connect():
            return []
        assert self._namespace is not None

        now = datetime.datetime.now()
        end = now + datetime.timedelta(hours=within_hours)

        try:
            calendar = self._namespace.GetDefaultFolder(OL_FOLDER_CALENDAR)
            items = calendar.Items
            items.IncludeRecurrences = True
            items.Sort("[Start]", False)

            filter_str = (
                f"[Start] >= '{_format_restrict_datetime(now)}' "
                f"AND [Start] <= '{_format_restrict_datetime(end)}'"
            )
            try:
                source_items = items.Restrict(filter_str)
            except Exception:
                source_items = items

            events: list[CalendarEvent] = []
            scanned = 0
            for item in self._iter_com_items(source_items):
                scanned += 1
                if scanned > _CALENDAR_SCAN_LIMIT:
                    break
                event = self._calendar_event_from_com(item)
                if event is None:
                    continue
                if event.start > end:
                    break
                if event.start < now:
                    continue
                events.append(event)
            events.sort(key=lambda event: event.start)
            return events
        except Exception:
            self._reset_connection()
            return []

    def close(self) -> None:
        """Release cached COM objects and uninitialize COM if needed."""
        self._reset_connection()
        if self._com_initialized:
            try:
                import pythoncom

                pythoncom.CoUninitialize()
            except Exception:
                pass
            self._com_initialized = False

    def _connect(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._namespace is not None:
            return True

        try:
            import pythoncom
        except ImportError:
            return False

        if not self._com_initialized:
            pythoncom.CoInitialize()
            self._com_initialized = True

        try:
            self._outlook = _attach_outlook_application()
            self._namespace = self._outlook.GetNamespace("MAPI")
            return True
        except Exception:
            self._reset_connection()
            return False

    def _reset_connection(self) -> None:
        self._outlook = None
        self._namespace = None

    def _collect_mail_items(self, items: Any, max_count: int) -> list[MailItem]:
        result: list[MailItem] = []
        for item in self._iter_com_items(items):
            mail = self._mail_item_from_com(item)
            if mail is None:
                continue
            result.append(mail)
            if len(result) >= max_count:
                break
        return result

    def _iter_com_items(self, items: Any):
        try:
            count = int(items.Count)
        except Exception:
            return
        for index in range(1, count + 1):
            try:
                yield items.Item(index)
            except Exception:
                continue

    def _mail_item_from_com(self, item: Any) -> MailItem | None:
        try:
            if int(getattr(item, "Class", 0)) != OL_MAIL_ITEM:
                return None
        except Exception:
            return None

        try:
            entry_id = _safe_str(getattr(item, "EntryID", ""))
            if not entry_id:
                return None

            subject = _safe_str(getattr(item, "Subject", ""), "(no subject)")
            sender_name = _safe_str(getattr(item, "SenderName", ""), "(unknown)")
            sender_email = self._sender_email_from_mail_item(item)
            received_at = _com_to_datetime(getattr(item, "ReceivedTime", datetime.datetime.now()))
            store_id = self._store_id_from_item(item)
            return MailItem(
                entry_id=entry_id,
                subject=subject,
                sender_name=sender_name,
                sender_email=sender_email,
                received_at=received_at,
                store_id=store_id,
            )
        except Exception:
            return None

    def _calendar_event_from_com(self, item: Any) -> CalendarEvent | None:
        try:
            if int(getattr(item, "Class", 0)) != OL_APPOINTMENT_ITEM:
                return None
        except Exception:
            return None

        try:
            entry_id = _safe_str(getattr(item, "EntryID", ""))
            if not entry_id:
                return None

            subject = _safe_str(getattr(item, "Subject", ""), "(no subject)")
            start = _com_to_datetime(getattr(item, "Start", datetime.datetime.now()))
            end = _com_to_datetime(getattr(item, "End", start))
            location = _safe_str(getattr(item, "Location", ""))
            global_id = _safe_str(getattr(item, "GlobalAppointmentID", "")) or None
            is_all_day = bool(getattr(item, "AllDayEvent", False))
            return CalendarEvent(
                entry_id=entry_id,
                subject=subject,
                start=start,
                end=end,
                location=location,
                global_appointment_id=global_id,
                is_all_day=is_all_day,
            )
        except Exception:
            return None

    def _sender_email_from_mail_item(self, item: Any) -> str:
        address = _safe_str(getattr(item, "SenderEmailAddress", ""))
        if "@" in address and not address.startswith("/"):
            return address
        try:
            smtp = item.PropertyAccessor.GetProperty(PR_SENDER_SMTP_ADDRESS)
            if smtp:
                return _safe_str(smtp)
        except Exception:
            pass
        return address or "(unknown)"

    def _store_id_from_item(self, item: Any) -> str | None:
        try:
            parent = getattr(item, "Parent", None)
            if parent is None:
                return None
            store = getattr(parent, "Store", None)
            if store is None:
                store_id = getattr(parent, "StoreID", None)
                return _safe_str(store_id) or None
            store_id = getattr(store, "StoreID", None)
            return _safe_str(store_id) or None
        except Exception:
            return None
