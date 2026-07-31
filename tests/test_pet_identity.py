"""Unit tests for per-pet display names and chat personalities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codex_pet import load_codex_pet_metadata, parse_pet_manifest
from config import (
    build_chat_system_prompt,
    get_pet_name,
    set_pet_name,
    set_pet_personality,
)
from settings.chat import default_pet_name, pet_personality_line
from settings.persistence import get_saved_pet_display_name, get_saved_pet_personality


@pytest.fixture
def codex_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "test-pet.codex-pet"
    pack.mkdir()
    manifest = {
        "id": "test-pet",
        "displayName": "Test Codie",
        "description": "A cheerful test companion who loves snacks.",
        "spritesheetPath": "spritesheet.webp",
    }
    (pack / "pet.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pack


def test_parse_pet_manifest_reads_display_name_and_description(codex_pack: Path) -> None:
    manifest = parse_pet_manifest(codex_pack / "pet.json")
    assert manifest is not None
    assert manifest.display_name == "Test Codie"
    assert manifest.description == "A cheerful test companion who loves snacks."


def test_load_codex_pet_metadata(codex_pack: Path) -> None:
    metadata = load_codex_pet_metadata(codex_pack)
    assert metadata is not None
    assert metadata.display_name == "Test Codie"


def test_get_pet_name_uses_saved_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "settings.sprites.get_pet_sprites_dir",
        lambda _index: Path("/nonexistent/sprites"),
    )
    set_pet_name("Mochi", pet_index=1)
    try:
        assert get_pet_name(1) == "Mochi"
        assert get_saved_pet_display_name(1) == "Mochi"
    finally:
        set_pet_name("", pet_index=1)


def test_default_pet_name_uses_codex_display_name(
    monkeypatch: pytest.MonkeyPatch,
    codex_pack: Path,
) -> None:
    monkeypatch.setattr(
        "settings.sprites.get_pet_sprites_dir",
        lambda _index: codex_pack,
    )
    assert default_pet_name(0) == "Test Codie"
    assert get_pet_name(0) == "Test Codie"


def test_pet_personality_line_prefers_custom_override(
    monkeypatch: pytest.MonkeyPatch,
    codex_pack: Path,
) -> None:
    monkeypatch.setattr(
        "settings.sprites.get_pet_sprites_dir",
        lambda _index: codex_pack,
    )
    set_pet_personality("You speak like a pirate", pet_index=0)
    try:
        assert "pirate" in pet_personality_line(0)
    finally:
        set_pet_personality("", pet_index=0)


def test_pet_personality_line_uses_codex_description(
    monkeypatch: pytest.MonkeyPatch,
    codex_pack: Path,
) -> None:
    monkeypatch.setattr(
        "settings.sprites.get_pet_sprites_dir",
        lambda _index: codex_pack,
    )
    assert "cheerful test companion" in pet_personality_line(0)


def test_build_chat_system_prompt_includes_pet_name_and_personality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "settings.sprites.get_pet_sprites_dir",
        lambda _index: Path("/nonexistent/sprites"),
    )
    set_pet_name("Luna", pet_index=2)
    set_pet_personality("You are shy and poetic.", pet_index=2)
    try:
        prompt = build_chat_system_prompt("en", pet_index=2)
        assert "You are Luna" in prompt
        assert "shy and poetic" in prompt
    finally:
        set_pet_name("", pet_index=2)
        set_pet_personality("", pet_index=2)


def test_per_pet_names_are_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "settings.sprites.get_pet_sprites_dir",
        lambda index: Path(f"/nonexistent/pet_{index}"),
    )
    set_pet_name("Alpha", pet_index=0)
    set_pet_name("Beta", pet_index=1)
    try:
        assert get_pet_name(0) == "Alpha"
        assert get_pet_name(1) == "Beta"
    finally:
        set_pet_name("", pet_index=0)
        set_pet_name("", pet_index=1)
        assert get_saved_pet_personality(0) is None
        assert get_saved_pet_personality(1) is None
