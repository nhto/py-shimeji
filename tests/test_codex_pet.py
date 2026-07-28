"""Unit tests for Codex Pet spritesheet import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PyQt6.QtGui import QColor, QImage

from codex_pet import (
    CELL_HEIGHT,
    CELL_WIDTH,
    GRID_COLUMNS,
    V1_ROWS,
    convert_codex_pet,
    grid_for_image_size,
    is_codex_pack,
    resolve_codex_frames,
)
from shimeji_pack import sprite_pack_kind


def _make_codex_spritesheet(path: Path, *, rows: int = V1_ROWS) -> None:
    width = GRID_COLUMNS * CELL_WIDTH
    height = rows * CELL_HEIGHT
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))

    colors = [
        QColor(255, 0, 0, 255),
        QColor(0, 255, 0, 255),
        QColor(0, 0, 255, 255),
        QColor(255, 255, 0, 255),
        QColor(255, 0, 255, 255),
        QColor(0, 255, 255, 255),
    ]
    for row in range(rows):
        for col in range(GRID_COLUMNS):
            color = colors[(row + col) % len(colors)]
            for py in range(row * CELL_HEIGHT, (row + 1) * CELL_HEIGHT):
                for px in range(col * CELL_WIDTH, (col + 1) * CELL_WIDTH):
                    image.setPixelColor(px, py, color)

    assert image.save(str(path), "PNG")


@pytest.fixture
def codex_pack(tmp_path: Path, qapp) -> Path:
    """Minimal Codex Pet folder with pet.json and spritesheet.png."""
    pack = tmp_path / "test-codie"
    pack.mkdir()
    spritesheet = pack / "spritesheet.png"
    _make_codex_spritesheet(spritesheet)
    manifest = {
        "id": "test-codie",
        "displayName": "Test Codie",
        "description": "Test pack",
        "spritesheetPath": "spritesheet.png",
        "spriteVersionNumber": 1,
    }
    (pack / "pet.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pack


def test_grid_for_image_size_v1() -> None:
    grid = grid_for_image_size(1536, 1872, sprite_version=1)
    assert grid is not None
    assert grid.rows == V1_ROWS
    assert grid.cell_width == CELL_WIDTH
    assert grid.cell_height == CELL_HEIGHT


def test_is_codex_pack_detects_manifest_folder(codex_pack: Path) -> None:
    assert is_codex_pack(codex_pack)
    assert sprite_pack_kind(codex_pack) == "codex"


def test_resolve_codex_frames_maps_idle_and_walk(codex_pack: Path) -> None:
    frames = resolve_codex_frames(codex_pack)
    assert frames is not None
    assert len(frames["idle"]) == 2
    assert len(frames["walk"]) == 2
    assert frames["idle"][0].is_file()
    assert frames["walk"][0].is_file()


def test_convert_codex_pet_writes_native_pngs(codex_pack: Path, tmp_path: Path) -> None:
    dest = tmp_path / "converted"
    assert convert_codex_pet(codex_pack, dest)
    assert (dest / "idle_1.png").is_file()
    assert (dest / "walk_1.png").is_file()
    assert (dest / "fall_1.png").is_file()
    assert (dest / "drag_1.png").is_file()
    assert sprite_pack_kind(dest) == "native"
