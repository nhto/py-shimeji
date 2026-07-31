"""Live desktop state for chat context (time, power, app state, optional window/clipboard)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from chat_context import BatteryStatus, format_desktop_chat_context

if TYPE_CHECKING:
    from pet_window import PetWindow

_MAX_CLIPBOARD_CHARS = 120
_MAX_WINDOW_TITLE_CHARS = 80


@dataclass(frozen=True)
class BatteryStatus:
    """Current power/battery snapshot."""

    on_ac: bool | None
    percent: int | None
    charging: bool | None = None


def _truncate_text(text: str, max_chars: int) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 1].rstrip() + "…"


def read_battery_status() -> BatteryStatus | None:
    """Return battery/power info when available on this platform."""
    if sys.platform == "win32":
        return _read_battery_status_windows()
    return None


def _read_battery_status_windows() -> BatteryStatus | None:
    import ctypes

    class _SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_byte),
            ("BatteryFlag", ctypes.c_byte),
            ("BatteryLifePercent", ctypes.c_byte),
            ("SystemStatusFlag", ctypes.c_byte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = _SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None

    on_ac: bool | None
    if status.ACLineStatus == 1:
        on_ac = True
    elif status.ACLineStatus == 0:
        on_ac = False
    else:
        on_ac = None

    percent: int | None = None
    if 0 <= status.BatteryLifePercent <= 100:
        percent = int(status.BatteryLifePercent)

    charging: bool | None = None
    if status.BatteryFlag == 3:
        charging = True
    elif status.BatteryFlag in (1, 2):
        charging = False

    if on_ac is None and percent is None:
        return None
    return BatteryStatus(on_ac=on_ac, percent=percent, charging=charging)


def read_active_window_title(exclude_hwnds: set[int] | None = None) -> str | None:
    """Return the foreground window title, excluding py-shimeji windows."""
    if sys.platform != "win32":
        return None

    import ctypes

    user32 = ctypes.windll.user32
    hwnd = int(user32.GetForegroundWindow())
    if not hwnd:
        return None
    if exclude_hwnds and hwnd in exclude_hwnds:
        return None

    length = int(user32.GetWindowTextLengthW(hwnd))
    if length <= 0:
        return None

    buffer = ctypes.create_unicode_buffer(length + 1)
    copied = int(user32.GetWindowTextW(hwnd, buffer, length + 1))
    if copied <= 0:
        return None

    title = buffer.value.strip()
    if not title:
        return None
    return _truncate_text(title, _MAX_WINDOW_TITLE_CHARS)


def read_clipboard_summary() -> str | None:
    """Return a short plain-text clipboard preview when available."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return None

    text = app.clipboard().text()
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    return _truncate_text(text, _MAX_CLIPBOARD_CHARS)


class DesktopChatContext:
    """Provider for local desktop context injected into chat prompts."""

    def __init__(
        self,
        pets: list[PetWindow],
        exclude_hwnds: set[int] | None = None,
    ) -> None:
        self._pets = pets
        self._exclude_hwnds = exclude_hwnds or set()

    def chat_context(self) -> str | None:
        from settings.chat import (
            get_chat_context_include_active_window,
            get_chat_context_include_clipboard,
        )

        motion_paused = bool(self._pets) and all(
            pet.motion_paused for pet in self._pets
        )
        click_through = bool(self._pets) and all(
            pet.click_through for pet in self._pets
        )

        active_window: str | None = None
        if get_chat_context_include_active_window():
            active_window = read_active_window_title(self._exclude_hwnds)

        clipboard: str | None = None
        if get_chat_context_include_clipboard():
            clipboard = read_clipboard_summary()

        return format_desktop_chat_context(
            now=datetime.now().astimezone(),
            battery=read_battery_status(),
            motion_paused=motion_paused,
            click_through=click_through,
            active_window_title=active_window,
            clipboard_text=clipboard,
        )
