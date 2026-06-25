"""Safe Outlook logging helpers — never log full message bodies."""

from __future__ import annotations

from outlook_models import CalendarEvent, MailItem

_MAX_LOG_FIELD_LEN = 200


def _truncate(value: str, *, limit: int = _MAX_LOG_FIELD_LEN) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}…"


def format_mail_log_summary(mail: MailItem) -> str:
    """Return a log-safe mail summary (sender + subject only)."""
    sender = mail.sender_name.strip() or mail.sender_email.strip() or "(unknown)"
    subject = mail.subject.strip() or "(no subject)"
    return f"{_truncate(sender)}: {_truncate(subject)}"


def format_event_log_summary(event: CalendarEvent) -> str:
    """Return a log-safe calendar event summary (subject only)."""
    subject = event.subject.strip() or "(meeting)"
    return _truncate(subject)
