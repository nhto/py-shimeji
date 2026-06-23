"""Application-wide constants and paths for the Shimeji desktop pet."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load key=value pairs from a local .env file when present."""
    env_path = Path(__file__).resolve().parent / ".env"
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


_load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent
SPRITES_ROOT: Path = PROJECT_ROOT / "assets" / "sprites"

# Legacy alias (shared folder before per-pet directories).
ASSETS_DIR: Path = SPRITES_ROOT

# Expected sprite filenames per state (frames are cycled in order).
SPRITE_FILES: dict[str, list[str]] = {
    "idle": ["idle_1.png", "idle_2.png"],
    "walk": ["walk_1.png", "walk_2.png"],
    "sit": ["sit_1.png"],
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

TOP_PERCH_MARGIN_PX: int = 80

ANIMATION_INTERVAL_MS: int = 120
BEHAVIOR_INTERVAL_MS: int = 500
IDLE_TO_WALK_MIN_MS: int = 1_000
IDLE_TO_WALK_MAX_MS: int = 2_500
WALK_TO_IDLE_MIN_MS: int = 1_000
WALK_TO_IDLE_MAX_MS: int = 2_500
IDLE_TO_SIT_MIN_MS: int = 20_000
IDLE_TO_SIT_MAX_MS: int = 40_000
SIT_TO_IDLE_MIN_MS: int = 2_000
SIT_TO_IDLE_MAX_MS: int = 4_000

# ---------------------------------------------------------------------------
# Movement & physics
# ---------------------------------------------------------------------------

MOVEMENT_SPEED_SCALE: float = 0.8

WALK_SPEED_PX: int = 3
CLIMB_SPEED_PX: int = 4
GRAVITY_PX: int = 8
_BASE_MOVE_TICK_MS: int = 16
FALL_TICK_MS: int = max(1, round(_BASE_MOVE_TICK_MS / MOVEMENT_SPEED_SCALE))
SURFACE_REFRESH_MS: int = 400

# Minimum window size to treat as a climbable surface (Windows).
MIN_WINDOW_WIDTH: int = 120
MIN_WINDOW_HEIGHT: int = 80

# ---------------------------------------------------------------------------
# Multi-pet
# ---------------------------------------------------------------------------

MAX_PETS: int = 2

# ---------------------------------------------------------------------------
# AI chat (OpenRouter)
# ---------------------------------------------------------------------------

OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
ENV_FILE_PATH: Path = PROJECT_ROOT / ".env"

_OPENROUTER_KEY_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "",
        "your-openrouter-api-key-here",
    }
)


def get_openrouter_api_key() -> str:
    """Return the current OpenRouter API key from the process environment."""
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


# Legacy alias; prefer get_openrouter_api_key() after runtime updates.
OPENROUTER_API_KEY: str = get_openrouter_api_key()


def has_openrouter_api_key() -> bool:
    """True when a non-placeholder OpenRouter API key is configured."""
    key = get_openrouter_api_key()
    return key.lower() not in {p.lower() for p in _OPENROUTER_KEY_PLACEHOLDERS}


def set_openrouter_api_key(key: str) -> None:
    """Persist an OpenRouter API key to .env and apply it for this session."""
    normalized = key.strip()
    os.environ["OPENROUTER_API_KEY"] = normalized
    _persist_env_var("OPENROUTER_API_KEY", normalized)


def _persist_env_var(name: str, value: str) -> None:
    """Update or remove a single key=value entry in the local .env file."""
    lines: list[str] = []
    if ENV_FILE_PATH.is_file():
        lines = ENV_FILE_PATH.read_text(encoding="utf-8").splitlines()

    new_lines: list[str] = []
    found = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue

        key, _ = stripped.split("=", 1)
        if key.strip() == name:
            found = True
            if value:
                new_lines.append(f"{name}={value}")
        else:
            new_lines.append(line)

    if value and not found:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(f"{name}={value}")

    if not new_lines and value:
        new_lines = [
            "# Get a key at https://openrouter.ai/keys",
            f"{name}={value}",
        ]

    content = "\n".join(new_lines)
    if content and not content.endswith("\n"):
        content += "\n"
    ENV_FILE_PATH.write_text(content, encoding="utf-8")

CHAT_MODELS: list[tuple[str, str]] = [
    ("openrouter/owl-alpha", "Owl Alpha"),
    ("qwen/qwen3.7-plus", "Qwen 3.7 Plus"),
    ("deepseek/deepseek-v4-pro", "DeepSeek V4 Pro"),
    ("xiaomi/mimo-v2.5-pro", "MiMo V2.5 Pro"),
]

CHAT_MODEL_SUPPORTS_IMAGES: frozenset[str] = frozenset(
    {
        "qwen/qwen3.7-plus",
    }
)

_CHAT_SETTINGS_PATH: Path = PROJECT_ROOT / ".chat_settings.json"


def _load_chat_settings() -> dict:
    if _CHAT_SETTINGS_PATH.is_file():
        try:
            data = json.loads(_CHAT_SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return {}


def _save_chat_settings(**updates: object) -> None:
    data = _load_chat_settings()
    data.update(updates)
    _CHAT_SETTINGS_PATH.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )


