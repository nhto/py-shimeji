"""Tests for Windows startup registration helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import settings.startup as startup


@pytest.fixture(autouse=True)
def _clear_app_settings(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings_path = tmp_path / ".app_settings.json"
    monkeypatch.setattr("settings.persistence._APP_SETTINGS_PATH", settings_path)
    settings_path.write_text("{}", encoding="utf-8")


def test_should_launch_minimized_from_setting() -> None:
    startup.set_launch_minimized(True)
    assert startup.should_launch_minimized(["main.py"]) is True


def test_should_launch_minimized_from_cli_flag() -> None:
    startup.set_launch_minimized(False)
    assert startup.should_launch_minimized(["main.py", "--minimized"]) is True


def test_set_start_with_windows_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(startup, "startup_ui_available", lambda: False)
    startup.set_start_with_windows(True)
    assert startup.get_start_with_windows() is True


def test_set_start_with_windows_registers_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    register = MagicMock()
    monkeypatch.setattr(startup, "startup_ui_available", lambda: True)
    monkeypatch.setattr(startup, "register_for_startup", register)
    monkeypatch.setattr(startup, "unregister_from_startup", MagicMock())

    startup.set_start_with_windows(True)
    register.assert_called_once_with(minimized=False)

    startup.set_launch_minimized(True)
    register.assert_called_with(minimized=True)


def test_set_start_with_windows_unregisters_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    unregister = MagicMock()
    monkeypatch.setattr(startup, "startup_ui_available", lambda: True)
    monkeypatch.setattr(startup, "register_for_startup", MagicMock())
    monkeypatch.setattr(startup, "unregister_from_startup", unregister)

    startup.set_start_with_windows(True)
    startup.set_start_with_windows(False)
    unregister.assert_called_once()


def test_build_launch_command_includes_minimized_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(startup.sys, "executable", r"C:\Python\python.exe")
    monkeypatch.setattr(startup.sys, "frozen", False, raising=False)

    command = startup.build_launch_command(minimized=True)
    assert command.endswith(" --minimized")
    assert "main.py" in command


def test_ensure_startup_registry_matches_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    register = MagicMock()
    unregister = MagicMock()
    monkeypatch.setattr(startup, "startup_ui_available", lambda: True)
    monkeypatch.setattr(startup, "register_for_startup", register)
    monkeypatch.setattr(startup, "unregister_from_startup", unregister)

    data = {"startup": {"start_with_windows": True, "launch_minimized": False}}
    monkeypatch.setattr(startup, "load_app_settings", lambda: data)
    startup.ensure_startup_registry_matches_setting()
    register.assert_called_once_with(minimized=False)

    register.reset_mock()
    data["startup"]["start_with_windows"] = False
    monkeypatch.setattr(startup, "is_registered_for_startup", lambda: True)
    startup.ensure_startup_registry_matches_setting()
    unregister.assert_called_once()
    register.assert_not_called()
