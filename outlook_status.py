"""Manage Outlook connection state and tray unread polling."""

from __future__ import annotations

from enum import Enum
from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config import (
    get_outlook_enabled,
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
from outlook_poll_worker import OutlookPollFailure, OutlookPollFailureReason


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
        self._poll_refresh_delegated = False
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

    def set_poll_refresh_delegated(self, delegated: bool) -> None:
        """When True, OutlookMonitor owns unread refresh; pause the status timer."""
        self._poll_refresh_delegated = bool(delegated)
        if delegated:
            self._stop_timer()
        elif self.is_connected and get_outlook_enabled():
            self._restart_timer()

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
            if not self._poll_refresh_delegated:
                self._restart_timer()
            self.unread_count_changed.emit(self._unread_count)
            self.status_changed.emit()
            return True

        self._fail_before_connect(self._detect_failure_state())
        return False

    def report_connection_lost(
        self,
        *,
        failure: OutlookPollFailure | None = None,
    ) -> None:
        """Mark Outlook unreachable while keeping integration enabled for retry."""
        if not get_outlook_enabled():
            return
        self._email = None
        self._unread_count = 0
        self._set_state(self._state_from_poll_failure(failure))
        self._stop_timer()
        self.unread_count_changed.emit(0)
        self.status_changed.emit()

    def report_connection_ok(
        self,
        email: str | None,
        unread_count: int | None,
    ) -> None:
        """Restore connected state after a successful poll cycle."""
        if not get_outlook_enabled():
            return
        was_connected = self.is_connected
        previous_unread = self._unread_count
        self._email = email
        count = unread_count if unread_count is not None else 0
        self._set_state(OutlookConnectionState.CONNECTED)
        if not was_connected and not self._poll_refresh_delegated:
            self._restart_timer()
        self._unread_count = count
        if count != previous_unread:
            self.unread_count_changed.emit(count)
        elif not was_connected:
            self.status_changed.emit()

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
            self.report_connection_lost()
            return

        self.report_connection_ok(email, unread)

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
        self.report_connection_lost()

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

    def _state_from_poll_failure(
        self,
        failure: OutlookPollFailure | None,
    ) -> OutlookConnectionState:
        if failure is None:
            return self._detect_failure_state()

        if failure.reason == OutlookPollFailureReason.NOT_CONFIGURED:
            return OutlookConnectionState.NEEDS_CONFIG
        if failure.reason == OutlookPollFailureReason.AUTH_EXPIRED:
            return OutlookConnectionState.BLOCKED
        if failure.reason == OutlookPollFailureReason.CONNECTION_LOST:
            if self._source != "graph" and not is_outlook_installed():
                return OutlookConnectionState.UNAVAILABLE
            return OutlookConnectionState.BLOCKED
        if failure.reason == OutlookPollFailureReason.COM_ERROR:
            return OutlookConnectionState.BLOCKED
        return self._detect_failure_state()

    def _set_state(self, state: OutlookConnectionState) -> None:
        self._state = state

    def _restart_timer(self) -> None:
        interval_ms = max(1, get_outlook_mail_poll_interval_sec()) * 1000
        self._timer.start(interval_ms)

    def _stop_timer(self) -> None:
        self._timer.stop()