def _valid_chat_model_ids() -> set[str]:
    return {model_id for model_id, _ in CHAT_MODELS}


def get_chat_model() -> str:
    """Return the persisted chat model, or a sensible default."""
    model = _load_chat_settings().get("model", "")
    if isinstance(model, str) and model in _valid_chat_model_ids():
        return model

    env_model = os.environ.get("OPENROUTER_MODEL", "")
    if env_model in _valid_chat_model_ids():
        return env_model

    return CHAT_MODELS[0][0]


def set_chat_model(model_id: str) -> None:
    """Persist the user's chat model choice."""
    if model_id not in _valid_chat_model_ids():
        return
    _save_chat_settings(model=model_id)


def chat_model_supports_images(model_id: str) -> bool:
    """Return whether the model accepts image input via OpenRouter."""
    return model_id in CHAT_MODEL_SUPPORTS_IMAGES


CHAT_DEFAULT_LANGUAGE: str = "zh-Hant"

CHAT_LANGUAGES: list[tuple[str, str]] = [
    ("en", "English"),
    ("zh-Hans", "Simplified Chinese"),
    ("zh-Hant", "Traditional Chinese"),
]

CHAT_LANGUAGE_INSTRUCTIONS: dict[str, str] = {
    "en": "Always reply in English, regardless of the language the user writes in.",
    "zh-Hans": "Always reply in Simplified Chinese (简体中文), regardless of the language the user writes in.",
    "zh-Hant": "Always reply in Traditional Chinese (繁體中文), regardless of the language the user writes in.",
}

CHAT_GREETINGS: dict[str, str] = {
    "en": (
        "Hi! I'm Bubu. Ask me anything — I'm happy to chat while I hang out on your desktop."
    ),
    "zh-Hans": "你好！我是 Bubu。随便问我什么吧——我很乐意一边陪你逛桌面一边聊天。",
    "zh-Hant": "你好！我是 Bubu。隨便問我什麼吧——我很樂意一邊陪你逛桌面一邊聊天。",
}

CHAT_NO_API_KEY_GREETINGS: dict[str, str] = {
    "en": (
        "Hi! I'm Bubu. I'd love to chat, but no OpenRouter API key is set yet. "
        "Use OpenRouter API key... in the tray menu to add one."
    ),
    "zh-Hans": (
        "你好！我是 Bubu。我很想聊天，但还没有配置 OpenRouter API 密钥。"
        "请在托盘菜单中选择 OpenRouter API key... 进行设置。"
    ),
    "zh-Hant": (
        "你好！我是 Bubu。我很想聊天，但還沒有設定 OpenRouter API 金鑰。"
        "請在系統匣選單中選擇 OpenRouter API key... 進行設定。"
    ),
}

CHAT_NO_API_KEY_SEND_LABELS: dict[str, str] = {
    "en": "Add your OpenRouter API key from the tray menu to chat.",
    "zh-Hans": "请从托盘菜单设置 OpenRouter API 密钥后再聊天。",
    "zh-Hant": "請從系統匣選單設定 OpenRouter API 金鑰後再聊天。",
}

CHAT_STATUS_ONLINE_LABELS: dict[str, str] = {
    "en": "Online",
    "zh-Hans": "在线",
    "zh-Hant": "線上",
}

CHAT_STATUS_OFFLINE_LABELS: dict[str, str] = {
    "en": "No API key",
    "zh-Hans": "未配置密钥",
    "zh-Hant": "未設定金鑰",
}

TRAY_NO_API_KEY_TITLE: str = "py-shimeji — chat unavailable"
TRAY_NO_API_KEY_MESSAGE: str = (
    "Choose OpenRouter API key... in the tray menu to chat with Bubu."
)
TRAY_API_KEY_SAVED_MESSAGE: str = "OpenRouter API key saved. You can chat with Bubu now."
TRAY_API_KEY_CLEARED_MESSAGE: str = "OpenRouter API key removed. Chat is disabled."

CHAT_INPUT_PLACEHOLDERS: dict[str, str] = {
    "en": "Say something to Bubu...",
    "zh-Hans": "跟 Bubu 说点什么...",
    "zh-Hant": "跟 Bubu 說點什麼...",
}

CHAT_SEND_LABELS: dict[str, str] = {
    "en": "Send",
    "zh-Hans": "发送",
    "zh-Hant": "傳送",
}

CHAT_ATTACH_IMAGE_LABELS: dict[str, str] = {
    "en": "Attach image",
    "zh-Hans": "附加图片",
    "zh-Hant": "附加圖片",
}

CHAT_IMAGE_ONLY_LABELS: dict[str, str] = {
    "en": "Image",
    "zh-Hans": "图片",
    "zh-Hant": "圖片",
}

CHAT_IMAGE_TOO_LARGE_LABELS: dict[str, str] = {
    "en": "Image must be 4 MB or smaller.",
    "zh-Hans": "图片不能超过 4 MB。",
    "zh-Hant": "圖片不能超過 4 MB。",
}

