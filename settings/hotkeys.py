"""Global hotkey bindings persisted in app settings."""

from __future__ import annotations

from settings.persistence import load_app_settings, save_app_settings

HOTKEY_ACTIONS: tuple[str, ...] = (
    "toggle_pause",
    "toggle_click_through",
    "toggle_pets_visible",
    "open_chat",
)

_DEFAULT_HOTKEY_BINDINGS: dict[str, str] = {
    "toggle_pause": "Ctrl+Alt+P",
    "toggle_click_through": "Ctrl+Alt+C",
    "toggle_pets_visible": "Ctrl+Alt+H",
    "open_chat": "Ctrl+Alt+B",
}


def _hotkey_settings() -> dict:
    hotkeys = load_app_settings().get("hotkeys", {})
    return hotkeys if isinstance(hotkeys, dict) else {}


def get_hotkey_binding(action: str) -> str:
    """Return the configured binding for a hotkey action, or the default."""
    if action not in HOTKEY_ACTIONS:
        raise ValueError(f"Unknown hotkey action: {action}")
    saved = _hotkey_settings().get(action)
    if isinstance(saved, str):
        return saved.strip()
    return _DEFAULT_HOTKEY_BINDINGS.get(action, "")


def set_hotkey_binding(action: str, binding: str) -> None:
    """Persist a global hotkey binding (empty string disables the action)."""
    if action not in HOTKEY_ACTIONS:
        raise ValueError(f"Unknown hotkey action: {action}")
    data = load_app_settings()
    hotkeys = data.setdefault("hotkeys", {})
    if not isinstance(hotkeys, dict):
        hotkeys = {}
        data["hotkeys"] = hotkeys
    hotkeys[action] = binding.strip()
    save_app_settings(data)
