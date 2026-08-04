"""Shimeji-EE / Group Fininity community sprite pack compatibility."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# Shimeji-EE advances poses on a ~30 Hz tick; Duration is measured in those ticks.
SHIMEJI_TICK_MS: float = 1000.0 / 30.0

# Map py-shimeji animation groups to Shimeji action names (first match wins).
STATE_ACTION_PRIORITY: dict[str, tuple[str, ...]] = {
    "idle": (
        "Stand",
        "Look",
        "StandUp",
        "StandUpAfterHideFromIe",
    ),
    "walk": (
        "Walk",
        "Run",
        "Dash",
        "WalkAlongWorkAreaFloor",
        "RunAlongWorkAreaFloor",
        "WalkAlongWorkAreaBottom",
        "RunAlongWorkAreaBottom",
    ),
    "climb": (
        "ClimbWall",
        "ClimbAlongWall",
        "ClimbCeiling",
        "ClimbAlongCeiling",
    ),
    "sit": (
        "Sit",
        "SitWhileDanglingLegs",
        "SitAndDangleLegs",
        "SitWithLegsDown",
        "SitWithLegsUp",
        "Sprawl",
        "SitDown",
        "SitAndLookAtMouse",
        "Sleep",
        "SleepOnFloor",
    ),
    "fall": (
        "Falling",
        "GrabWall",
        "GrabCeiling",
        "Tripping",
        "Bouncing",
    ),
    "drag": (
        "Pinched",
        "Resisting",
        "Dragged",
    ),
}

# Limits used only when exporting to native idle_1.png / walk_1.png filenames.
CONVERT_FRAME_LIMITS: dict[str, int] = {
    "idle": 2,
    "walk": 2,
    "climb": 2,
    "sit": 1,
    "fall": 1,
    "drag": 1,
}

_ACTIONS_XML_NAMES: tuple[str, ...] = ("actions.xml", "動作.xml", "Actions.xml")


@dataclass(frozen=True)
class SpriteAnimation:
    """Resolved sprite frames and optional per-frame dwell times."""

    paths: list[Path]
    durations_ms: list[int] | None = None


def _local_tag(element: ET.Element) -> str:
    tag = element.tag
    return tag.rpartition("}")[-1]


def _normalize_image_ref(image: str) -> str:
    """Turn a Pose Image attribute into a filename relative to the pack image root."""
    cleaned = image.strip().lstrip("/").replace("\\", "/")
    return Path(cleaned).name


def _parse_pose_duration(pose: ET.Element) -> int:
    raw = pose.get("Duration", "1")
    try:
        duration = int(raw)
    except (TypeError, ValueError):
        duration = 1
    return max(1, duration)


def find_actions_xml(pack_dir: Path) -> Path | None:
    """Locate a Shimeji actions file inside a sprite pack folder."""
    pack_dir = pack_dir.resolve()
    candidates = [
        pack_dir / "conf" / name for name in _ACTIONS_XML_NAMES
    ] + [pack_dir / name for name in _ACTIONS_XML_NAMES]
    for path in candidates:
        if path.is_file():
            return path
    return None


def image_root_for_actions(actions_xml: Path) -> Path:
    """Directory that contains the pack's PNG frames."""
    if actions_xml.parent.name.lower() == "conf":
        return actions_xml.parent.parent
    return actions_xml.parent


def parse_action_sequences(actions_xml: Path) -> dict[str, list[tuple[str, int]]]:
    """
    Parse action names and their animation sequences from actions.xml.

    Returns ``action -> [(image_filename, duration_ticks), ...]``.

    Only direct ``<Animation>`` children of each ``<Action>`` are considered so
    sequence-only actions (for example ``Fall``) do not pollute frame lists.
    """
    text = actions_xml.read_text(encoding="utf-8-sig")
    root = ET.fromstring(text)

    action_sequences: dict[str, list[tuple[str, int]]] = {}
    for element in root.iter():
        if _local_tag(element) != "Action":
            continue
        name = element.get("Name")
        if not name:
            continue

        frames: list[tuple[str, int]] = []
        for child in element:
            if _local_tag(child) != "Animation":
                continue
            for pose in child:
                if _local_tag(pose) != "Pose":
                    continue
                image = pose.get("Image")
                if not image:
                    continue
                frames.append(
                    (_normalize_image_ref(image), _parse_pose_duration(pose))
                )
        if frames:
            action_sequences[name] = frames
    return action_sequences


