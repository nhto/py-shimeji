"""Unit tests for global hotkey string parsing."""

from __future__ import annotations

import sys

import pytest

from hotkeys import ParsedHotkey, parse_hotkey


@pytest.mark.skipif(sys.platform != "win32", reason="Hotkeys are Windows-only")
def test_parse_ctrl_alt_letter() -> None:
    parsed = parse_hotkey("Ctrl+Alt+P")
    assert parsed == ParsedHotkey(modifiers=0x0002 | 0x0001, vk=ord("P"))


@pytest.mark.skipif(sys.platform != "win32", reason="Hotkeys are Windows-only")
def test_parse_shift_win_function_key() -> None:
    parsed = parse_hotkey("Shift+Win+F5")
    assert parsed is not None
    assert parsed.modifiers == 0x0004 | 0x0008
    assert parsed.vk == 0x74


@pytest.mark.skipif(sys.platform != "win32", reason="Hotkeys are Windows-only")
@pytest.mark.parametrize(
    "binding",
    [
        "",
        "P",
        "Ctrl+Alt",
        "Ctrl+Alt+UnknownKey",
        "Ctrl+Alt+P+Q",
    ],
)
def test_parse_rejects_invalid_bindings(binding: str) -> None:
    assert parse_hotkey(binding) is None
