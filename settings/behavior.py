"""User-tunable pet behavior settings and ambient speech phrases."""

from __future__ import annotations

import random

from settings.chat import get_chat_language
from settings.core import (
    AMBIENT_SPEECH_ENABLED_DEFAULT,
    BEHAVIOR_CURSOR_CHASE_DEFAULT,
    BEHAVIOR_CURSOR_CHASE_MAX,
    BEHAVIOR_CURSOR_CHASE_MIN,
    BEHAVIOR_SPEED_PERCENT_DEFAULT,
    BEHAVIOR_SPEED_PERCENT_MAX,
    BEHAVIOR_SPEED_PERCENT_MIN,
    CLIMB_SPEED_PX,
    FALL_TICK_MS,
    GRAVITY_PX,
    MAX_PETS,
    MAX_PET_COUNT,
    MIN_PET_COUNT,
    WALK_SPEED_PX,
)
from settings.persistence import clamp_float, clamp_int, load_app_settings, save_app_settings

AMBIENT_SPEECH_PHRASES: dict[str, list[str]] = {
    "en": [
        "*yawn*",
        "Hello~",
        "Nice day!",
        "Hmm…",
        "La la la~",
        "I'm bored.",
        "Still here!",
        "Zzz… just kidding.",
    ],
    "zh-Hans": [
        "*打哈欠*",
        "你好呀~",
        "今天天气不错！",
        "嗯……",
        "啦啦啦~",
        "有点无聊。",
        "我还在哦！",
        "zzz…开玩笑的。",
    ],
    "zh-Hant": [
        "*打哈欠*",
        "你好呀~",
        "今天天氣不錯！",
        "嗯……",
        "啦啦啦~",
        "有點無聊。",
        "我還在哦！",
        "zzz…開玩笑的。",
    ],
}

AMBIENT_BUMP_PHRASES: dict[str, list[str]] = {
    "en": ["Oof!", "Hey!", "Watch it!", "Boop."],
    "zh-Hans": ["哎呀！", "嘿！", "看着点！", "咚。"],
    "zh-Hant": ["哎呀！", "嘿！", "看著點！", "咚。"],
}

AMBIENT_LAND_PHRASES: dict[str, list[str]] = {
    "en": ["Safe!", "That was a drop.", "Whew.", "Landed~"],
    "zh-Hans": ["安全落地！", "好险。", "呼~", "着陆~"],
    "zh-Hant": ["安全落地！", "好險。", "呼~", "著陸~"],
}


def _behavior_settings() -> dict:
    behavior = load_app_settings().get("behavior", {})
    return behavior if isinstance(behavior, dict) else {}


def get_speed_percent() -> int:
    """Return the user movement speed as a percentage of the base speed."""
    raw = _behavior_settings().get("speed_percent", BEHAVIOR_SPEED_PERCENT_DEFAULT)
    return clamp_int(
        raw,
        BEHAVIOR_SPEED_PERCENT_MIN,
        BEHAVIOR_SPEED_PERCENT_MAX,
        BEHAVIOR_SPEED_PERCENT_DEFAULT,
    )


def get_cursor_chase_chance() -> float:
    """Return the probability (0–1) that an idle pet starts chasing the cursor."""
    raw = _behavior_settings().get("cursor_chase_chance", BEHAVIOR_CURSOR_CHASE_DEFAULT)
    return clamp_float(
        raw,
        BEHAVIOR_CURSOR_CHASE_MIN,
        BEHAVIOR_CURSOR_CHASE_MAX,
        BEHAVIOR_CURSOR_CHASE_DEFAULT,
    )


def get_saved_pet_count() -> int:
    """Return how many pets to spawn (persisted, or MAX_PETS by default)."""
    raw = _behavior_settings().get("pet_count", MAX_PETS)
    return clamp_int(raw, MIN_PET_COUNT, MAX_PET_COUNT, MAX_PETS)


def get_ambient_speech_enabled() -> bool:
    """Return whether pets should show ambient speech bubbles."""
    raw = _behavior_settings().get("ambient_speech_enabled", AMBIENT_SPEECH_ENABLED_DEFAULT)
    if isinstance(raw, bool):
        return raw
    return AMBIENT_SPEECH_ENABLED_DEFAULT


def get_effective_walk_speed_px() -> int:
    return max(1, round(WALK_SPEED_PX * get_speed_percent() / 100))


def get_effective_climb_speed_px() -> int:
    return max(1, round(CLIMB_SPEED_PX * get_speed_percent() / 100))


def get_effective_gravity_px() -> int:
    return max(1, round(GRAVITY_PX * get_speed_percent() / 100))


def get_move_tick_ms() -> int:
    """Movement timer interval; shorter when speed percent is higher."""
    return max(1, round(FALL_TICK_MS * 100 / get_speed_percent()))


def set_behavior_settings(
    *,
    speed_percent: int,
    cursor_chase_chance: float,
    pet_count: int,
    ambient_speech_enabled: bool,
) -> None:
    """Persist pet behavior settings."""
    data = load_app_settings()
    data["behavior"] = {
        "speed_percent": clamp_int(
            speed_percent,
            BEHAVIOR_SPEED_PERCENT_MIN,
            BEHAVIOR_SPEED_PERCENT_MAX,
            BEHAVIOR_SPEED_PERCENT_DEFAULT,
        ),
        "cursor_chase_chance": clamp_float(
            cursor_chase_chance,
            BEHAVIOR_CURSOR_CHASE_MIN,
            BEHAVIOR_CURSOR_CHASE_MAX,
            BEHAVIOR_CURSOR_CHASE_DEFAULT,
        ),
        "pet_count": clamp_int(pet_count, MIN_PET_COUNT, MAX_PET_COUNT, MAX_PETS),
        "ambient_speech_enabled": bool(ambient_speech_enabled),
    }
    save_app_settings(data)


def get_ambient_phrase(event: str | None = None) -> str | None:
    """Return a short ambient phrase for the current UI language."""
    language = get_chat_language()
    if event == "bump":
        phrases = AMBIENT_BUMP_PHRASES.get(language, AMBIENT_BUMP_PHRASES["en"])
    elif event == "land":
        phrases = AMBIENT_LAND_PHRASES.get(language, AMBIENT_LAND_PHRASES["en"])
    else:
        phrases = AMBIENT_SPEECH_PHRASES.get(language, AMBIENT_SPEECH_PHRASES["en"])
    if not phrases:
        return None
    return random.choice(phrases)
