"""Windows startup registration and launch-minimized preferences."""

from __future__ import annotations

import sys
from pathlib import Path

from settings.persistence import load_app_settings, save_app_settings

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE_NAME = "py-shimeji"
_MINIMIZED_FLAG = "--minimized"


def startup_ui_available() -> bool:
    """True when startup tray toggles should be shown."""
    return sys.platform == "win32"


def _startup_settings() -> dict:
    raw = load_app_settings().get("startup", {})
    return raw if isinstance(raw, dict) else {}


def get_start_with_windows() -> bool:
    """Return whether the app should register for Windows logon startup."""
    return bool(_startup_settings().get("start_with_windows", False))


def get_launch_minimized() -> bool:
    """Return whether the app should start with pets hidden (tray only)."""
    return bool(_startup_settings().get("launch_minimized", False))


def set_start_with_windows(enabled: bool) -> None:
    """Persist and apply the Windows logon startup preference."""
    data = load_app_settings()
    startup = data.setdefault("startup", {})
    if not isinstance(startup, dict):
        startup = {}
        data["startup"] = startup
    startup["start_with_windows"] = enabled
    save_app_settings(data)
    if startup_ui_available():
        if enabled:
            register_for_startup(minimized=get_launch_minimized())
        else:
            unregister_from_startup()


def set_launch_minimized(enabled: bool) -> None:
    """Persist launch-minimized preference and refresh the Run key when needed."""
    data = load_app_settings()
    startup = data.setdefault("startup", {})
    if not isinstance(startup, dict):
        startup = {}
        data["startup"] = startup
    startup["launch_minimized"] = enabled
    save_app_settings(data)
    if startup_ui_available() and get_start_with_windows():
        register_for_startup(minimized=enabled)


def should_launch_minimized(argv: list[str] | None = None) -> bool:
    """True when this process should skip showing pets on startup."""
    args = argv if argv is not None else sys.argv
    if _MINIMIZED_FLAG in args:
        return True
    return get_launch_minimized()


def build_launch_command(*, minimized: bool) -> str:
    """Build the command line stored in the Windows Run registry value."""
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        command = f'"{executable}"'
    else:
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        command = f'"{sys.executable}" "{main_py.resolve()}"'
    if minimized:
        command += f" {_MINIMIZED_FLAG}"
    return command


def is_registered_for_startup() -> bool:
    """Return whether the Run key currently contains a py-shimeji entry."""
    if not startup_ui_available():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _RUN_VALUE_NAME)
            return True
    except OSError:
        return False


def register_for_startup(*, minimized: bool) -> None:
    """Write or update the py-shimeji entry in the current user's Run key."""
    if not startup_ui_available():
        return
    import winreg

    command = build_launch_command(minimized=minimized)
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        _RUN_KEY,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, _RUN_VALUE_NAME, 0, winreg.REG_SZ, command)


def unregister_from_startup() -> None:
    """Remove the py-shimeji entry from the current user's Run key."""
    if not startup_ui_available():
        return
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, _RUN_VALUE_NAME)
    except OSError:
        pass


def ensure_startup_registry_matches_setting() -> None:
    """Keep the Run key aligned with persisted startup preferences."""
    if not startup_ui_available():
        return
    if get_start_with_windows():
        register_for_startup(minimized=get_launch_minimized())
    elif is_registered_for_startup():
        unregister_from_startup()
