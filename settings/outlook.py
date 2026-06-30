"""Outlook integration settings and helpers."""

from __future__ import annotations

import os
import sys

from settings.core import MAX_PETS
from settings.persistence import clamp_int, load_app_settings, save_app_settings

OUTLOOK_SOURCE_GRAPH: str = "graph"
OUTLOOK_SOURCE_COM: str = "com"
OUTLOOK_MAIL_POLL_INTERVAL_SEC_DEFAULT: int = 45
OUTLOOK_CALENDAR_POLL_INTERVAL_SEC_DEFAULT: int = 60
OUTLOOK_MEETING_REMINDER_MINUTES_DEFAULT: list[int] = [15, 5]
OUTLOOK_MAIL_POLL_INTERVAL_SEC_MIN: int = 15
OUTLOOK_MAIL_POLL_INTERVAL_SEC_MAX: int = 3600
OUTLOOK_NOTIFY_PET_FIRST_VISIBLE: int = -1


def outlook_com_supported() -> bool:
    """True when this platform can use classic Outlook COM."""
    return sys.platform == "win32"


def get_azure_client_id() -> str:
    return os.environ.get("AZURE_CLIENT_ID", "").strip()


def get_azure_tenant_id() -> str:
    tenant = os.environ.get("AZURE_TENANT_ID", "organizations").strip()
    return tenant or "organizations"


def outlook_graph_configured() -> bool:
    return bool(get_azure_client_id())


def outlook_integration_available() -> bool:
    """True when at least one Outlook backend can be used."""
    return outlook_graph_configured() or outlook_com_supported()


def outlook_ui_available() -> bool:
    """True when Outlook tray menu and settings should be shown."""
    if sys.platform != "win32":
        return False
    return outlook_integration_available()


def is_new_outlook_preferred() -> bool:
    """Best-effort detection of New Outlook as the active mail client."""
    if sys.platform != "win32":
        return True
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Office\16.0\Outlook\Preferences",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "UseNewOutlook")
            return int(value) != 0
    except OSError:
        pass
    try:
        import subprocess

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-AppxPackage -Name Microsoft.OutlookForWindows | Select-Object -First 1",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return "Microsoft.OutlookForWindows" in result.stdout
    except Exception:
        return False


def get_default_outlook_source() -> str:
    """Prefer COM when Graph is not configured (typical for locked-down work accounts)."""
    if outlook_graph_configured() and is_new_outlook_preferred():
        return OUTLOOK_SOURCE_GRAPH
    if outlook_com_supported():
        return OUTLOOK_SOURCE_COM
    return OUTLOOK_SOURCE_GRAPH


def _outlook_settings_raw() -> dict:
    outlook = load_app_settings().get("outlook", {})
    return outlook if isinstance(outlook, dict) else {}


def _normalize_reminder_minutes(value: object) -> list[int]:
    if not isinstance(value, list):
        return list(OUTLOOK_MEETING_REMINDER_MINUTES_DEFAULT)
    minutes: list[int] = []
    for item in value:
        try:
            minute = int(item)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if minute > 0:
            minutes.append(minute)
    if not minutes:
        return list(OUTLOOK_MEETING_REMINDER_MINUTES_DEFAULT)
    return sorted(set(minutes), reverse=True)


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def _normalize_notify_pet_index(value: object) -> int:
    if value == OUTLOOK_NOTIFY_PET_FIRST_VISIBLE:
        return OUTLOOK_NOTIFY_PET_FIRST_VISIBLE
    try:
        index = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return OUTLOOK_NOTIFY_PET_FIRST_VISIBLE
    if index < 0:
        return OUTLOOK_NOTIFY_PET_FIRST_VISIBLE
    return min(index, MAX_PETS - 1)


def get_outlook_source() -> str:
    raw = _outlook_settings_raw().get("source")
    if isinstance(raw, str) and raw.strip().lower() in {OUTLOOK_SOURCE_GRAPH, OUTLOOK_SOURCE_COM}:
        return raw.strip().lower()
    return get_default_outlook_source()


