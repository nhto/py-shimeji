"""Poll Outlook for new mail and upcoming meetings; notify pets."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config import (
    format_speech_bubble_text,
    get_outlook_calendar_enabled,
    get_outlook_calendar_poll_interval_sec,
    get_outlook_enabled,
    get_outlook_mail_enabled,
    get_outlook_mail_poll_interval_sec,
    get_outlook_meeting_reminder_minutes,
    get_outlook_reminded_events,
    get_outlook_seen_mail_entry_ids,
    get_outlook_source,
    set_outlook_reminded_events,
    set_outlook_seen_mail_entry_ids,
)
from outlook_models import CalendarEvent, MailItem
from outlook_poll_worker import OutlookPollResult, OutlookPollWorker
from pet_window import PetWindow

TrayNotifier = Callable[[str, str], None]

_MAX_SEEN_MAIL_IDS = 500


def _reminder_key(entry_id: str, minutes: int) -> str:
    return f"{entry_id}|{minutes}"


def format_mail_notification(mail: MailItem) -> str:
    sender = mail.sender_name.strip() or mail.sender_email
    return f"📧 {sender}: {mail.subject}"


def format_meeting_notification(event: CalendarEvent, minutes_left: int) -> str:
    title = event.subject.strip() or "(meeting)"
    if minutes_left <= 0:
        return f"📅 {title} now"
    return f"📅 {title} in {minutes_left} min"


class OutlookMonitor(QObject):
    """Timer-driven Outlook polling with deduplication and pet alerts."""

    mail_received = pyqtSignal(MailItem)
    meeting_soon = pyqtSignal(CalendarEvent, int)

    def __init__(
        self,
        pets: list[PetWindow],
        *,
        outlook_status: object | None = None,
        tray_notifier: TrayNotifier | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pets = pets
        self._outlook_status = outlook_status
        self._tray_notifier = tray_notifier
        self._running = False
        self._mail_baseline_pending = True
        self._worker: OutlookPollWorker | None = None
        self._pending_poll_mail = False
        self._pending_poll_calendar = False

        self._mail_timer = QTimer(self)
        self._mail_timer.timeout.connect(self._poll_mail)
        self._calendar_timer = QTimer(self)
        self._calendar_timer.timeout.connect(self._poll_calendar)

        self.mail_received.connect(self._on_mail_received)
        self.meeting_soon.connect(self._on_meeting_soon)

    def set_tray_notifier(self, notifier: TrayNotifier | None) -> None:
        self._tray_notifier = notifier

    def start(self) -> None:
        """Begin polling when Outlook integration is enabled."""
        if self._running or not get_outlook_enabled():
            return
        self._running = True
        self._mail_baseline_pending = True
        self._restart_timers()
        self._poll_mail()
        self._poll_calendar()

    def stop(self) -> None:
        """Stop polling without clearing Outlook settings."""
        self._running = False
        self._mail_timer.stop()
        self._calendar_timer.stop()
        self._cancel_worker()

    def shutdown(self) -> None:
        """Release resources on application exit."""
        self.stop()

    def _restart_timers(self) -> None:
        mail_ms = max(1, get_outlook_mail_poll_interval_sec()) * 1000
        calendar_ms = max(1, get_outlook_calendar_poll_interval_sec()) * 1000
        if get_outlook_mail_enabled():
            self._mail_timer.start(mail_ms)
        else:
            self._mail_timer.stop()
        if get_outlook_calendar_enabled():
            self._calendar_timer.start(calendar_ms)
        else:
            self._calendar_timer.stop()

    def _poll_mail(self) -> None:
        if not self._running or not get_outlook_mail_enabled():
            return
        self._queue_poll(poll_mail=True, poll_calendar=False)

    def _poll_calendar(self) -> None:
        if not self._running or not get_outlook_calendar_enabled():
            return
        self._queue_poll(poll_mail=False, poll_calendar=True)

    def _queue_poll(self, *, poll_mail: bool, poll_calendar: bool) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._pending_poll_mail = self._pending_poll_mail or poll_mail
            self._pending_poll_calendar = self._pending_poll_calendar or poll_calendar
            return
        self._start_worker(poll_mail=poll_mail, poll_calendar=poll_calendar)

    def _start_worker(self, *, poll_mail: bool, poll_calendar: bool) -> None:
        self._worker = OutlookPollWorker(
            poll_mail=poll_mail,
            poll_calendar=poll_calendar,
            source=get_outlook_source(),
            parent=self,
        )
        self._worker.poll_complete.connect(self._on_poll_complete)
        self._worker.poll_failed.connect(self._on_poll_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _cancel_worker(self) -> None:
        if self._worker is None:
            return
        if self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(3000)
        self._worker = None
        self._pending_poll_mail = False
        self._pending_poll_calendar = False

    def _on_worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        if not self._running:
            return
        if self._pending_poll_mail or self._pending_poll_calendar:
            poll_mail = self._pending_poll_mail
            poll_calendar = self._pending_poll_calendar
            self._pending_poll_mail = False
            self._pending_poll_calendar = False
            self._start_worker(poll_mail=poll_mail, poll_calendar=poll_calendar)

    def _on_poll_failed(self) -> None:
        if self._outlook_status is not None:
            report = getattr(self._outlook_status, "report_connection_lost", None)
            if callable(report):
                report()

    def _on_poll_complete(self, result: object) -> None:
        if not isinstance(result, OutlookPollResult):
            return

        if self._outlook_status is not None:
            report_ok = getattr(self._outlook_status, "report_connection_ok", None)
            if callable(report_ok):
                report_ok(result.email, result.unread_count)

        if result.poll_mail and get_outlook_mail_enabled():
            self._process_mail(result.mail_items)
        if result.poll_calendar and get_outlook_calendar_enabled():
            self._process_calendar(result.calendar_events)

    def _process_mail(self, messages: list[MailItem]) -> None:
        seen_ids = set(get_outlook_seen_mail_entry_ids())
        if self._mail_baseline_pending:
            self._mail_baseline_pending = False
            if not seen_ids:
                self._persist_seen_ids([mail.entry_id for mail in messages])
                return

        new_messages = [mail for mail in messages if mail.entry_id not in seen_ids]
        if not new_messages:
            return

        updated_ids = list(seen_ids)
        for mail in new_messages:
            updated_ids.append(mail.entry_id)
            self.mail_received.emit(mail)
        self._persist_seen_ids(updated_ids)

    def _process_calendar(self, events: list[CalendarEvent]) -> None:
        now = datetime.now()
        reminded = dict(get_outlook_reminded_events())
        thresholds = get_outlook_meeting_reminder_minutes()
        changed = False

        for event in events:
            minutes_left = int((event.start - now).total_seconds() // 60)
            for threshold in thresholds:
                key = _reminder_key(event.entry_id, threshold)
                if key in reminded:
                    continue
                if 0 <= minutes_left <= threshold:
                    reminded[key] = True
                    changed = True
                    self.meeting_soon.emit(event, minutes_left)

        if changed:
            set_outlook_reminded_events(reminded)

    def _persist_seen_ids(self, entry_ids: list[str]) -> None:
        trimmed = entry_ids[-_MAX_SEEN_MAIL_IDS:]
        set_outlook_seen_mail_entry_ids(trimmed)

    def _pick_notify_pet(self) -> PetWindow | None:
        for pet in self._pets:
            if pet.isVisible():
                return pet
        return self._pets[0] if self._pets else None

    def _notify(self, text: str, *, tray_title: str = "py-shimeji") -> None:
        pet = self._pick_notify_pet()
        bubble_text = format_speech_bubble_text(text)
        if bubble_text is not None and pet is not None:
            pet.show_speech_bubble(bubble_text)
            return
        if self._tray_notifier is not None:
            self._tray_notifier(tray_title, text)

    def _on_mail_received(self, mail: MailItem) -> None:
        self._notify(format_mail_notification(mail))

    def _on_meeting_soon(self, event: CalendarEvent, minutes_left: int) -> None:
        self._notify(format_meeting_notification(event, minutes_left))
