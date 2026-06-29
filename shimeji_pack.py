"""Shimeji-EE / Group Finity community sprite pack compatibility."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

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
        "ClimbWall",
        "ClimbAlongWall",
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

STATE_FRAME_LIMITS: dict[str, int] = {
    "idle": 2,
    "walk": 2,
    "sit": 1,
    "fall": 1,
    "drag": 1,
}

_ACTIONS_XML_NAMES: tuple[str, ...] = ("actions.xml", "動作.xml", "Actions.xml")


def _local_tag(element: ET.Element) -> str:
    tag = element.tag
    return tag.rpartition("}")[-1]


def _normalize_image_ref(image: str) -> str:
    """Turn a Pose Image attribute into a filename relative to the pack image root."""
    cleaned = image.strip().lstrip("/").replace("\\", "/")
    return Path(cleaned).name


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


def parse_action_frames(actions_xml: Path) -> dict[str, list[str]]:
    """
    Parse action names and their animation frame filenames from actions.xml.

    Only direct ``<Animation>`` children of each ``<Action>`` are considered so
    sequence-only actions (for example ``Fall``) do not pollute frame lists.
    """
    text = actions_xml.read_text(encoding="utf-8-sig")
    root = ET.fromstring(text)

    action_frames: dict[str, list[str]] = {}
    for element in root.iter():
        if _local_tag(element) != "Action":
            continue
        name = element.get("Name")
        if not name:
            continue

        frames: list[str] = []
        for child in element:
            if _local_tag(child) != "Animation":
                continue
            for pose in child:
                if _local_tag(pose) != "Pose":
                    continue
                image = pose.get("Image")
                if image:
                    frames.append(_normalize_image_ref(image))
        if frames:
            action_frames[name] = frames
    return action_frames


def _find_image(image_root: Path, filename: str) -> Path | None:
    for base in (image_root, image_root / "img"):
        path = base / filename
        if path.is_file():
            return path.resolve()
    return None


def resolve_shimeji_frames(pack_dir: Path) -> dict[str, list[Path]] | None:
    """
    Map a Shimeji pack folder to py-shimeji animation groups.

    Returns ``None`` when no actions.xml is present or no frames resolve.
    """
    actions_xml = find_actions_xml(pack_dir)
    if actions_xml is None:
        return None

    action_frames = parse_action_frames(actions_xml)
    if not action_frames:
        return None

    image_root = image_root_for_actions(actions_xml)
    resolved: dict[str, list[Path]] = {}

    for state, priorities in STATE_ACTION_PRIORITY.items():
        limit = STATE_FRAME_LIMITS[state]
        paths: list[Path] = []
        seen: set[str] = set()

        for action_name in priorities:
            for image_name in action_frames.get(action_name, ()):
                if image_name in seen:
                    continue
                path = _find_image(image_root, image_name)
                if path is None:
                    continue
                seen.add(image_name)
                paths.append(path)
                if len(paths) >= limit:
                    break
            if len(paths) >= limit:
                break

        if state in {"idle", "walk"} and len(paths) == 1 and limit > 1:
            paths.append(paths[0])

        if paths:
            resolved[state] = paths

    return resolved or None


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
    """Return ``native``, ``shimeji``, or ``none`` for a sprite folder."""
    if has_native_sprites(sprites_dir):
        return "native"
    if is_shimeji_pack(sprites_dir):
        return "shimeji"
    return "none"


def resolve_sprite_frame_paths(sprites_dir: Path) -> dict[str, list[Path]]:
    """
    Return animation-group -> image paths for native or Shimeji sprite folders.

    Native py-shimeji names take precedence when present.
    """
    from config import SPRITE_FILES

    if has_native_sprites(sprites_dir):
        return {
            state: [sprites_dir / name for name in filenames]
            for state, filenames in SPRITE_FILES.items()
        }

    shimeji = resolve_shimeji_frames(sprites_dir)
    if shimeji:
        return shimeji

    return {
        state: [sprites_dir / name for name in filenames]
        for state, filenames in SPRITE_FILES.items()
    }


def preview_sprite_path(sprites_dir: Path) -> Path | None:
    """Best thumbnail candidate for a sprite folder."""
    paths = resolve_sprite_frame_paths(sprites_dir)
    for state in ("idle", "walk", "sit", "drag", "fall"):
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
    frame_paths = resolve_sprite_frame_paths(sprites_dir)
    entries: list[tuple[str, str, bool, bool]] = []

    for state, filenames in SPRITE_FILES.items():
        optional = state in SPRITE_OPTIONAL_STATES
        paths = frame_paths.get(state, [])
        for index, filename in enumerate(filenames):
            path = paths[index] if index < len(paths) else None
            present = path is not None and path.is_file()
            if kind == "shimeji" and present and path is not None:
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

    frames = resolve_shimeji_frames(source_dir)
    if not frames:
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)
    wrote = False
    for state, filenames in SPRITE_FILES.items():
        paths = frames.get(state, [])
        for index, filename in enumerate(filenames):
            if index >= len(paths):
                continue
            shutil.copy2(paths[index], dest_dir / filename)
            wrote = True
    return wrote
