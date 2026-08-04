"""Project paths and environment loading."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _app_data_root() -> Path:
    """
    Writable directory for .env and JSON settings.

    In a frozen build this is the folder containing the executable so user
    settings survive updates when the app is replaced.
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _bundle_root() -> Path:
    """Read-only bundle root (PyInstaller extract dir, or project root in dev)."""
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _load_dotenv(root: Path) -> None:
    """Load key=value pairs from a local .env file when present."""
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


PROJECT_ROOT: Path = _app_data_root()
BUNDLE_ROOT: Path = _bundle_root()
SPRITES_ROOT: Path = BUNDLE_ROOT / "assets" / "sprites"

_load_dotenv(PROJECT_ROOT)

ASSETS_DIR: Path = SPRITES_ROOT
ENV_FILE_PATH: Path = PROJECT_ROOT / ".env"

SPRITE_FILES: dict[str, list[str]] = {
    "idle": ["idle_1.png", "idle_2.png"],
    "walk": ["walk_1.png", "walk_2.png"],
    "climb": ["climb_1.png", "climb_2.png"],
    "sit": ["sit_1.png"],
    "fall": ["fall_1.png"],
    "drag": ["drag_1.png"],
}

SPRITE_OPTIONAL_STATES: frozenset[str] = frozenset({"sit", "climb"})
