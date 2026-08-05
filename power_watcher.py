"""Hide pets when the system sleeps and restore on resume (Windows)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import QAbstractNativeEventFilter, QObject

if TYPE_CHECKING:
    from pet_window import PetWindow

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    WM_POWERBROADCAST = 0x0218
    PBT_APMSUSPEND = 0x0004
    PBT_APMRESUMECRITICAL = 0x0006
    PBT_APMRESUMESUSPEND = 0x0007
else:
    WM_POWERBROADCAST = 0
    PBT_APMSUSPEND = 0
    PBT_APMRESUMECRITICAL = 0
    PBT_APMRESUMESUSPEND = 0


class _PowerEventFilter(QAbstractNativeEventFilter):
    def __init__(self, watcher: "PowerStateWatcher") -> None:
        super().__init__()
        self._watcher = watcher

    def nativeEventFilter(self, event_type, message):  # type: ignore[override]
        if sys.platform != "win32" or event_type != b"windows_generic_MSG":
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message != WM_POWERBROADCAST:
            return False, 0
        if self._watcher.handle_power_event(int(msg.wParam)):
            return True, 0
        return False, 0


class PowerStateWatcher(QObject):
    """Hide visible pets on system suspend and restore them on resume."""

    def __init__(
        self,
        pets: list[PetWindow],
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pets = pets
        self._enabled = sys.platform == "win32"
        self._suspended = False
        self._visibility_snapshot: list[bool] = []
        self._filter: _PowerEventFilter | None = None
        if self._enabled:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                self._filter = _PowerEventFilter(self)
                app.installNativeEventFilter(self._filter)

    def handle_power_event(self, event: int) -> bool:
        """Handle a WM_POWERBROADCAST wParam value. Returns True when consumed."""
        if event == PBT_APMSUSPEND:
            self._on_suspend()
            return True
        if event in (PBT_APMRESUMECRITICAL, PBT_APMRESUMESUSPEND):
            self._on_resume()
            return True
        return False

    def set_pets(self, pets: list[PetWindow]) -> None:
        """Update the pet list when pets are added or removed at runtime."""
        if self._suspended:
            for pet in pets:
                if pet.isVisible():
                    pet.hide()
        self._pets = pets
        if self._suspended:
            old_len = len(self._visibility_snapshot)
            new_len = len(pets)
            if new_len > old_len:
                self._visibility_snapshot.extend([False] * (new_len - old_len))
            else:
                self._visibility_snapshot = self._visibility_snapshot[:new_len]

    def shutdown(self) -> None:
        if self._filter is not None:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.removeNativeEventFilter(self._filter)
            self._filter = None

    def _on_suspend(self) -> None:
        if self._suspended:
            return
        self._suspended = True
        self._visibility_snapshot = [pet.isVisible() for pet in self._pets]
        for pet in self._pets:
            if pet.isVisible():
                pet.hide()

    def _on_resume(self) -> None:
        if not self._suspended:
            return
        self._suspended = False
        for pet, was_visible in zip(self._pets, self._visibility_snapshot, strict=False):
            if was_visible:
                pet.show()
        self._visibility_snapshot = []
