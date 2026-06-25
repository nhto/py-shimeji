"""Shared text helpers for Outlook mail/calendar notifications."""

from __future__ import annotations

import html
import re

_TEAMS_JOIN_URL_RE = re.compile(
    r"https://teams\.microsoft\.com/l/meetup-join/[^\s<>\"']+",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def plain_text_first_line(raw: str, *, max_len: int = 60) -> str:
    """Return the first non-empty body line as plain text, truncated."""
    if not raw:
        return ""
    first = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0]
    first = _HTML_TAG_RE.sub(" ", first)
    first = html.unescape(first)
    first = " ".join(first.split())
    if not first:
        return ""
    if len(first) <= max_len:
        return first
    return f"{first[: max_len - 1]}…"


def extract_teams_join_url(*chunks: str) -> str:
    """Find a Microsoft Teams join URL in one or more text blobs."""
    for chunk in chunks:
        if not chunk:
            continue
        match = _TEAMS_JOIN_URL_RE.search(chunk)
        if match:
            return match.group(0)
    return ""


def truncate_notification_line(text: str, *, max_len: int = 70) -> str:
    """Truncate a single notification line with an ellipsis."""
    collapsed = " ".join(text.split())
    if not collapsed:
        return ""
    if len(collapsed) <= max_len:
        return collapsed
    return f"{collapsed[: max_len - 1]}…"
