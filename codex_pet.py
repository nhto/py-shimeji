"""Codex Pet spritesheet compatibility (pet.json + spritesheet.webp/png)."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

# Codex Pet atlas layout (see https://codexpet.xyz/spec/).
GRID_COLUMNS = 8
CELL_WIDTH = 192
CELL_HEIGHT = 208
V1_ROWS = 9
V2_ROWS = 11
V1_SIZE = (GRID_COLUMNS * CELL_WIDTH, V1_ROWS * CELL_HEIGHT)
V2_SIZE = (GRID_COLUMNS * CELL_WIDTH, V2_ROWS * CELL_HEIGHT)

_CACHE_DIR_NAME = ".py-shimeji-cache"
_PET_JSON_NAME = "pet.json"
_SPRITESHEET_NAMES: tuple[str, ...] = (
    "spritesheet.webp",
    "spritesheet.png",
    "spritesheet.jpg",
    "spritesheet.jpeg",
)

# Map py-shimeji animation groups to Codex spritesheet rows and frame columns.
STATE_ROW_FRAMES: dict[str, list[tuple[int, int]]] = {
    "idle": [(0, 0), (0, 1)],
    "walk": [(1, 0), (1, 1)],
    "sit": [(6, 0)],
    "fall": [(4, 0)],
    "drag": [(5, 0)],
}

STATE_FRAME_LIMITS: dict[str, int] = {
    "idle": 2,
    "walk": 2,
    "sit": 1,
    "fall": 1,
    "drag": 1,
}


@dataclass(frozen=True)
class CodexManifest:
    """Parsed fields from a Codex ``pet.json`` manifest."""

    spritesheet_path: str
    sprite_version: int


@dataclass(frozen=True)
class CodexGrid:
    """Spritesheet grid geometry."""

    rows: int
    cell_width: int
    cell_height: int


def _load_qimage():
    """Lazy import so non-Qt callers can use manifest helpers."""
    from PyQt6.QtGui import QImage

    return QImage


def find_pet_json(pack_dir: Path) -> Path | None:
    """Return ``pet.json`` when present in a Codex pet folder."""
    path = pack_dir.resolve() / _PET_JSON_NAME
    return path if path.is_file() else None


def parse_pet_manifest(pet_json: Path) -> CodexManifest | None:
    """Parse a Codex ``pet.json`` file."""
    try:
        data = json.loads(pet_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    spritesheet_path = data.get("spritesheetPath")
    if not isinstance(spritesheet_path, str) or not spritesheet_path.strip():
        spritesheet_path = _SPRITESHEET_NAMES[0]
    version_raw = data.get("spriteVersionNumber", 1)
    try:
        sprite_version = int(version_raw)
    except (TypeError, ValueError):
        sprite_version = 1
    return CodexManifest(
        spritesheet_path=spritesheet_path.strip(),
        sprite_version=sprite_version,
    )


def find_spritesheet(pack_dir: Path, manifest: CodexManifest | None = None) -> Path | None:
    """Locate the Codex spritesheet image inside a pack folder."""
    pack_dir = pack_dir.resolve()
    candidates: list[Path] = []
    if manifest is not None:
        candidates.append(pack_dir / manifest.spritesheet_path)
    candidates.extend(pack_dir / name for name in _SPRITESHEET_NAMES)
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            return path.resolve()
    return None


def grid_for_image_size(
    width: int,
    height: int,
    *,
    sprite_version: int | None = None,
) -> CodexGrid | None:
    """Derive Codex grid geometry from a spritesheet's pixel size."""
    if width <= 0 or height <= 0 or width % GRID_COLUMNS != 0:
        return None

    cell_width = width // GRID_COLUMNS
    if sprite_version == 2 or (width, height) == V2_SIZE:
        rows = V2_ROWS
    elif sprite_version == 1 or (width, height) == V1_SIZE:
        rows = V1_ROWS
    elif height % CELL_HEIGHT == 0:
        rows = height // CELL_HEIGHT
    else:
        return None

    if rows < V1_ROWS:
        return None

    cell_height = height // rows
    if cell_height <= 0:
        return None
    return CodexGrid(rows=rows, cell_width=cell_width, cell_height=cell_height)


def _cell_is_empty(image, row: int, col: int, grid: CodexGrid) -> bool:
    """Return True when a grid cell has no visible pixels."""
    x = col * grid.cell_width
    y = row * grid.cell_height
    for py in range(y, y + grid.cell_height):
        for px in range(x, x + grid.cell_width):
            if image.pixelColor(px, py).alpha() > 0:
                return False
    return True


def _extract_cell(image, row: int, col: int, grid: CodexGrid):
    """Copy one spritesheet cell into a new image."""
    QImage = _load_qimage()
    x = col * grid.cell_width
    y = row * grid.cell_height
    return image.copy(x, y, grid.cell_width, grid.cell_height)


def _cache_dir(pack_dir: Path) -> Path:
    return pack_dir.resolve() / _CACHE_DIR_NAME


def _cache_stamp_path(pack_dir: Path) -> Path:
    return _cache_dir(pack_dir) / ".source-stamp"