def parse_action_frames(actions_xml: Path) -> dict[str, list[str]]:
    """Parse action names and frame filenames (legacy helper, no timing)."""
    sequences = parse_action_sequences(actions_xml)
    return {
        name: [image for image, _duration in frames]
        for name, frames in sequences.items()
    }


def _find_image(image_root: Path, filename: str) -> Path | None:
    for base in (image_root, image_root / "img"):
        path = base / filename
        if path.is_file():
            return path.resolve()
    return None


def _resolve_action_sequence(
    action_frames: list[tuple[str, int]],
    image_root: Path,
    *,
    limit: int | None = None,
) -> SpriteAnimation | None:
    paths: list[Path] = []
    durations_ms: list[int] = []
    seen: set[str] = set()

    for image_name, duration_ticks in action_frames:
        if image_name in seen:
            continue
        path = _find_image(image_root, image_name)
        if path is None:
            continue
        seen.add(image_name)
        paths.append(path)
        durations_ms.append(max(1, round(duration_ticks * SHIMEJI_TICK_MS)))
        if limit is not None and len(paths) >= limit:
            break

    if not paths:
        return None
    return SpriteAnimation(paths=paths, durations_ms=durations_ms)


def resolve_shimeji_animations(pack_dir: Path) -> dict[str, SpriteAnimation] | None:
    """
    Map a Shimeji pack folder to py-shimeji animation groups with full sequences.

    Returns ``None`` when no actions.xml is present or no frames resolve.
    """
    actions_xml = find_actions_xml(pack_dir)
    if actions_xml is None:
        return None

    action_sequences = parse_action_sequences(actions_xml)
    if not action_sequences:
        return None

    image_root = image_root_for_actions(actions_xml)
    resolved: dict[str, SpriteAnimation] = {}

    for state, priorities in STATE_ACTION_PRIORITY.items():
        for action_name in priorities:
            sequence = action_sequences.get(action_name)
            if not sequence:
                continue
            animation = _resolve_action_sequence(sequence, image_root)
            if animation is not None:
                resolved[state] = animation
                break

    return resolved or None


def resolve_shimeji_frames(pack_dir: Path) -> dict[str, list[Path]] | None:
    """
    Map a Shimeji pack folder to py-shimeji animation groups.

    Returns ``None`` when no actions.xml is present or no frames resolve.
    """
    animations = resolve_shimeji_animations(pack_dir)
    if animations is None:
        return None
    return {state: anim.paths for state, anim in animations.items()}


def has_native_sprites(sprites_dir: Path) -> bool:
    """True when the folder uses py-shimeji's idle_1.png naming convention."""
    from config import SPRITE_FILES

    if not sprites_dir.is_dir():
        return False
    return any(
        (sprites_dir / name).is_file()
        for names in SPRITE_FILES.values()
        for name in names
    )


def is_shimeji_pack(sprites_dir: Path) -> bool:
    """True when actions.xml resolves to at least one usable frame."""
    if not sprites_dir.is_dir():
        return False
    frames = resolve_shimeji_frames(sprites_dir)
    return frames is not None and any(frames.values())


def sprite_pack_kind(sprites_dir: Path) -> str:
    """Return ``native``, ``shimeji``, ``codex``, or ``none`` for a sprite folder."""
    if has_native_sprites(sprites_dir):
        return "native"
    if is_shimeji_pack(sprites_dir):
        return "shimeji"
    from codex_pet import is_codex_pack

    if is_codex_pack(sprites_dir):
        return "codex"
    return "none"


