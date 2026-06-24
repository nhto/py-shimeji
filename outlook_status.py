"""Manage Outlook connection state and tray unread polling."""

from __future__ import annotations

from enum import Enum
from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config import (
    get_outlook_mail_poll_interval_sec,
    get_outlook_source,
    outlook_com_supported,
    outlook_graph_configured,
    outlook_integration_available,
    set_outlook_enabled,
)
from outlook_backend import create_outlook_backend
from outlook_com_client import is_outlook_installed
from outlook_graph_auth import clear_graph_token_cache


class OutlookConnectionState(Enum):
    UNSUPPORTED = "unsupported"
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"
    NEEDS_CONFIG = "needs_config"


class OutlookStatusManager(QObject):
    """Attach to Outlook via Microsoft Graph or classic COM."""

    status_changed = pyqtSignal()
    unread_count_changed = pyqtSignal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend: Any = create_outlook_backend()
        self._source = get_outlook_source()
        self._state = self._initial_state()
        self._email: str | None = None
        self._unread_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)

    @property
    def source(self) -> str:
        return self._source

    @property
    def state(self) -> OutlookConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == OutlookConnectionState.CONNECTED

    @property
    def email(self) -> str | None:
        return self._email

    @property
    def unread_count(self) -> int:
        return self._unread_count

    def reload_backend(self) -> None:
        """Recreate the backend after settings change the connection type."""
        self._backend.close()
        self._source = get_outlook_source()
        self._backend = create_outlook_backend(self._source)
        if not self.is_connected:
            self._state = self._initial_state()
            self.status_changed.emit()

    def try_restore_connection(self) -> bool:
        """Reconnect when Outlook integration was enabled in settings."""
        self.reload_backend()
        return self.connect_outlook()

    def connect_outlook(self) -> bool:
        """Connect via Graph (browser sign-in) or classic COM."""
        self.reload_backend()

        if not outlook_integration_available():
            self._set_state(OutlookConnectionState.UNSUPPORTED)
            return False

        if self._source == "graph":
            if not outlook_graph_configured():
                self._fail_before_connect(OutlookConnectionState.NEEDS_CONFIG)
                return False
            connected = self._backend.connect(interactive=True)
        else:
            if not outlook_com_supported():
                self._fail_before_connect(OutlookConnectionState.UNSUPPORTED)
                return False
            connected = self._backend.is_available()

        if connected:
            self._email = self._backend.get_current_user_email()
            self._unread_count = self._backend.get_unread_inbox_count() or 0
            self._set_state(OutlookConnectionState.CONNECTED)
            set_outlook_enabled(True)
            self._restart_timer()
            self.unread_count_changed.emit(self._unread_count)
            self.status_changed.emit()
            return True

        self._fail_before_connect(self._detect_failure_state())
        return False

    def disconnect_outlook(self, *, sign_out: bool = False) -> None:
        """Stop polling. Optionally clear saved Graph tokens."""
        self._stop_timer()
        self._email = None
        self._unread_count = 0
        if sign_out and self._source == "graph":
            clear_graph_token_cache()
        if outlook_integration_available():
            self._set_state(OutlookConnectionState.DISCONNECTED)
        else:
            self._set_state(OutlookConnectionState.UNSUPPORTED)
        set_outlook_enabled(False)
        self._backend.close()
        self.unread_count_changed.emit(0)
        self.status_changed.emit()

    def refresh(self) -> None:
        """Refresh unread count while connected."""
        if not self.is_connected:
            return

        if self._source == "graph":
            if not self._backend.connect(interactive=False):
                self._fail_connection()
                return
        elif not self._backend.is_available():
            self._fail_connection()
            return

        email = self._backend.get_current_user_email()
        unread = self._backend.get_unread_inbox_count()
        if unread is None:
            self._fail_connection()
            return

        self._email = email
        if unread != self._unread_count:
            self._unread_count = unread
            self.unread_count_changed.emit(unread)
        self.status_changed.emit()

    def shutdown(self) -> None:
        """Release resources on application exit."""
        self._stop_timer()
        self._backend.close()

    def _initial_state(self) -> OutlookConnectionState:
        if not outlook_integration_available():
            return OutlookConnectionState.UNSUPPORTED
        if get_outlook_source() == "graph" and not outlook_graph_configured():
            return OutlookConnectionState.NEEDS_CONFIG
        return OutlookConnectionState.DISCONNECTED

    def _fail_before_connect(self, state: OutlookConnectionState) -> None:
        self._email = None
        self._unread_count = 0
        self._set_state(state)
        set_outlook_enabled(False)
        self._stop_timer()
        self.unread_count_changed.emit(0)
        self.status_changed.emit()

    def _fail_connection(self) -> None:
        self._fail_before_connect(self._detect_failure_state())

    def _detect_failure_state(self) -> OutlookConnectionState:
        if self._source == "graph":
            if not outlook_graph_configured():
                return OutlookConnectionState.NEEDS_CONFIG
            return OutlookConnectionState.BLOCKED
        if not outlook_com_supported():
            return OutlookConnectionState.UNSUPPORTED
        if not is_outlook_installed():
            return OutlookConnectionState.UNAVAILABLE
        return OutlookConnectionState.BLOCKED

    def _set_state(self, state: OutlookConnectionState) -> None:
        self._state = state

    def _restart_timer(self) -> None:
        interval_ms = max(1, get_outlook_mail_poll_interval_sec()) * 1000
        self._timer.start(interval_ms)

    def _stop_timer(self) -> None:
        self._timer.stop()
