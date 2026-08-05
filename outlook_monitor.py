"""Poll Outlook for new mail and upcoming meetings; notify pets."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from typing import Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config import (
    MAIL_BODY_PREVIEW_MAX_CHARS,
    MEETING_LOCATION_MAX_CHARS,
    MEETING_SNOOZE_MINUTES,
    OUTLOOK_NOTIFY_PET_FIRST_VISIBLE,
    get_outlook_calendar_enabled,
    get_outlook_calendar_poll_interval_sec,
    get_outlook_enabled,
    get_outlook_mail_enabled,
    get_outlook_mail_events_enabled,
    get_outlook_mail_poll_interval_sec,
    get_outlook_meeting_reminder_minutes,
    get_outlook_notify_pet_index,
    get_outlook_notify_when_paused,
    get_outlook_reminded_events,
    get_outlook_seen_mail_entry_ids,
    get_outlook_snoozed_events,
    get_outlook_source,
    set_outlook_reminded_events,
    set_outlook_seen_mail_entry_ids,
    set_outlook_snoozed_events,
)
from outlook_logging import format_event_log_summary, format_mail_log_summary
from outlook_models import CalendarEvent, MailItem
from outlook_poll_worker import (
    OutlookPollFailure,
    OutlookPollFailureReason,
    OutlookPollResult,
    OutlookPollWorker,
    format_poll_failure_tray_hint,
)
from outlook_actions import join_meeting, open_calendar_event, open_mail
from outlook_text import truncate_notification_line
from pet_window import PetWindow
from chat_context import format_outlook_chat_context
from settings.core import format_speech_bubble_text

TrayNotifier = Callable[[str, str], None]
_logger = logging.getLogger(__name__)
_MAX_SEEN_MAIL_IDS = 500
_MAX_REMINDED_EVENTS = 500


def _reminder_key(entry_id: str, minutes: int) -> str:
    return f"{entry_id}|{minutes}"


def _prune_reminded_events(
    reminded: dict[str, bool],
    active_entry_ids: set[str],
) -> dict[str, bool]:
    """Drop reminder keys for meetings no longer in the poll window."""
    pruned = {
        key: value
        for key, value in reminded.items()
        if key.split("|", 1)[0] in active_entry_ids
    }
    if len(pruned) <= _MAX_REMINDED_EVENTS:
        return pruned
    # Keep the most recently added keys when over cap (dict preserves insertion order).
    excess = len(pruned) - _MAX_REMINDED_EVENTS
    return dict(list(pruned.items())[excess:])


def _mail_snooze_key(entry_id: str) -> str:
    return f"mail|{entry_id}"


def format_mail_notification(mail: MailItem) -> str:
    sender = mail.sender_name.strip() or mail.sender_email
    importance = "⚠️ " if mail.is_high_importance else ""
    lines = [f"{importance}📧 {sender}: {mail.subject}"]
    preview = truncate_notification_line(
        mail.body_preview,
        max_len=MAIL_BODY_PREVIEW_MAX_CHARS,
    )
    if preview:
        lines.append(preview)
    return "\n".join(lines)


def _meeting_location_line(event: CalendarEvent) -> str:
    url = event.online_meeting_url.strip()
    location = event.location.strip()
    if url:
        return truncate_notification_line(url, max_len=MEETING_LOCATION_MAX_CHARS)
    if location:
        return truncate_notification_line(location, max_len=MEETING_LOCATION_MAX_CHARS)
    return ""


def format_meeting_notification(event: CalendarEvent, minutes_left: int) -> str:
    title = event.subject.strip() or "(meeting)"
    if minutes_left <= 0:
        lines = [f"📅 {title} now"]
    else:
        lines = [f"📅 {title} in {minutes_left} min"]
    detail = _meeting_location_line(event)
    if detail:
        lines.append(detail)
    return "\n".join(lines)


class OutlookMonitor(QObject):
    """Timer-driven Outlook polling with deduplication and pet alerts."""

    mail_received = pyqtSignal(MailItem)
    meeting_soon = pyqtSignal(CalendarEvent, int, int)

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
        self._mail_events: QObject | None = None
        self._upcoming_events: list[CalendarEvent] = []

        self._mail_timer = QTimer(self)
        self._mail_timer.timeout.connect(self._poll_mail)
        self._calendar_timer = QTimer(self)
        self._calendar_timer.timeout.connect(self._poll_calendar)

        self.mail_received.connect(self._on_mail_received)
        self.meeting_soon.connect(self._on_meeting_soon)

    def set_tray_notifier(self, notifier: TrayNotifier | None) -> None:
        self._tray_notifier = notifier

    def _set_status_refresh_delegated(self, delegated: bool) -> None:
        if self._outlook_status is None:
            return
        setter = getattr(self._outlook_status, "set_poll_refresh_delegated", None)
        if callable(setter):
            setter(delegated)

    @property
    def mail_events_active(self) -> bool:
        if self._mail_events is None:
            return False
        is_active = getattr(self._mail_events, "is_active", False)
        return bool(is_active() if callable(is_active) else is_active)

    def start(self) -> None:
        """Begin polling when Outlook integration is enabled."""
        if self._running or not get_outlook_enabled():
            return
        self._running = True
        self._mail_baseline_pending = True
        self._set_status_refresh_delegated(True)
        self._restart_timers()
        self._poll_calendar()
        self._poll_mail()

    def stop(self) -> None:
        """Stop polling without clearing Outlook settings."""
        self._running = False
        self._mail_timer.stop()
        self._calendar_timer.stop()
        self._stop_mail_events()
        self._cancel_worker()
        self._set_status_refresh_delegated(False)

    def shutdown(self) -> None:
        """Release resources on application exit."""
        self.stop()

    def chat_context(self) -> str | None:
        """Return a short live Outlook snapshot for the chat system prompt."""
        connected = bool(
            self._outlook_status is not None
            and getattr(self._outlook_status, "is_connected", False)
        )
        unread: int | None = None
        if self._outlook_status is not None:
            raw_unread = getattr(self._outlook_status, "unread_count", None)
            if isinstance(raw_unread, int):
                unread = raw_unread
        return format_outlook_chat_context(
            enabled=get_outlook_enabled(),
            connected=connected,
            unread_count=unread if connected else None,
            upcoming_events=self._upcoming_events,
        )

    def restart_mail_delivery(self) -> None:
        """Restart mail events/polling after settings change."""
        if not self._running:
            return
        self._stop_mail_events()
        self._start_mail_events()
        self._restart_timers()

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

    def _disconnect_worker(self, worker: OutlookPollWorker) -> None:
        for signal, slot in (
            (worker.poll_complete, self._on_poll_complete),
            (worker.poll_failed, self._on_poll_failed),
            (worker.finished, self._on_worker_finished),
        ):
            try:
                signal.disconnect(slot)
            except TypeError:
                pass

    def _cancel_worker(self) -> None:
        if self._worker is None:
            return

        worker = self._worker
        self._worker = None
        self._pending_poll_mail = False
        self._pending_poll_calendar = False
        self._disconnect_worker(worker)

        if worker.isRunning():
            worker.requestInterruption()
            if not worker.wait(10_000):
                worker.terminate()
                worker.wait(2_000)
        worker.deleteLater()

    def _on_worker_finished(self) -> None:
        worker = self.sender()
        if not isinstance(worker, OutlookPollWorker):
            worker = self._worker
        if worker is self._worker:
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

    def _start_mail_events(self) -> None:
        self._stop_mail_events()
        if not self._running or not get_outlook_mail_enabled():
            return
        if get_outlook_source() != "com" or not get_outlook_mail_events_enabled():
            return
        if sys.platform != "win32":
            return

        try:
            from outlook_com_events import OutlookComMailEventSource

            source = OutlookComMailEventSource(parent=self)
            source.mail_received.connect(self._on_event_mail)
            source.unavailable.connect(self._on_mail_events_lost)
            if source.start():
                self._mail_events = source
                self._poll_mail()
            else:
                source.deleteLater()
        except Exception:
            self._mail_events = None

    def _stop_mail_events(self) -> None:
        if self._mail_events is None:
            return
        stop = getattr(self._mail_events, "stop", None)
        if callable(stop):
            stop()
        self._mail_events.deleteLater()
        self._mail_events = None

    def _on_mail_events_lost(self) -> None:
        self._stop_mail_events()
        self._restart_timers()

    def _on_event_mail(self, mail: object) -> None:
        if not isinstance(mail, MailItem):
            return
        if self._mail_baseline_pending:
            seen_ids = set(get_outlook_seen_mail_entry_ids())
            if mail.entry_id not in seen_ids:
                self._persist_seen_ids([*seen_ids, mail.entry_id])
            return
        self._deliver_new_mail([mail])

    def _on_poll_failed(self, failure: object) -> None:
        if not isinstance(failure, OutlookPollFailure):
            failure = OutlookPollFailure(reason=OutlookPollFailureReason.UNKNOWN)

        was_connected = (
            self._outlook_status is not None
            and getattr(self._outlook_status, "is_connected", False)
        )
        if self._outlook_status is not None:
            report = getattr(self._outlook_status, "report_connection_lost", None)
            if callable(report):
                report(failure=failure)

        if was_connected and self._tray_notifier is not None:
            hint = format_poll_failure_tray_hint(failure)
            if hint:
                self._tray_notifier("Outlook", hint)

    def _on_poll_complete(self, result: object) -> None:
        if not isinstance(result, OutlookPollResult):
            return

        if self._outlook_status is not None:
            report_ok = getattr(self._outlook_status, "report_connection_ok", None)
            if callable(report_ok):
                report_ok(result.email, result.unread_count)

        if result.poll_mail and get_outlook_mail_enabled():
            was_baseline = self._mail_baseline_pending
            self._process_mail(result.mail_items)
            if (
                was_baseline
                and get_outlook_source() == "com"
                and get_outlook_mail_events_enabled()
            ):
                self._start_mail_events()
                self._restart_timers()
        if result.poll_calendar and get_outlook_calendar_enabled():
            self._upcoming_events = list(result.calendar_events)
            self._process_calendar(result.calendar_events)

    def _process_mail(self, messages: list[MailItem]) -> None:
        seen_ids = set(get_outlook_seen_mail_entry_ids())
        if self._mail_baseline_pending:
            self._mail_baseline_pending = False
            if not seen_ids:
                self._persist_seen_ids([mail.entry_id for mail in messages])
                return
        self._deliver_new_mail([mail for mail in messages if mail.entry_id not in seen_ids])

    def _deliver_new_mail(self, messages: list[MailItem]) -> None:
        if not messages:
            return
        now = datetime.now()
        seen_ids = list(get_outlook_seen_mail_entry_ids())
        seen_set = set(seen_ids)
        snoozed = dict(get_outlook_snoozed_events())
        snoozed_changed = False
        for mail in messages:
            if mail.entry_id in seen_set:
                continue
            key = _mail_snooze_key(mail.entry_id)
            until_raw = snoozed.get(key)
            if until_raw is not None:
                until = self._parse_snooze_until(until_raw)
                if until is not None and now < until:
                    continue
                del snoozed[key]
                snoozed_changed = True
            seen_set.add(mail.entry_id)
            seen_ids.append(mail.entry_id)
            _logger.info("New mail: %s", format_mail_log_summary(mail))
            self.mail_received.emit(mail)
        if snoozed_changed:
            set_outlook_snoozed_events(snoozed)
        self._persist_seen_ids(seen_ids)

    def _process_calendar(self, events: list[CalendarEvent]) -> None:
        now = datetime.now()
        active_entry_ids = {event.entry_id for event in events}
        original_reminded = dict(get_outlook_reminded_events())
        reminded = _prune_reminded_events(original_reminded, active_entry_ids)
        snoozed = dict(get_outlook_snoozed_events())
        thresholds = get_outlook_meeting_reminder_minutes()
        reminded_changed = reminded != original_reminded
        snoozed_changed = False

        for key, until_raw in list(snoozed.items()):
            until = self._parse_snooze_until(until_raw)
            if until is None or now >= until:
                del snoozed[key]
                snoozed_changed = True

        for event in events:
            minutes_left = int((event.start - now).total_seconds() // 60)
            for threshold in thresholds:
                key = _reminder_key(event.entry_id, threshold)
                until_raw = snoozed.get(key)
                if until_raw is not None:
                    until = self._parse_snooze_until(until_raw)
                    if until is not None and now < until:
                        continue
                if key in reminded:
                    continue
                if 0 <= minutes_left <= threshold:
                    reminded[key] = True
                    reminded_changed = True
                    _logger.info(
                        "Meeting reminder: %s (%s min)",
                        format_event_log_summary(event),
                        minutes_left,
                    )
                    self.meeting_soon.emit(event, minutes_left, threshold)

        if reminded_changed:
            set_outlook_reminded_events(reminded)
        if snoozed_changed:
            set_outlook_snoozed_events(snoozed)

    @staticmethod
    def _parse_snooze_until(raw: object) -> datetime | None:
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            return datetime.fromisoformat(raw.strip())
        except ValueError:
            return None

    def _snooze_meeting(self, entry_id: str, threshold: int) -> None:
        key = _reminder_key(entry_id, threshold)
        reminded = dict(get_outlook_reminded_events())
        if key in reminded:
            del reminded[key]
            set_outlook_reminded_events(reminded)

        snoozed = dict(get_outlook_snoozed_events())
        until = datetime.now() + timedelta(minutes=MEETING_SNOOZE_MINUTES)
        snoozed[key] = until.isoformat(timespec="seconds")
        set_outlook_snoozed_events(snoozed)
        _logger.info(
            "Meeting reminder snoozed for %s min: %s",
            MEETING_SNOOZE_MINUTES,
            key,
        )

    def _snooze_mail(self, entry_id: str) -> None:
        key = _mail_snooze_key(entry_id)
        snoozed = dict(get_outlook_snoozed_events())
        until = datetime.now() + timedelta(minutes=MEETING_SNOOZE_MINUTES)
        snoozed[key] = until.isoformat(timespec="seconds")
        set_outlook_snoozed_events(snoozed)

        seen_ids = list(get_outlook_seen_mail_entry_ids())
        if entry_id in seen_ids:
            set_outlook_seen_mail_entry_ids([item_id for item_id in seen_ids if item_id != entry_id])
        _logger.info(
            "Mail notification snoozed for %s min: %s",
            MEETING_SNOOZE_MINUTES,
            entry_id,
        )

    def _persist_seen_ids(self, entry_ids: list[str]) -> None:
        trimmed = entry_ids[-_MAX_SEEN_MAIL_IDS:]
        set_outlook_seen_mail_entry_ids(trimmed)

    def _pick_notify_pet(self) -> PetWindow | None:
        index = get_outlook_notify_pet_index()
        if index != OUTLOOK_NOTIFY_PET_FIRST_VISIBLE and 0 <= index < len(self._pets):
            return self._pets[index]
        for pet in self._pets:
            if pet.isVisible():
                return pet
        return self._pets[0] if self._pets else None

    def _should_show_bubble(self, pet: PetWindow | None) -> bool:
        if pet is None or not pet.isVisible():
            return False
        if pet.motion_paused and not get_outlook_notify_when_paused():
            return False
        return True

    def _notify(
        self,
        text: str,
        *,
        tray_title: str = "py-shimeji",
        bubble_actions: list[tuple[str, Callable[[], None]]] | None = None,
    ) -> None:
        pet = self._pick_notify_pet()
        bubble_text = format_speech_bubble_text(text)
        if bubble_text is not None and self._should_show_bubble(pet) and pet is not None:
            pet.show_speech_bubble(bubble_text, actions=bubble_actions)
        elif self._tray_notifier is not None:
            self._tray_notifier(tray_title, text)

    def _on_mail_received(self, mail: MailItem) -> None:
        snooze_label = f"Snooze {MEETING_SNOOZE_MINUTES} min"
        actions = [
            (
                "Open in Outlook",
                lambda mail_item=mail: open_mail(mail_item),
            ),
            (
                snooze_label,
                lambda entry_id=mail.entry_id: self._snooze_mail(entry_id),
            ),
        ]
        self._notify(format_mail_notification(mail), bubble_actions=actions)

    def _meeting_bubble_actions(
        self,
        event: CalendarEvent,
        threshold: int,
    ) -> list[tuple[str, Callable[[], None]]]:
        actions: list[tuple[str, Callable[[], None]]] = []
        if event.online_meeting_url.strip():
            actions.append(
                (
                    "Join meeting",
                    lambda meeting=event: join_meeting(meeting),
                )
            )
        actions.append(
            (
                "Open in Outlook",
                lambda meeting=event: open_calendar_event(meeting),
            )
        )
        snooze_label = f"Snooze {MEETING_SNOOZE_MINUTES} min"
        actions.append(
            (
                snooze_label,
                lambda entry_id=event.entry_id, reminder_threshold=threshold: self._snooze_meeting(
                    entry_id,
                    reminder_threshold,
                ),
            )
        )
        return actions

    def _on_meeting_soon(
        self,
        event: CalendarEvent,
        minutes_left: int,
        threshold: int,
    ) -> None:
        text = format_meeting_notification(event, minutes_left)
        self._notify(
            text,
            bubble_actions=self._meeting_bubble_actions(event, threshold),
        )
