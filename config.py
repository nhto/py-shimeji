"""Application-wide constants and paths for the Shimeji desktop pet."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = PROJECT_ROOT / "assets" / "sprites"

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
GRAVITY_PX: int = 8
FALL_TICK_MS: int = 16

# ---------------------------------------------------------------------------
# Fallback rendering (used when sprite files are missing)
# ---------------------------------------------------------------------------

FALLBACK_BODY_COLOR: str = "#FF6B9D"
FALLBACK_OUTLINE_COLOR: str = "#2D1B2E"
FALLBACK_EYE_COLOR: str = "#FFFFFF"
FALLBACK_PUPIL_COLOR: str = "#1A1A2E"
