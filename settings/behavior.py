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
        "Hi there!",
        "Nice day!",
        "Hmm…",
        "La la la~",
        "I'm bored.",
        "Still here!",
        "Zzz… just kidding.",
        "What are you up to?",
        "Don't forget to stretch!",
        "Need a break?",
        "I'm keeping you company~",
        "So quiet today.",
        "Want to chat?",
        "This spot is comfy.",
        "I could use a snack…",
        "You're doing great!",
        "Take it easy~",
        "Just wandering~",
        "Peek-a-boo!",
        "Is it snack time yet?",
        "The desktop is my playground.",
        "I like hanging out here.",
        "Any plans today?",
        "Stay hydrated!",
        "You got this!",
        "I'm not sleepy… zzz",
        "Boing boing~",
        "Life is good~",
    ],
    "zh-Hans": [
        "*打哈欠*",
        "你好呀~",
        "嗨嗨！",
        "今天天气不错！",
        "嗯……",
        "啦啦啦~",
        "有点无聊。",
        "我还在哦！",
        "zzz…开玩笑的。",
        "你在忙什么呀？",
        "记得伸个懒腰！",
        "要不要休息一下？",
        "我陪你呢~",
        "今天好安静。",
        "想聊聊天吗？",
        "这里待着挺舒服。",
        "有点想吃点东西…",
        "你很棒哦！",
        "慢慢来~",
        "随便逛逛~",
        "躲猫猫！",
        "到零食时间了吗？",
        "桌面是我的游乐场。",
        "我喜欢待在这里。",
        "今天有什么计划？",
        "记得喝水！",
        "加油！",
        "我不困…zzz",
        "蹦蹦跳跳~",
        "生活真美好~",
    ],
    "zh-Hant": [
        "*打哈欠*",
        "你好呀~",
        "嗨嗨！",
        "今天天氣不錯！",
        "嗯……",
        "啦啦啦~",
        "有點無聊。",
        "我還在哦！",
        "zzz…開玩笑的。",
        "你在忙什麼呀？",
        "記得伸個懶腰！",
        "要不要休息一下？",
        "我陪你呢~",
        "今天好安靜。",
        "想聊聊天嗎？",
        "這裡待著挺舒服。",
        "有點想吃點東西…",
        "你很棒哦！",
        "慢慢來~",
        "隨便逛逛~",
        "躲貓貓！",
        "到零食時間了嗎？",
        "桌面是我的遊樂場。",
        "我喜歡待在這裡。",
        "今天有什麼計劃？",
        "記得喝水！",
        "加油！",
        "我不困…zzz",
        "蹦蹦跳跳~",
        "生活真美好~",
    ],
}

AMBIENT_BUMP_PHRASES: dict[str, list[str]] = {
    "en": [
        "Oof!",
        "Hey!",
        "Watch it!",
        "Boop.",
        "Excuse me!",
        "Personal space!",
        "Bump!",
        "Whoa there!",
        "Careful~",
        "That was close.",
        "Hey, I'm walking here!",
        "Oopsie!",
    ],
    "zh-Hans": [
        "哎呀！",
        "嘿！",
        "看着点！",
        "咚。",
        "借过借过！",
        "注意点啦！",
        "撞到了！",
        "哇！",
        "小心~",
        "好险。",
        "让一让嘛！",
        "不好意思！",
    ],
    "zh-Hant": [
        "哎呀！",
        "嘿！",
        "看著點！",
        "咚。",
        "借過借過！",
        "注意點啦！",
        "撞到了！",
        "哇！",
        "小心~",
        "好險。",
        "讓一讓嘛！",
        "不好意思！",
    ],
}

AMBIENT_LAND_PHRASES: dict[str, list[str]] = {
    "en": [
        "Safe!",
        "That was a drop.",
        "Whew.",
        "Landed~",
        "Made it!",
        "Gravity wins again.",
        "Soft landing~",
        "I'm okay!",
        "That was scary…",
        "Back on solid ground.",
        "Phew~",
        "Ten points!",
    ],
    "zh-Hans": [
        "安全落地！",
        "好险。",
        "呼~",
        "着陆~",
        "成功！",
        "重力又赢了。",
        "软着陆~",
        "我没事！",
        "吓死我了…",
        "回到地面了。",
        "呼~",
        "满分落地！",
    ],
    "zh-Hant": [
        "安全落地！",
        "好險。",
        "呼~",
        "著陸~",
        "成功！",
        "重力又贏了。",
        "軟著陸~",
        "我沒事！",
        "嚇死我了…",
        "回到地面了。",
        "呼~",
        "滿分落地！",
    ],
}

AMBIENT_POKE_PHRASES: dict[str, list[str]] = {
    "en": [
        "Hey!",
        "Poke!",
        "*boop*",
        "That tickles~",
        "Again?",
        "Hi there!",
        "Mmh?",
        "Stop it~",
        "Hehe!",
        "You found me!",
        "What is it?",
        "I'm shy…",
        "More pokes!",
        "That feels nice~",
        "Hello hello!",
    ],
    "zh-Hans": [
        "嘿！",
        "戳戳！",
        "*啵*",
        "好痒~",
        "又来？",
        "你好呀！",
        "嗯？",
        "别戳啦~",
        "嘿嘿！",
        "找到我啦！",
        "怎么了？",
        "好害羞…",
        "再戳一下！",
        "好舒服~",
        "你好你好！",
    ],
    "zh-Hant": [
        "嘿！",
        "戳戳！",
        "*啵*",
        "好癢~",
        "又來？",
        "你好呀！",
        "嗯？",
        "別戳啦~",
        "嘿嘿！",
        "找到我啦！",
        "怎麼了？",
        "好害羞…",
        "再戳一下！",
        "好舒服~",
        "你好你好！",
    ],
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
    elif event == "poke":
        phrases = AMBIENT_POKE_PHRASES.get(language, AMBIENT_POKE_PHRASES["en"])
    else:
        phrases = AMBIENT_SPEECH_PHRASES.get(language, AMBIENT_SPEECH_PHRASES["en"])
    if not phrases:
        return None
    return random.choice(phrases)
