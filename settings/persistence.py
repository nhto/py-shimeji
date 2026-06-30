"""Read/write .app_settings.json."""

from __future__ import annotations

import json
from pathlib import Path

from settings.paths import PROJECT_ROOT

_APP_SETTINGS_PATH: Path = PROJECT_ROOT / ".app_settings.json"


def load_app_settings() -> dict:
    if _APP_SETTINGS_PATH.is_file():
        try:
            data = json.loads(_APP_SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return {}


def save_app_settings(data: dict) -> None:
    _APP_SETTINGS_PATH.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )


def pet_settings_entry(pet_index: int) -> dict:
    pets = load_app_settings().get("pets", {})
    if not isinstance(pets, dict):
        return {}
    entry = pets.get(str(pet_index), {})
    return entry if isinstance(entry, dict) else {}


def clamp_int(value: object, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def clamp_float(value: object, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def get_saved_pet_sprites_dir(pet_index: int) -> Path | None:
    """Return a persisted sprite folder when it still exists on disk."""
    raw = pet_settings_entry(pet_index).get("sprites_dir")
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    return path if path.is_dir() else None


def get_saved_pet_sprite_scale_percent(pet_index: int) -> int | None:
    """Return a persisted sprite scale percentage, or None for the default."""
    raw = pet_settings_entry(pet_index).get("sprite_scale_percent")
    if raw is None:
        return None
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def set_saved_pet_sprite_scale_percent(pet_index: int, scale_percent: int) -> None:
    """Persist the sprite scale percentage for a pet."""
    data = load_app_settings()
    pets = data.setdefault("pets", {})
    if not isinstance(pets, dict):
        pets = {}
        data["pets"] = pets
    entry = pets.setdefault(str(pet_index), {})
    if not isinstance(entry, dict):
        entry = {}
        pets[str(pet_index)] = entry
    entry["sprite_scale_percent"] = scale_percent
    save_app_settings(data)


def set_saved_pet_sprites_dir(pet_index: int, sprites_dir: Path) -> None:
    """Persist the sprite folder for a pet."""
    data = load_app_settings()
    pets = data.setdefault("pets", {})
    if not isinstance(pets, dict):
        pets = {}
        data["pets"] = pets
    entry = pets.setdefault(str(pet_index), {})
    if not isinstance(entry, dict):
        entry = {}
        pets[str(pet_index)] = entry
    entry["sprites_dir"] = str(sprites_dir.resolve())
    save_app_settings(data)


def get_saved_pet_visible(pet_index: int) -> bool | None:
    """Return persisted visibility, or None to use the startup default."""
    entry = pet_settings_entry(pet_index)
    if "visible" not in entry:
        return None
    return bool(entry["visible"])


def set_saved_pet_visible(pet_index: int, visible: bool) -> None:
    """Persist whether a pet should be shown on startup."""
    data = load_app_settings()
    pets = data.setdefault("pets", {})
    if not isinstance(pets, dict):
        pets = {}
        data["pets"] = pets
    entry = pets.setdefault(str(pet_index), {})
    if not isinstance(entry, dict):
        entry = {}
        pets[str(pet_index)] = entry
    entry["visible"] = visible
    save_app_settings(data)


def get_saved_pets_paused() -> bool:
    """Return whether pets should start in reduce-motion pause mode."""
    return bool(load_app_settings().get("pets_paused", False))


def set_saved_pets_paused(paused: bool) -> None:
    """Persist reduce-motion pause mode for the next launch."""
    data = load_app_settings()
    data["pets_paused"] = paused
    save_app_settings(data)
