"""Update-check preferences stored in .app_settings.json."""

from __future__ import annotations

from settings.persistence import load_app_settings, save_app_settings


def get_update_check_enabled() -> bool:
    """Whether to check GitHub Releases on startup (frozen builds only)."""
    return load_app_settings().get("update_check_enabled", True) is not False


def set_update_check_enabled(enabled: bool) -> None:
    data = load_app_settings()
    data["update_check_enabled"] = enabled
    save_app_settings(data)


def get_skipped_version() -> str | None:
    """Version the user chose to skip for update notifications."""
    raw = load_app_settings().get("skipped_update_version")
    return raw if isinstance(raw, str) and raw.strip() else None


def set_skipped_version(version: str | None) -> None:
    data = load_app_settings()
    if version:
        data["skipped_update_version"] = version
    else:
        data.pop("skipped_update_version", None)
    save_app_settings(data)