def _read_cache_stamp(pack_dir: Path) -> str | None:
    path = _cache_stamp_path(pack_dir)
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _write_cache_stamp(pack_dir: Path, spritesheet: Path) -> None:
    cache = _cache_dir(pack_dir)
    cache.mkdir(parents=True, exist_ok=True)
    stamp = f"{spritesheet.resolve()}|{spritesheet.stat().st_mtime_ns}"
    _cache_stamp_path(pack_dir).write_text(stamp, encoding="utf-8")


def _cache_is_current(pack_dir: Path, spritesheet: Path) -> bool:
    stamp = _read_cache_stamp(pack_dir)
    if stamp is None:
        return False
    expected = f"{spritesheet.resolve()}|{spritesheet.stat().st_mtime_ns}"
    return stamp == expected


def _export_frame(
    image,
    grid: CodexGrid,
    row: int,
    col: int,
    dest: Path,
) -> bool:
    """Write one spritesheet cell to ``dest`` when it contains pixels."""
    if row >= grid.rows or col >= GRID_COLUMNS:
        return False
    if _cell_is_empty(image, row, col, grid):
        return False
    cell = _extract_cell(image, row, col, grid)
    if cell.isNull():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    return cell.save(str(dest), "PNG")


def load_codex_spritesheet(spritesheet: Path):
    """Load a Codex spritesheet as a :class:`QImage`."""
    QImage = _load_qimage()
    image = QImage(str(spritesheet))
    return image if not image.isNull() else None


def codex_grid_for_pack(pack_dir: Path) -> tuple[Path, CodexGrid] | None:
    """Return the spritesheet path and grid geometry for a Codex pack."""
    pack_dir = pack_dir.resolve()
    manifest = None
    pet_json = find_pet_json(pack_dir)
    if pet_json is not None:
        manifest = parse_pet_manifest(pet_json)

    spritesheet = find_spritesheet(pack_dir, manifest)
    if spritesheet is None:
        return None

    image = load_codex_spritesheet(spritesheet)
    if image is None:
        return None

    version = manifest.sprite_version if manifest is not None else None
    grid = grid_for_image_size(
        image.width(),
        image.height(),
        sprite_version=version,
    )
    if grid is None:
        return None
    return spritesheet, grid


def is_codex_pack(sprites_dir: Path) -> bool:
    """True when the folder contains a readable Codex spritesheet."""
    if not sprites_dir.is_dir():
        return False
    return resolve_codex_frames(sprites_dir) is not None


def _resolve_frame_path(
    pack_dir: Path,
    spritesheet: Path,
    image,
    grid: CodexGrid,
    row: int,
    col: int,
    filename: str,
) -> Path | None:
    cache = _cache_dir(pack_dir)
    dest = cache / filename
    if not _cache_is_current(pack_dir, spritesheet):
        if cache.exists():
            shutil.rmtree(cache, ignore_errors=True)
        _write_cache_stamp(pack_dir, spritesheet)

    if dest.is_file():
        return dest
    if _export_frame(image, grid, row, col, dest):
        return dest
    return None


def resolve_codex_frames(pack_dir: Path) -> dict[str, list[Path]] | None:
    """
    Map a Codex pet folder to py-shimeji animation groups.

    Frames are extracted from the spritesheet into ``.py-shimeji-cache/``.
    """
    from config import SPRITE_FILES

    info = codex_grid_for_pack(pack_dir)
    if info is None:
        return None

    spritesheet, grid = info
    image = load_codex_spritesheet(spritesheet)
    if image is None:
        return None

    resolved: dict[str, list[Path]] = {}
    for state, filenames in SPRITE_FILES.items():
        coords = STATE_ROW_FRAMES.get(state, ())
        limit = STATE_FRAME_LIMITS.get(state, len(filenames))
        paths: list[Path] = []

        for index in range(min(limit, len(filenames))):
            if index < len(coords):
                row, col = coords[index]
            elif coords:
                row, col = coords[-1]
            else:
                break
            path = _resolve_frame_path(
                pack_dir,
                spritesheet,
                image,
                grid,
                row,
                col,
                filenames[index],
            )
            if path is not None:
                paths.append(path)

        if state in {"idle", "walk"} and len(paths) == 1 and limit > 1:
            paths.append(paths[0])

        if paths:
            resolved[state] = paths

    return resolved or None


def convert_codex_pet(source_dir: Path, dest_dir: Path) -> bool:
    """
    Export a Codex pet pack to py-shimeji's native PNG filenames.

    Returns True when at least one frame was written.
    """
    from config import SPRITE_FILES

    info = codex_grid_for_pack(source_dir)
    if info is None:
        return False

    spritesheet, grid = info
    image = load_codex_spritesheet(spritesheet)
    if image is None:
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    wrote = False
    for state, filenames in SPRITE_FILES.items():
        coords = STATE_ROW_FRAMES.get(state, ())
        limit = STATE_FRAME_LIMITS.get(state, len(filenames))
        for index, filename in enumerate(filenames):
            if index >= limit or index >= len(coords):
                continue
            row, col = coords[index]
            if _export_frame(image, grid, row, col, dest_dir / filename):
                wrote = True
    return wrote