def get_outlook_graph_token_cache() -> str:
    cached = _outlook_settings_raw().get("graph_token_cache")
    return cached if isinstance(cached, str) else ""


def set_outlook_graph_token_cache(cache: str) -> None:
    _save_outlook_partial({"graph_token_cache": cache})


def _outlook_enabled_from_env() -> bool:
    value = os.environ.get("OUTLOOK_COM_ENABLED", "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    value = os.environ.get("OUTLOOK_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_outlook_settings() -> dict:
    """Return normalized Outlook settings with defaults applied."""
    raw = _outlook_settings_raw()
    enabled_default = _outlook_enabled_from_env()
    return {
        "enabled": bool(raw.get("enabled", enabled_default)),
        "source": get_outlook_source(),
        "mail_enabled": bool(raw.get("mail_enabled", True)),
        "mail_events_enabled": bool(raw.get("mail_events_enabled", True)),
        "calendar_enabled": bool(raw.get("calendar_enabled", True)),
        "mail_poll_interval_sec": clamp_int(
            raw.get("mail_poll_interval_sec"),
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MIN,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MAX,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_DEFAULT,
        ),
        "calendar_poll_interval_sec": clamp_int(
            raw.get("calendar_poll_interval_sec"),
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MIN,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MAX,
            OUTLOOK_CALENDAR_POLL_INTERVAL_SEC_DEFAULT,
        ),
        "meeting_reminder_minutes": _normalize_reminder_minutes(
            raw.get("meeting_reminder_minutes")
        ),
        "seen_mail_entry_ids": _normalize_string_list(raw.get("seen_mail_entry_ids")),
        "reminded_events": raw.get("reminded_events")
        if isinstance(raw.get("reminded_events"), dict)
        else {},
        "snoozed_events": raw.get("snoozed_events")
        if isinstance(raw.get("snoozed_events"), dict)
        else {},
        "notify_pet_index": _normalize_notify_pet_index(raw.get("notify_pet_index")),
        "notify_when_paused": bool(raw.get("notify_when_paused", True)),
        "include_shared_mailboxes": bool(raw.get("include_shared_mailboxes", False)),
        "mailbox_store_ids": _normalize_string_list(raw.get("mailbox_store_ids")),
    }


def get_outlook_enabled() -> bool:
    return bool(get_outlook_settings()["enabled"])


def get_outlook_mail_enabled() -> bool:
    return bool(get_outlook_settings()["mail_enabled"])


def get_outlook_mail_events_enabled() -> bool:
    """Real-time inbox events are classic COM only."""
    if get_outlook_source() != OUTLOOK_SOURCE_COM:
        return False
    return bool(get_outlook_settings()["mail_events_enabled"])


def get_outlook_calendar_enabled() -> bool:
    return bool(get_outlook_settings()["calendar_enabled"])


def get_outlook_mail_poll_interval_sec() -> int:
    return int(get_outlook_settings()["mail_poll_interval_sec"])


def get_outlook_calendar_poll_interval_sec() -> int:
    return int(get_outlook_settings()["calendar_poll_interval_sec"])


def get_outlook_meeting_reminder_minutes() -> list[int]:
    return list(get_outlook_settings()["meeting_reminder_minutes"])


def get_outlook_seen_mail_entry_ids() -> list[str]:
    return list(get_outlook_settings()["seen_mail_entry_ids"])


def get_outlook_reminded_events() -> dict:
    reminded = get_outlook_settings()["reminded_events"]
    return dict(reminded) if isinstance(reminded, dict) else {}


def get_outlook_snoozed_events() -> dict:
    snoozed = get_outlook_settings()["snoozed_events"]
    return dict(snoozed) if isinstance(snoozed, dict) else {}


def get_outlook_notify_pet_index() -> int:
    return int(get_outlook_settings()["notify_pet_index"])


def get_outlook_notify_when_paused() -> bool:
    return bool(get_outlook_settings()["notify_when_paused"])


def get_outlook_include_shared_mailboxes() -> bool:
    return bool(get_outlook_settings()["include_shared_mailboxes"])


def get_outlook_mailbox_store_ids() -> list[str]:
    return list(get_outlook_settings()["mailbox_store_ids"])


def _save_outlook_partial(updates: dict) -> None:
    data = load_app_settings()
    outlook = data.setdefault("outlook", {})
    if not isinstance(outlook, dict):
        outlook = {}
        data["outlook"] = outlook
    outlook.update(updates)
    save_app_settings(data)


def set_outlook_enabled(enabled: bool) -> None:
    _save_outlook_partial({"enabled": bool(enabled)})


def set_outlook_mail_enabled(enabled: bool) -> None:
    _save_outlook_partial({"mail_enabled": bool(enabled)})


def set_outlook_mail_events_enabled(enabled: bool) -> None:
    _save_outlook_partial({"mail_events_enabled": bool(enabled)})


def set_outlook_calendar_enabled(enabled: bool) -> None:
    _save_outlook_partial({"calendar_enabled": bool(enabled)})


def set_outlook_settings(
    *,
    source: str | None = None,
    mail_enabled: bool | None = None,
    mail_events_enabled: bool | None = None,
    calendar_enabled: bool | None = None,
    mail_poll_interval_sec: int | None = None,
    calendar_poll_interval_sec: int | None = None,
    meeting_reminder_minutes: list[int] | None = None,
    notify_pet_index: int | None = None,
    notify_when_paused: bool | None = None,
    include_shared_mailboxes: bool | None = None,
    mailbox_store_ids: list[str] | None = None,
) -> None:
    """Persist user-facing Outlook settings from the settings dialog."""
    updates: dict[str, object] = {}
    if source is not None:
        normalized = source.strip().lower()
        if normalized in {OUTLOOK_SOURCE_GRAPH, OUTLOOK_SOURCE_COM}:
            updates["source"] = normalized
    if mail_enabled is not None:
        updates["mail_enabled"] = bool(mail_enabled)
    if mail_events_enabled is not None:
        updates["mail_events_enabled"] = bool(mail_events_enabled)
    if calendar_enabled is not None:
        updates["calendar_enabled"] = bool(calendar_enabled)
    if mail_poll_interval_sec is not None:
        updates["mail_poll_interval_sec"] = clamp_int(
            mail_poll_interval_sec,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MIN,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MAX,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_DEFAULT,
        )
    if calendar_poll_interval_sec is not None:
        updates["calendar_poll_interval_sec"] = clamp_int(
            calendar_poll_interval_sec,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MIN,
            OUTLOOK_MAIL_POLL_INTERVAL_SEC_MAX,
            OUTLOOK_CALENDAR_POLL_INTERVAL_SEC_DEFAULT,
        )
    if meeting_reminder_minutes is not None:
        updates["meeting_reminder_minutes"] = _normalize_reminder_minutes(
            meeting_reminder_minutes
        )
    if notify_pet_index is not None:
        updates["notify_pet_index"] = _normalize_notify_pet_index(notify_pet_index)
    if notify_when_paused is not None:
        updates["notify_when_paused"] = bool(notify_when_paused)
    if include_shared_mailboxes is not None:
        updates["include_shared_mailboxes"] = bool(include_shared_mailboxes)
    if mailbox_store_ids is not None:
        updates["mailbox_store_ids"] = _normalize_string_list(mailbox_store_ids)
    if updates:
        _save_outlook_partial(updates)


def set_outlook_seen_mail_entry_ids(entry_ids: list[str]) -> None:
    _save_outlook_partial({"seen_mail_entry_ids": _normalize_string_list(entry_ids)})


def set_outlook_reminded_events(reminded_events: dict) -> None:
    payload = reminded_events if isinstance(reminded_events, dict) else {}
    _save_outlook_partial({"reminded_events": payload})


def set_outlook_snoozed_events(snoozed_events: dict) -> None:
    payload = snoozed_events if isinstance(snoozed_events, dict) else {}
    _save_outlook_partial({"snoozed_events": payload})
