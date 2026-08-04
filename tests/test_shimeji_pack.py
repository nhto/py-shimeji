"""Unit tests for Shimeji actions.xml sprite import."""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtGui import QColor, QImage

from shimeji_pack import (
    SHIMEJI_TICK_MS,
    parse_action_sequences,
    resolve_shimeji_animations,
    resolve_sprite_animations,
    sprite_pack_kind,
)


def _write_png(path: Path, color: QColor) -> None:
    image = QImage(32, 32, QImage.Format.Format_ARGB32)
    image.fill(color)
    assert image.save(str(path), "PNG")


@pytest.fixture
def shimeji_pack(tmp_path: Path) -> Path:
    """Minimal Shimeji pack with multi-frame walk, climb, and sit actions."""
    pack = tmp_path / "test-shimeji"
    conf = pack / "conf"
    conf.mkdir(parents=True)

    colors = {
        "stand1.png": QColor(255, 0, 0, 255),
        "stand2.png": QColor(255, 64, 0, 255),
        "walk1.png": QColor(0, 255, 0, 255),
        "walk2.png": QColor(0, 200, 0, 255),
        "walk3.png": QColor(0, 150, 0, 255),
        "walk4.png": QColor(0, 100, 0, 255),
        "climb1.png": QColor(0, 0, 255, 255),
        "climb2.png": QColor(0, 0, 200, 255),
        "climb3.png": QColor(0, 0, 150, 255),
        "sit1.png": QColor(255, 255, 0, 255),
        "sit2.png": QColor(255, 220, 0, 255),
    }
    for name, color in colors.items():
        _write_png(pack / name, color)

    actions_xml = conf / "actions.xml"
    actions_xml.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<Mascot>
  <ActionList>
    <Action Name="Stand" Type="Stay" BorderType="Floor">
      <Animation>
        <Pose Image="/stand1.png" Duration="50"/>
        <Pose Image="/stand2.png" Duration="50"/>
      </Animation>
    </Action>
    <Action Name="Walk" Type="Move" BorderType="Floor">
      <Animation>
        <Pose Image="/walk1.png" Duration="3"/>
        <Pose Image="/walk2.png" Duration="3"/>
        <Pose Image="/walk3.png" Duration="3"/>
        <Pose Image="/walk4.png" Duration="3"/>
      </Animation>
    </Action>
    <Action Name="ClimbWall" Type="Move" BorderType="Wall">
      <Animation>
        <Pose Image="/climb1.png" Duration="2"/>
        <Pose Image="/climb2.png" Duration="2"/>
        <Pose Image="/climb3.png" Duration="2"/>
      </Animation>
    </Action>
    <Action Name="Sit" Type="Stay" BorderType="Floor">
      <Animation>
        <Pose Image="/sit1.png" Duration="30"/>
        <Pose Image="/sit2.png" Duration="30"/>
      </Animation>
    </Action>
  </ActionList>
</Mascot>
""",
        encoding="utf-8",
    )
    return pack


def test_parse_action_sequences_reads_durations(shimeji_pack: Path) -> None:
    sequences = parse_action_sequences(shimeji_pack / "conf" / "actions.xml")
    assert sequences["Walk"] == [
        ("walk1.png", 3),
        ("walk2.png", 3),
        ("walk3.png", 3),
        ("walk4.png", 3),
    ]
    assert sequences["ClimbWall"][0] == ("climb1.png", 2)


def test_resolve_shimeji_animations_uses_full_sequences(shimeji_pack: Path) -> None:
    animations = resolve_shimeji_animations(shimeji_pack)
    assert animations is not None
    assert len(animations["idle"].paths) == 2
    assert len(animations["walk"].paths) == 4
    assert len(animations["climb"].paths) == 3
    assert len(animations["sit"].paths) == 2


def test_resolve_shimeji_animations_preserves_pose_durations(shimeji_pack: Path) -> None:
    animations = resolve_shimeji_animations(shimeji_pack)
    assert animations is not None
    walk = animations["walk"]
    assert walk.durations_ms is not None
    assert walk.durations_ms == [round(3 * SHIMEJI_TICK_MS)] * 4


def test_climb_is_separate_from_walk(shimeji_pack: Path) -> None:
    animations = resolve_shimeji_animations(shimeji_pack)
    assert animations is not None
    walk_names = {path.name for path in animations["walk"].paths}
    climb_names = {path.name for path in animations["climb"].paths}
    assert "climb1.png" in climb_names
    assert climb_names.isdisjoint(walk_names)


def test_sprite_pack_kind_detects_shimeji(shimeji_pack: Path) -> None:
    assert sprite_pack_kind(shimeji_pack) == "shimeji"


def test_resolve_sprite_animations_for_shimeji_pack(shimeji_pack: Path) -> None:
    animations = resolve_sprite_animations(shimeji_pack)
    assert len(animations["walk"].paths) == 4
    assert animations["climb"].durations_ms is not None
