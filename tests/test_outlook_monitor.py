"""Unit tests for Outlook mail dedup, snooze, and notification formatting."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from outlook_models import CalendarEvent, MailItem
from outlook_monitor import (
    OutlookMonitor,
    _mail_snooze_key,
    _reminder_key,
    format_mail_notification,
    format_meeting_notification,
)


def _sample_mail(entry_id: str = "mail-1") -> MailItem:
    return MailItem(
        entry_id=entry_id,
        subject="Hello",
        sender_name="Alice",
        sender_email="alice@example.com",
        received_at=datetime(2026, 6, 30, 9, 0, 0),
        body_preview="Preview text",
    )


def test_format_mail_notification_includes_sender_and_preview() -> None:
    text = format_mail_notification(_sample_mail())
    assert "Alice" in text
    assert "Hello" in text
    assert "Preview text" in text


def test_format_mail_notification_marks_high_importance() -> None:
    mail = MailItem(
        entry_id="x",
        subject="Urgent",
        sender_name="Bob",
        sender_email="bob@example.com",
        received_at=datetime.now(),
        is_high_importance=True,
    )
    assert format_mail_notification(mail).startswith("⚠️")


def test_format_meeting_notification_now_vs_upcoming() -> None:
    event = CalendarEvent(
        entry_id="evt-1",
        subject="Standup",
        start=datetime.now(),
        end=datetime.now() + timedelta(minutes=30),
        location="Room A",
    )
    assert "now" in format_meeting_notification(event, 0)
    assert "in 5 min" in format_meeting_notification(event, 5)


def test_reminder_and_mail_snooze_keys() -> None:
    assert _reminder_key("evt", 15) == "evt|15"
    assert _mail_snooze_key("mail-9") == "mail|mail-9"


def test_parse_snooze_until_accepts_isoformat() -> None:
    raw = "2026-06-30T12:00:00"
    parsed = OutlookMonitor._parse_snooze_until(raw)
    assert parsed == datetime.fromisoformat(raw)


def test_parse_snooze_until_rejects_garbage() -> None:
    assert OutlookMonitor._parse_snooze_until("not-a-date") is None
    assert OutlookMonitor._parse_snooze_until(None) is None


@patch("outlook_monitor.set_outlook_seen_mail_entry_ids")
@patch("outlook_monitor.get_outlook_seen_mail_entry_ids", return_value=[])
@patch("outlook_monitor.get_outlook_snoozed_events", return_value={})
def test_deliver_new_mail_emits_unseen_messages(
    _snoozed,
    _seen,
    persist_seen,
    qapp,
) -> None:
    monitor = OutlookMonitor(pets=[], parent=None)
    received: list[MailItem] = []
    monitor.mail_received.connect(received.append)

    monitor._deliver_new_mail([_sample_mail("a"), _sample_mail("b")])

    assert [mail.entry_id for mail in received] == ["a", "b"]
    persist_seen.assert_called_once()
    assert persist_seen.call_args.args[0] == ["a", "b"]


@patch("outlook_monitor.set_outlook_seen_mail_entry_ids")
@patch("outlook_monitor.get_outlook_seen_mail_entry_ids", return_value=[])
@patch("outlook_monitor.get_outlook_snoozed_events")
def test_deliver_new_mail_skips_snoozed_until_expires(
    get_snoozed,
    _seen,
    persist_seen,
    qapp,
) -> None:
    mail = _sample_mail("snoozed-mail")
    key = _mail_snooze_key(mail.entry_id)
    future = (datetime.now() + timedelta(minutes=10)).isoformat(timespec="seconds")
    get_snoozed.return_value = {key: future}

    monitor = OutlookMonitor(pets=[], parent=None)
    received: list[MailItem] = []
    monitor.mail_received.connect(received.append)

    monitor._deliver_new_mail([mail])

    assert received == []
    persist_seen.assert_called_once_with([])


@patch("outlook_monitor.set_outlook_seen_mail_entry_ids")
@patch("outlook_monitor.get_outlook_seen_mail_entry_ids", return_value=[])
def test_process_mail_baseline_records_all_when_no_seen_ids(
    _seen,
    persist_seen,
    qapp,
) -> None:
    monitor = OutlookMonitor(pets=[], parent=None)
    monitor._mail_baseline_pending = True

    monitor._process_mail([_sample_mail("one"), _sample_mail("two")])

    assert monitor._mail_baseline_pending is False
    persist_seen.assert_called_once_with(["one", "two"])


@patch("outlook_monitor.set_outlook_reminded_events")
@patch("outlook_monitor.get_outlook_reminded_events", return_value={})
@patch("outlook_monitor.get_outlook_snoozed_events", return_value={})
@patch("outlook_monitor.get_outlook_meeting_reminder_minutes", return_value=[15])
def test_process_calendar_emits_when_within_threshold(
    _thresholds,
    _snoozed,
    _reminded,
    set_reminded,
    qapp,
) -> None:
    monitor = OutlookMonitor(pets=[], parent=None)
    soon: list[tuple[CalendarEvent, int, int]] = []
    monitor.meeting_soon.connect(lambda event, left, threshold: soon.append((event, left, threshold)))

    start = datetime.now() + timedelta(minutes=10)
    event = CalendarEvent(
        entry_id="evt-42",
        subject="Review",
        start=start,
        end=start + timedelta(minutes=30),
    )
    monitor._process_calendar([event])

    assert len(soon) == 1
    assert soon[0][0].entry_id == "evt-42"
    set_reminded.assert_called_once()