def _native_sprite_animations(sprites_dir: Path) -> dict[str, SpriteAnimation]:
    from config import SPRITE_FILES

    return {
        state: SpriteAnimation(
            paths=[sprites_dir / name for name in filenames],
            durations_ms=None,
        )
        for state, filenames in SPRITE_FILES.items()
    }


def resolve_sprite_animations(sprites_dir: Path) -> dict[str, SpriteAnimation]:
    """
    Return animation-group data for native, Shimeji, or Codex sprite folders.

    Native py-shimeji names take precedence when present.
    """
    if has_native_sprites(sprites_dir):
        return _native_sprite_animations(sprites_dir)

    shimeji = resolve_shimeji_animations(sprites_dir)
    if shimeji:
        return shimeji

    from codex_pet import resolve_codex_frames

    codex = resolve_codex_frames(sprites_dir)
    if codex:
        return {
            state: SpriteAnimation(paths=paths, durations_ms=None)
            for state, paths in codex.items()
        }

    return _native_sprite_animations(sprites_dir)


def resolve_sprite_frame_paths(sprites_dir: Path) -> dict[str, list[Path]]:
    """
    Return animation-group -> image paths for native or Shimeji sprite folders.

    Native py-shimeji names take precedence when present.
    """
    return {
        state: animation.paths
        for state, animation in resolve_sprite_animations(sprites_dir).items()
    }


def preview_sprite_path(sprites_dir: Path) -> Path | None:
    """Best thumbnail candidate for a sprite folder."""
    paths = resolve_sprite_frame_paths(sprites_dir)
    for state in ("idle", "walk", "sit", "climb", "drag", "fall"):
        for path in paths.get(state, ()):
            if path.is_file():
                return path
    return None


def iter_sprite_display_entries(
    sprites_dir: Path | None,
) -> list[tuple[str, str, bool, bool]]:
    """
    Return checklist rows for the sprite picker.

    Each row is ``(state, display_label, optional, present)``.
    For Shimeji packs the label shows the mapped source file.
    """
    from config import SPRITE_FILES, SPRITE_OPTIONAL_STATES

    if sprites_dir is None:
        return [
            (state, filename, state in SPRITE_OPTIONAL_STATES, False)
            for state, filenames in SPRITE_FILES.items()
            for filename in filenames
        ]

    kind = sprite_pack_kind(sprites_dir)
    animations = resolve_sprite_animations(sprites_dir)
    entries: list[tuple[str, str, bool, bool]] = []

    for state, filenames in SPRITE_FILES.items():
        optional = state in SPRITE_OPTIONAL_STATES
        animation = animations.get(state)
        paths = animation.paths if animation is not None else []

        if kind == "shimeji" and len(paths) > len(filenames):
            for index, path in enumerate(paths):
                present = path.is_file()
                label = f"{state} {index + 1} ← {path.name}"
                entries.append((state, label, optional, present))
            continue

        for index, filename in enumerate(filenames):
            path = paths[index] if index < len(paths) else None
            present = path is not None and path.is_file()
            if kind == "shimeji" and present and path is not None:
                label = f"{filename} ← {path.name}"
            elif kind == "codex" and present and path is not None:
                label = f"{filename} ← {path.name}"
            else:
                label = filename
            entries.append((state, label, optional, present))
    return entries


def convert_shimeji_pack(source_dir: Path, dest_dir: Path) -> bool:
    """
    Export a Shimeji pack to py-shimeji's native PNG filenames.

    Returns True when at least one frame was written.
    """
    from config import SPRITE_FILES

    animations = resolve_shimeji_animations(source_dir)
    if not animations:
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    wrote = False
    for state, filenames in SPRITE_FILES.items():
        animation = animations.get(state)
        if animation is None:
            continue
        limit = CONVERT_FRAME_LIMITS.get(state, len(filenames))
        for index, filename in enumerate(filenames):
            if index >= limit or index >= len(animation.paths):
                continue
            shutil.copy2(animation.paths[index], dest_dir / filename)
            wrote = True
    return wrote
