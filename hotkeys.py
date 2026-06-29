"""Global keyboard shortcuts (Windows RegisterHotKey via ctypes)."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass

from PyQt6.QtCore import QAbstractNativeEventFilter
from PyQt6.QtWidgets import QApplication, QWidget

from config import HOTKEY_ACTIONS, get_hotkey_binding

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    WM_HOTKEY = 0x0312
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008

    _VK_BY_NAME: dict[str, int] = {
        "backspace": 0x08,
        "tab": 0x09,
        "enter": 0x0D,
        "return": 0x0D,
        "escape": 0x1B,
        "esc": 0x1B,
        "space": 0x20,
        "pageup": 0x21,
        "pagedown": 0x22,
        "end": 0x23,
        "home": 0x24,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
        "insert": 0x2D,
        "delete": 0x2E,
    }
    for _index in range(1, 13):
        _VK_BY_NAME[f"f{_index}"] = 0x6F + _index


@dataclass(frozen=True)
class ParsedHotkey:
    modifiers: int
    vk: int


def _parse_hotkey(binding: str) -> ParsedHotkey | None:
    """Parse strings like ``Ctrl+Alt+P`` into Windows modifier and virtual-key codes."""
    if sys.platform != "win32":
        return None

    parts = [part.strip() for part in binding.split("+") if part.strip()]
    if not parts:
        return None

    modifiers = 0
    key_token: str | None = None
    for part in parts:
        token = part.lower()
        if token in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif token == "alt":
            modifiers |= MOD_ALT
        elif token == "shift":
            modifiers |= MOD_SHIFT
        elif token in ("win", "super", "meta"):
            modifiers |= MOD_WIN
        else:
            if key_token is not None:
                return None
            key_token = token

    if key_token is None or modifiers == 0:
        return None

    if key_token in _VK_BY_NAME:
        vk = _VK_BY_NAME[key_token]
    elif len(key_token) == 1 and key_token.isalnum():
        vk = ord(key_token.upper())
    else:
        return None

    return ParsedHotkey(modifiers=modifiers, vk=vk)


class _HotkeyEventFilter(QAbstractNativeEventFilter):
    def __init__(self, manager: "GlobalHotkeyManager") -> None:
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, event_type, message):  # type: ignore[override]
        if sys.platform != "win32" or event_type != b"windows_generic_MSG":
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY:
            self._manager._on_hotkey(int(msg.wParam))
            return True, 0
        return False, 0


class GlobalHotkeyManager:
    """Register system-wide hotkeys and dispatch them on the Qt main thread."""

    def __init__(self, parent: QWidget | None = None) -> None:
        self._enabled = sys.platform == "win32"
        self._hwnd_widget = parent
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._registered: dict[int, str] = {}
        self._filter: _HotkeyEventFilter | None = None
        if self._enabled and parent is not None:
            app = QApplication.instance()
            if app is not None:
                self._filter = _HotkeyEventFilter(self)
                app.installNativeEventFilter(self._filter)

    def register(self, action: str, callback: Callable[[], None]) -> None:
        if action not in HOTKEY_ACTIONS:
            raise ValueError(f"Unknown hotkey action: {action}")
        self._callbacks[action] = callback

    def reload(self) -> None:
        """Unregister all hotkeys and apply bindings from config."""
        if not self._enabled or self._hwnd_widget is None:
            return

        hwnd = int(self._hwnd_widget.winId())
        for hotkey_id in list(self._registered):
            _user32.UnregisterHotKey(hwnd, hotkey_id)
        self._registered.clear()

        for index, action in enumerate(HOTKEY_ACTIONS, start=1):
            binding = get_hotkey_binding(action)
            if not binding:
                continue
            parsed = _parse_hotkey(binding)
            if parsed is None:
                continue
            if not _user32.RegisterHotKey(hwnd, index, parsed.modifiers, parsed.vk):
                continue
            self._registered[index] = action

    def shutdown(self) -> None:
        if not self._enabled or self._hwnd_widget is None:
            return

        hwnd = int(self._hwnd_widget.winId())
        for hotkey_id in list(self._registered):
            _user32.UnregisterHotKey(hwnd, hotkey_id)
        self._registered.clear()

        if self._filter is not None:
            app = QApplication.instance()
            if app is not None:
                app.removeNativeEventFilter(self._filter)
            self._filter = None

    def _on_hotkey(self, hotkey_id: int) -> None:
        action = self._registered.get(hotkey_id)
        if action is None:
            return
        callback = self._callbacks.get(action)
        if callback is not None:
            callback()
