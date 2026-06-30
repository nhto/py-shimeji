"""Sprite pack discovery and per-pet sprite folders."""

from __future__ import annotations

from pathlib import Path

from i18n.locale import sprite_state_label
from settings.core import (
    SPRITE_SCALE_PERCENT_DEFAULT,
    SPRITE_SCALE_PERCENT_MAX,
    SPRITE_SCALE_PERCENT_MIN,
    effective_pet_size,
)
from settings.paths import SPRITE_FILES, SPRITE_OPTIONAL_STATES, SPRITES_ROOT
from settings.persistence import (
    clamp_int,
    get_saved_pet_sprite_scale_percent,
    get_saved_pet_sprites_dir,
    set_saved_pet_sprite_scale_percent,
    set_saved_pet_sprites_dir,
)

__all__ = [
    "discover_sprite_packs",
    "effective_pet_size",
    "get_pet_sprites_dir",
    "get_sprite_scale_percent",
    "iter_sprite_file_entries",
    "pet_has_sprites",
    "set_saved_pet_sprite_scale_percent",
    "set_saved_pet_sprites_dir",
    "sprite_pack_display_name",
    "sprite_state_label",
]


def get_sprite_scale_percent(pet_index: int) -> int:
    """Return the persisted sprite scale for a pet (50–200%, default 100%)."""
    raw = get_saved_pet_sprite_scale_percent(pet_index)
    if raw is None:
        return SPRITE_SCALE_PERCENT_DEFAULT
    return clamp_int(
        raw,
        SPRITE_SCALE_PERCENT_MIN,
        SPRITE_SCALE_PERCENT_MAX,
        SPRITE_SCALE_PERCENT_DEFAULT,
    )


def get_pet_sprites_dir(pet_index: int) -> Path:
    """
    Return the sprite folder for a pet.

    Uses a persisted path when saved and still valid, otherwise the default
    ``assets/sprites/pet_N/`` folder (with legacy fallback for pet 1).
    """
    saved = get_saved_pet_sprites_dir(pet_index)
    if saved is not None:
        return saved
    return _default_pet_sprites_dir(pet_index)


def _default_pet_sprites_dir(pet_index: int) -> Path:
    """
    Default sprite folder for a pet without persisted overrides.

    Each pet loads PNGs from ``assets/sprites/pet_N/`` (N is 1-based).
    Pet 1 falls back to the legacy flat ``assets/sprites/`` folder when
    ``pet_1/`` does not exist but shared sprite files are present.
    """
    per_pet = SPRITES_ROOT / f"pet_{pet_index + 1}"
    if per_pet.is_dir():
        return per_pet
    if pet_index == 0 and _legacy_shared_sprites_present():
        return SPRITES_ROOT
    return per_pet


def _legacy_shared_sprites_present() -> bool:
    """True when PNGs still live directly under assets/sprites/."""
    return any((SPRITES_ROOT / name).is_file() for names in SPRITE_FILES.values() for name in names)


def pet_has_sprites(sprites_dir: Path) -> bool:
    """True when the folder contains native or Shimeji community sprite frames."""
    from shimeji_pack import has_native_sprites, is_shimeji_pack

    if not sprites_dir.is_dir():
        return False
    return has_native_sprites(sprites_dir) or is_shimeji_pack(sprites_dir)


def iter_sprite_file_entries() -> list[tuple[str, str, bool]]:
    """Return ``(state, filename, optional)`` for every expected sprite PNG."""
    entries: list[tuple[str, str, bool]] = []
    for state, filenames in SPRITE_FILES.items():
        optional = state in SPRITE_OPTIONAL_STATES
        for filename in filenames:
            entries.append((state, filename, optional))
    return entries


def discover_sprite_packs(extra_dirs: Path | list[Path] | None = None) -> list[Path]:
    """
    Return sprite folders that contain at least one valid PNG.

    Scans built-in ``assets/sprites/`` (including one level of subfolders) and
    any extra paths supplied by the caller (e.g. the pet's current folder).
    """
    found: dict[str, Path] = {}

    def add_if_valid(path: Path) -> None:
        resolved = path.resolve()
        if pet_has_sprites(resolved):
            found[str(resolved)] = resolved

    if SPRITES_ROOT.is_dir():
        add_if_valid(SPRITES_ROOT)
        for child in sorted(SPRITES_ROOT.iterdir()):
            if not child.is_dir():
                continue
            add_if_valid(child)
            for sub in sorted(child.iterdir()):
                if sub.is_dir():
                    add_if_valid(sub)

    extras = extra_dirs if isinstance(extra_dirs, list) else ([extra_dirs] if extra_dirs else [])
    for path in extras:
        if path is not None:
            add_if_valid(path)

    return sorted(found.values(), key=_sprite_pack_sort_key)


def sprite_pack_display_name(path: Path, language: str | None = None) -> str:
    """Human-readable label for a sprite folder in the picker grid."""
    _ = language
    try:
        rel = path.resolve().relative_to(SPRITES_ROOT.resolve())
        return str(rel).replace("\\", " / ")
    except ValueError:
        return path.name or str(path)


def _sprite_pack_sort_key(path: Path) -> tuple[int, str]:
    try:
        rel = path.resolve().relative_to(SPRITES_ROOT.resolve())
        return (0, str(rel).lower())
    except ValueError:
        return (1, str(path).lower())
