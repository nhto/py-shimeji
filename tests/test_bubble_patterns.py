"""Unit tests for chat and speech bubble patterns."""

from bubble_patterns import (
    CHAT_BUBBLE_PATTERN_IDS,
    SPEECH_BUBBLE_PATTERN_IDS,
    chat_bubble_pattern_count,
    speech_bubble_pattern_count,
    wrap_chat_bubble_content,
)


def test_chat_pattern_count():
    assert chat_bubble_pattern_count() == len(CHAT_BUBBLE_PATTERN_IDS)
    assert chat_bubble_pattern_count() >= 5


def test_speech_pattern_count():
    assert speech_bubble_pattern_count() == len(SPEECH_BUBBLE_PATTERN_IDS)
    assert speech_bubble_pattern_count() >= 5


def test_wrap_chat_bubble_content_cycles_patterns():
    bodies = {
        wrap_chat_bubble_content(
            "hello",
            is_user=False,
            pattern_index=index,
            bubble_bg="#f1f5f9",
            bubble_fg="#1e293b",
            border="border:1px solid #e2e8f0;",
        )
        for index in range(chat_bubble_pattern_count())
    }
    assert len(bodies) == chat_bubble_pattern_count()
    assert all("hello" in body for body in bodies)
    assert len(bodies) == len(set(bodies))


def test_wrap_chat_bubble_content_user_accent_side():
    html = wrap_chat_bubble_content(
        "hi",
        is_user=True,
        pattern_index=0,
        bubble_bg="#4f46e5",
        bubble_fg="#ffffff",
        border="border:1px solid #6366f1;",
    )
    assert "hi" in html
    assert "bgcolor=" in html
