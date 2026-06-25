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
from outlook_models import CalendarEvent, MailItem, MailStore
from outlook_text import extract_teams_join_url, plain_text_first_line

try:
    from config import (
        get_outlook_include_shared_mailboxes,
        get_outlook_mailbox_store_ids,
    )
except ImportError:  # pragma: no cover - script import edge case
    def get_outlook_include_shared_mailboxes() -> bool:
        return False

    def get_outlook_mailbox_store_ids() -> list[str]:
        return []

_OUTLOOK_START_TIMEOUT_SEC = 45
_CALENDAR_SCAN_LIMIT = 500
_OL_IMPORTANCE_HIGH = 2


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
        """Return the unread message count across configured inboxes."""
        if not self._connect():
            return None
        total = 0
        found = False
        for inbox in self._iter_inboxes():
            try:
                total += int(inbox.Items.Restrict("[UnRead] = True").Count)
                found = True
            except Exception:
                continue
        if not found:
            self._reset_connection()
            return None
        return total

    def list_unread_messages(self, max_count: int = 10) -> list[MailItem]:
        """Return up to max_count unread messages from configured inboxes."""
        if max_count <= 0 or not self._connect():
            return []

        collected: list[MailItem] = []
        seen_entry_ids: set[str] = set()
        for inbox in self._iter_inboxes():
            try:
                restricted = inbox.Items.Restrict("[UnRead] = True")
                restricted.Sort("[ReceivedTime]", True)
                for mail in self._collect_mail_items(restricted, max_count):
                    if mail.entry_id in seen_entry_ids:
                        continue
                    seen_entry_ids.add(mail.entry_id)
                    collected.append(mail)
                    if len(collected) >= max_count:
                        break
            except Exception:
                continue
            if len(collected) >= max_count:
                break

        collected.sort(key=lambda mail: mail.received_at, reverse=True)
        return collected[:max_count]

    def list_mail_stores(self) -> list[MailStore]:
        """Return mail stores in the signed-in Outlook profile."""
        if not self._connect():
            return []
        stores: list[MailStore] = []
        for store in self._iter_stores():
            store_id = _safe_str(getattr(store, "StoreID", ""))
            if not store_id:
                continue
            display_name = _safe_str(getattr(store, "DisplayName", ""), store_id)
            stores.append(MailStore(store_id=store_id, display_name=display_name))
        return stores

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

    def get_inbox_items(self) -> Any | None:
        """Return the default inbox Items collection for COM event sinks."""
        if not self._connect():
            return None
        assert self._namespace is not None
        try:
            inbox = self._namespace.GetDefaultFolder(OL_FOLDER_INBOX)
            return inbox.Items
        except Exception:
            self._reset_connection()
            return None

    def get_outlook_application(self) -> Any | None:
        """Return the Outlook.Application COM object when connected."""
        if not self._connect():
            return None
        return self._outlook

    def get_mail_item_by_entry_id(self, entry_id: str) -> Any | None:
        """Fetch a single MAPI item by entry ID."""
        if not entry_id or not self._connect():
            return None
        assert self._namespace is not None
        try:
            return self._namespace.GetItemFromID(entry_id)
        except Exception:
            return None

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

    def _iter_stores(self):
        assert self._namespace is not None
        try:
            stores = self._namespace.Stores
            count = int(stores.Count)
        except Exception:
            return
        for index in range(1, count + 1):
            try:
                yield stores.Item(index)
            except Exception:
                continue

    def _inbox_for_store_id(self, store_id: str) -> Any | None:
        for store in self._iter_stores():
            if _safe_str(getattr(store, "StoreID", "")) != store_id:
                continue
            try:
                return store.GetDefaultFolder(OL_FOLDER_INBOX)
            except Exception:
                return None
        return None

    def _iter_inboxes(self):
        assert self._namespace is not None
        store_ids = get_outlook_mailbox_store_ids()
        if store_ids:
            for store_id in store_ids:
                inbox = self._inbox_for_store_id(store_id)
                if inbox is not None:
                    yield inbox
            return

        if get_outlook_include_shared_mailboxes():
            for store in self._iter_stores():
                try:
                    yield store.GetDefaultFolder(OL_FOLDER_INBOX)
                except Exception:
                    continue
            return

        try:
            yield self._namespace.GetDefaultFolder(OL_FOLDER_INBOX)
        except Exception:
            return

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
        return mail_item_from_com(item)

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
            body = _safe_str(getattr(item, "Body", ""))
            online_meeting_url = extract_teams_join_url(location, body)
            return CalendarEvent(
                entry_id=entry_id,
                subject=subject,
                start=start,
                end=end,
                location=location,
                online_meeting_url=online_meeting_url,
                global_appointment_id=global_id,
                is_all_day=is_all_day,
            )
        except Exception:
            return None

    def _sender_email_from_mail_item(self, item: Any) -> str:
        return sender_email_from_com_mail_item(item)

    def _store_id_from_item(self, item: Any) -> str | None:
        return store_id_from_com_item(item)


def sender_email_from_com_mail_item(item: Any) -> str:
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


def store_id_from_com_item(item: Any) -> str | None:
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


def mail_item_from_com(item: Any) -> MailItem | None:
    """Convert a classic Outlook COM mail item into a MailItem."""
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
        sender_email = sender_email_from_com_mail_item(item)
        received_at = _com_to_datetime(getattr(item, "ReceivedTime", datetime.datetime.now()))
        store_id = store_id_from_com_item(item)
        body_preview = plain_text_first_line(_safe_str(getattr(item, "Body", "")))
        try:
            is_high_importance = int(getattr(item, "Importance", 1)) == _OL_IMPORTANCE_HIGH
        except Exception:
            is_high_importance = False
        return MailItem(
            entry_id=entry_id,
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            received_at=received_at,
            store_id=store_id,
            body_preview=body_preview,
            is_high_importance=is_high_importance,
        )
    except Exception:
        return None