CHAT_IMAGE_UNSUPPORTED_LABELS: dict[str, str] = {
    "en": "Please choose a PNG, JPEG, GIF, or WebP image.",
    "zh-Hans": "请选择 PNG、JPEG、GIF 或 WebP 图片。",
    "zh-Hant": "請選擇 PNG、JPEG、GIF 或 WebP 圖片。",
}

CHAT_MAX_IMAGE_BYTES: int = 4 * 1024 * 1024


def _valid_chat_language_ids() -> set[str]:
    return {lang_id for lang_id, _ in CHAT_LANGUAGES}


def get_chat_language() -> str:
    """Return the persisted reply language, or Traditional Chinese by default."""
    language = _load_chat_settings().get("language", "")
    if isinstance(language, str) and language in _valid_chat_language_ids():
        return language
    return CHAT_DEFAULT_LANGUAGE


def set_chat_language(language_id: str) -> None:
    """Persist the user's preferred reply language."""
    if language_id not in _valid_chat_language_ids():
        return
    _save_chat_settings(language=language_id)


def build_chat_system_prompt(language: str | None = None) -> str:
    """Build the system prompt with a language-specific reply instruction."""
    lang = language if language in _valid_chat_language_ids() else get_chat_language()
    instruction = CHAT_LANGUAGE_INSTRUCTIONS.get(lang, CHAT_LANGUAGE_INSTRUCTIONS["en"])
    return f"{CHAT_SYSTEM_PROMPT} {instruction}"


CHAT_MAX_HISTORY: int = 20
CHAT_WINDOW_WIDTH: int = 360
CHAT_WINDOW_HEIGHT: int = 460
CHAT_WINDOW_GAP_PX: int = 14
CHAT_SYSTEM_PROMPT: str = (
    "You are Bubu, a cute and playful brown bear desktop pet in the py-shimeji app. "
    "You live on the user's screen, walk along window edges, sit, and sometimes fall. "
    "Reply in a warm, friendly, slightly whimsical tone. Keep answers concise unless "
    "the user asks for detail. Use simple language. You may use the occasional bear "
    "or paw emoji, but don't overdo it."
)

# Pet-to-pet interaction while walking on the same ledge.
PEER_INTERACTION_Y_TOLERANCE_PX: int = 16
PEER_NUDGE_PX: int = 5
PEER_SIT_ON_BUMP_CHANCE: float = 0.2

# Cursor chase: walk toward the mouse on the same ledge, then sit when it stays still.
CURSOR_CHASE_CHANCE: float = 0.12
CURSOR_CHASE_MIN_MS: int = 3_000
CURSOR_CHASE_MAX_MS: int = 10_000
CURSOR_SIT_DISTANCE_PX: int = 28
CURSOR_STILL_MS: int = 700
CURSOR_STILL_TOLERANCE_PX: int = 10
CURSOR_Y_TOLERANCE_PX: int = 56

# ---------------------------------------------------------------------------
# Fallback rendering (used when sprite files are missing)
# ---------------------------------------------------------------------------

FALLBACK_BODY_COLOR: str = "#FF6B9D"
FALLBACK_OUTLINE_COLOR: str = "#2D1B2E"
FALLBACK_EYE_COLOR: str = "#FFFFFF"
FALLBACK_PUPIL_COLOR: str = "#1A1A2E"

# Per-pet fallback palettes when multiple pets are active.
PET_FALLBACK_PALETTES: list[dict[str, str]] = [
    {
        "body": FALLBACK_BODY_COLOR,
        "outline": FALLBACK_OUTLINE_COLOR,
        "eye": FALLBACK_EYE_COLOR,
        "pupil": FALLBACK_PUPIL_COLOR,
    },
    {
        "body": "#4ECDC4",
        "outline": "#1A3A3A",
        "eye": "#FFFFFF",
        "pupil": "#0D2B2B",
    },
]


def get_pet_sprites_dir(pet_index: int) -> Path:
    """
    Return the sprite folder for a pet.

    Each pet loads PNGs from ``assets/sprites/pet_N/`` (N is 1-based).
    Pet 1 falls back to the legacy flat ``assets/sprites/`` folder when
    ``pet_1/`` does not exist but shared sprite files are present.
    """
    per_pet = SPRITES_ROOT / f"pet_{pet_index + 1}"
    if per_pet.is_dir():
        return per_pet
    if pet_index == 0 and _legacy_shared_sprites_present():
        return SPRITES_ROOT
    return per_pet


def _legacy_shared_sprites_present() -> bool:
    """True when PNGs still live directly under assets/sprites/."""
    return any((SPRITES_ROOT / name).is_file() for names in SPRITE_FILES.values() for name in names)


def pet_has_sprites(sprites_dir: Path) -> bool:
    """True when the folder contains at least one expected sprite PNG."""
    if not sprites_dir.is_dir():
        return False
    return any((sprites_dir / name).is_file() for names in SPRITE_FILES.values() for name in names)
