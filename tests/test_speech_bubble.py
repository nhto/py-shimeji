"""Unit tests for speech bubble text formatting."""

from __future__ import annotations

from settings.core import SPEECH_BUBBLE_MAX_CHARS, format_speech_bubble_text


def test_collapses_blank_lines() -> None:
    assert format_speech_bubble_text("  hello \n\n  world  ") == "hello\nworld"


def test_returns_none_for_empty_input() -> None:
    assert format_speech_bubble_text("   \n") is None


def test_returns_none_when_too_long() -> None:
    text = "x" * (SPEECH_BUBBLE_MAX_CHARS + 1)
    assert format_speech_bubble_text(text) is None


def test_accepts_text_at_limit() -> None:
    text = "x" * SPEECH_BUBBLE_MAX_CHARS
    assert format_speech_bubble_text(text) == text
