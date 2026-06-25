"""Real-time classic Outlook inbox events via COM (Windows only)."""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from outlook_com_client import OutlookComClient, mail_item_from_com
from outlook_logging import format_mail_log_summary
from outlook_models import MailItem

_logger = logging.getLogger(__name__)

_COM_PUMP_INTERVAL_MS = 100
_on_item_add_callback: Callable[[Any], None] | None = None
_on_new_mail_ex_callback: Callable[[str], None] | None = None


class _InboxItemsEventSink:
    """COM event sink for MAPI inbox Items.OnItemAdd."""

    def OnItemAdd(self, item: Any) -> None:  # noqa: N802 - COM event name
        if _on_item_add_callback is not None:
            _on_item_add_callback(item)


class _OutlookApplicationEventSink:
    """COM event sink for Application.NewMailEx (more reliable in New Outlook)."""

    def OnNewMailEx(self, entry_ids_collection: str) -> None:  # noqa: N802
        if _on_new_mail_ex_callback is not None:
            _on_new_mail_ex_callback(entry_ids_collection)


class OutlookComMailEventSource(QObject):
    """Listen for new inbox mail on the Qt main thread with a COM message pump."""

    mail_received = pyqtSignal(object)
    unavailable = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._client = OutlookComClient()
        self._inbox_event_sink: Any | None = None
        self._application_event_sink: Any | None = None
        self._active = False
        self._pump_timer = QTimer(self)
        self._pump_timer.setInterval(_COM_PUMP_INTERVAL_MS)
        self._pump_timer.timeout.connect(self._pump_com_messages)

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self) -> bool:
        """Attach to the default inbox and begin pumping COM events."""
        if sys.platform != "win32" or self._active:
            return self._active

        global _on_item_add_callback, _on_new_mail_ex_callback
        try:
            if not self._client.is_available():
                return False

            import win32com.client

            inbox_items = self._client.get_inbox_items()
            if inbox_items is None:
                return False

            _on_item_add_callback = self._handle_com_item_add
            _on_new_mail_ex_callback = self._handle_new_mail_ex
            self._inbox_event_sink = win32com.client.WithEvents(
                inbox_items, _InboxItemsEventSink
            )

            outlook_app = self._client.get_outlook_application()
            if outlook_app is not None:
                try:
                    self._application_event_sink = win32com.client.WithEvents(
                        outlook_app, _OutlookApplicationEventSink
                    )
                except Exception:
                    _logger.warning("Application.NewMailEx events unavailable", exc_info=True)

            self._active = True
            self._pump_timer.start()
            return True
        except Exception:
            _logger.exception("Failed to start Outlook inbox event sink")
            self.stop()
            return False

    def stop(self) -> None:
        """Detach from inbox events and release COM resources."""
        global _on_item_add_callback, _on_new_mail_ex_callback

        self._active = False
        self._pump_timer.stop()
        self._inbox_event_sink = None
        self._application_event_sink = None
        _on_item_add_callback = None
        _on_new_mail_ex_callback = None
        self._client.close()

    def _pump_com_messages(self) -> None:
        if not self._active:
            return
        try:
            import pythoncom

            pythoncom.PumpWaitingMessages()
        except Exception:
            _logger.exception("Outlook COM message pump failed")
            self.unavailable.emit()
            self.stop()

    def _handle_new_mail_ex(self, entry_ids_collection: str) -> None:
        for raw_id in entry_ids_collection.split(","):
            entry_id = raw_id.strip()
            if not entry_id:
                continue
            item = self._client.get_mail_item_by_entry_id(entry_id)
            if item is not None:
                self._handle_com_item_add(item)

    def _handle_com_item_add(self, item: Any) -> None:
        try:
            if not bool(getattr(item, "UnRead", False)):
                return
        except Exception:
            pass

        mail = mail_item_from_com(item)
        if mail is None:
            return
        _logger.info("COM mail event: %s", format_mail_log_summary(mail))
        self.mail_received.emit(mail)
