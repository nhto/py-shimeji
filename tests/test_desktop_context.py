"""Unit tests for desktop chat context settings and provider."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from chat_context import clear_chat_context_providers
from desktop_context import DesktopChatContext
from settings.chat import (
    get_chat_context_include_active_window,
    get_chat_context_include_clipboard,
    set_chat_context_include_active_window,
    set_chat_context_include_clipboard,
)


@pytest.fixture(autouse=True)
def _reset_context_settings() -> None:
    set_chat_context_include_active_window(False)
    set_chat_context_include_clipboard(False)
    clear_chat_context_providers()
    yield
    set_chat_context_include_active_window(False)
    set_chat_context_include_clipboard(False)
    clear_chat_context_providers()


def test_context_settings_default_off() -> None:
    assert get_chat_context_include_active_window() is False
    assert get_chat_context_include_clipboard() is False


def test_context_settings_persist() -> None:
    set_chat_context_include_active_window(True)
    set_chat_context_include_clipboard(True)
    assert get_chat_context_include_active_window() is True
    assert get_chat_context_include_clipboard() is True


def test_desktop_chat_context_respects_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    pet = MagicMock()
    pet.motion_paused = False
    pet.click_through = False
    provider = DesktopChatContext([pet])

    monkeypatch.setattr(
        "desktop_context.read_active_window_title",
        lambda _exclude: "Secret window",
    )
    monkeypatch.setattr(
        "desktop_context.read_clipboard_summary",
        lambda: "secret clipboard",
    )

    text = provider.chat_context()
    assert text is not None
    assert "Secret window" not in text
    assert "secret clipboard" not in text

    set_chat_context_include_active_window(True)
    set_chat_context_include_clipboard(True)
    text = provider.chat_context()
    assert text is not None
    assert "Secret window" in text
    assert "secret clipboard" in text
