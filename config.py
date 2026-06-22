"""Application-wide constants and paths for the Shimeji desktop pet."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent
SPRITES_ROOT: Path = PROJECT_ROOT / "assets" / "sprites"

# Legacy alias (shared folder before per-pet directories).
ASSETS_DIR: Path = SPRITES_ROOT

# Expected sprite filenames per state (frames are cycled in order).
SPRITE_FILES: dict[str, list[str]] = {
    "idle": ["idle_1.png", "idle_2.png"],
    "walk": ["walk_1.png", "walk_2.png"],
    "fall": ["fall_1.png"],
    "drag": ["drag_1.png"],
}

# ---------------------------------------------------------------------------
# Window & pet dimensions
# ---------------------------------------------------------------------------

PET_WIDTH: int = 64
PET_HEIGHT: int = 64

# ---------------------------------------------------------------------------
# Timers (milliseconds)
# ---------------------------------------------------------------------------

ANIMATION_INTERVAL_MS: int = 120
BEHAVIOR_INTERVAL_MS: int = 500
IDLE_TO_WALK_MIN_MS: int = 3_000
IDLE_TO_WALK_MAX_MS: int = 8_000
WALK_TO_IDLE_MIN_MS: int = 2_000
WALK_TO_IDLE_MAX_MS: int = 5_000

# ---------------------------------------------------------------------------
# Movement & physics
# ---------------------------------------------------------------------------

WALK_SPEED_PX: int = 3
CLIMB_SPEED_PX: int = 4
GRAVITY_PX: int = 8
FALL_TICK_MS: int = 16
SURFACE_REFRESH_MS: int = 400

# Minimum window size to treat as a climbable surface (Windows).
MIN_WINDOW_WIDTH: int = 120
MIN_WINDOW_HEIGHT: int = 80

# ---------------------------------------------------------------------------
# Multi-pet
# ---------------------------------------------------------------------------

MAX_PETS: int = 2

# ---------------------------------------------------------------------------
# Fallback rendering (used when sprite files are missing)
# ---------------------------------------------------------------------------

FALLBACK_BODY_COLOR: str = "#FF6B9D"
FALLBACK_OUTLINE_COLOR: str = "#2D1B2E"
FALLBACK_EYE_COLOR: str = "#FFFFFF"
FALLBACK_PUPIL_COLOR: str = "#1A1A2E"

# Per-pet fallback palettes when multiple pets are active.
PET_FALLBACK_PALETTES: list[dict[str, str]] = [
    {
        "body": FALLBACK_BODY_COLOR,
        "outline": FALLBACK_OUTLINE_COLOR,
        "eye": FALLBACK_EYE_COLOR,
        "pupil": FALLBACK_PUPIL_COLOR,
    },
    {
        "body": "#4ECDC4",
        "outline": "#1A3A3A",
        "eye": "#FFFFFF",
        "pupil": "#0D2B2B",
    },
]


def get_pet_sprites_dir(pet_index: int) -> Path:
    """
    Return the sprite folder for a pet.

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
    """True when the folder contains at least one expected sprite PNG."""
    if not sprites_dir.is_dir():
        return False
    return any((sprites_dir / name).is_file() for names in SPRITE_FILES.values() for name in names)
