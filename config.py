"""Application-wide constants and paths for the Shimeji desktop pet."""

from __future__ import annotations

import json
import os
import random
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
    return Path(__file__).resolve().parent


def _bundle_root() -> Path:
    """Read-only bundle root (PyInstaller extract dir, or project root in dev)."""
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


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


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = _app_data_root()
BUNDLE_ROOT: Path = _bundle_root()
SPRITES_ROOT: Path = BUNDLE_ROOT / "assets" / "sprites"

_load_dotenv(PROJECT_ROOT)

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

# States whose PNGs are nice-to-have; idle is used when sit frames are missing.
SPRITE_OPTIONAL_STATES: frozenset[str] = frozenset({"sit"})

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
MIN_PET_COUNT: int = 1
MAX_PET_COUNT: int = 4

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
        "Use Preference in the tray menu to add one."
    ),
    "zh-Hans": (
        "你好！我是 Bubu。我很想聊天，但还没有配置 OpenRouter API 密钥。"
        "请在托盘菜单中选择「偏好设置」进行设置。"
    ),
    "zh-Hant": (
        "你好！我是 Bubu。我很想聊天，但還沒有設定 OpenRouter API 金鑰。"
        "請在系統匣選單中選擇「偏好設定」進行設定。"
    ),
}

CHAT_NO_API_KEY_SEND_LABELS: dict[str, str] = {
    "en": "Add your OpenRouter API key from Preference in the tray menu to chat.",
    "zh-Hans": "请从托盘菜单的「偏好设置」设置 OpenRouter API 密钥后再聊天。",
    "zh-Hant": "請從系統匣選單的「偏好設定」設定 OpenRouter API 金鑰後再聊天。",
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

CHAT_STATUS_TYPING_LABELS: dict[str, str] = {
    "en": "Typing...",
    "zh-Hans": "正在回复...",
    "zh-Hant": "正在回覆...",
}

CHAT_TYPING_PHRASE_LABELS: dict[str, str] = {
    "en": "Bubu is thinking",
    "zh-Hans": "Bubu 正在思考",
    "zh-Hant": "Bubu 正在思考",
}

CHAT_TYPING_INTERVAL_MS: int = 380

TRAY_NO_API_KEY_TITLE_LABELS: dict[str, str] = {
    "en": "py-shimeji — chat unavailable",
    "zh-Hans": "py-shimeji — 无法聊天",
    "zh-Hant": "py-shimeji — 無法聊天",
}

TRAY_NO_API_KEY_MESSAGE_LABELS: dict[str, str] = {
    "en": (
        "Open Preference in the tray menu to add an OpenRouter API key and chat with Bubu."
    ),
    "zh-Hans": "在托盘菜单中打开「偏好设置」以添加 OpenRouter API 密钥并与 Bubu 聊天。",
    "zh-Hant": "在系統匣選單中開啟「偏好設定」以新增 OpenRouter API 金鑰並與 Bubu 聊天。",
}

TRAY_API_KEY_SAVED_MESSAGE_LABELS: dict[str, str] = {
    "en": "OpenRouter API key saved. You can chat with Bubu now.",
    "zh-Hans": "OpenRouter API 密钥已保存。现在可以与 Bubu 聊天了。",
    "zh-Hant": "OpenRouter API 金鑰已儲存。現在可以與 Bubu 聊天了。",
}

TRAY_API_KEY_CLEARED_MESSAGE_LABELS: dict[str, str] = {
    "en": "OpenRouter API key removed. Chat is disabled.",
    "zh-Hans": "OpenRouter API 密钥已移除。聊天功能已禁用。",
    "zh-Hant": "OpenRouter API 金鑰已移除。聊天功能已停用。",
}

TRAY_PREFERENCES_SAVED_MESSAGE_LABELS: dict[str, str] = {
    "en": "Preferences saved.",
    "zh-Hans": "偏好设置已保存。",
    "zh-Hant": "偏好設定已儲存。",
}

TRAY_HIDE_PET_LABELS: dict[str, str] = {
    "en": "Hide Pet {index}",
    "zh-Hans": "隐藏宠物 {index}",
    "zh-Hant": "隱藏寵物 {index}",
}

TRAY_SHOW_PET_LABELS: dict[str, str] = {
    "en": "Show Pet {index}",
    "zh-Hans": "显示宠物 {index}",
    "zh-Hant": "顯示寵物 {index}",
}

TRAY_CHANGE_SPRITES_LABELS: dict[str, str] = {
    "en": "Change Pet {index} sprites...",
    "zh-Hans": "更改宠物 {index} 形象...",
    "zh-Hant": "更改寵物 {index} 形象...",
}

TRAY_SELECT_SPRITES_TITLE_LABELS: dict[str, str] = {
    "en": "Select sprite folder for Pet {index}",
    "zh-Hans": "选择宠物 {index} 的形象文件夹",
    "zh-Hant": "選擇寵物 {index} 的形象資料夾",
}

SPRITE_PICKER_TITLE_LABELS: dict[str, str] = {
    "en": "Pet {index} appearance",
    "zh-Hans": "宠物 {index} 形象",
    "zh-Hant": "寵物 {index} 形象",
}

SPRITE_PICKER_INTRO_LABELS: dict[str, str] = {
    "en": "Choose a sprite set, or browse for a custom folder.",
    "zh-Hans": "选择一套形象，或浏览自定义文件夹。",
    "zh-Hant": "選擇一套形象，或瀏覽自訂資料夾。",
}

SPRITE_PICKER_FILES_HEADING_LABELS: dict[str, str] = {
    "en": "PNG files in the folder",
    "zh-Hans": "文件夹中的 PNG 文件",
    "zh-Hant": "資料夾中的 PNG 檔案",
}

SPRITE_STATE_LABELS: dict[str, dict[str, str]] = {
    "idle": {"en": "Idle", "zh-Hans": "待机", "zh-Hant": "待機"},
    "walk": {"en": "Walk", "zh-Hans": "行走", "zh-Hant": "行走"},
    "sit": {"en": "Sit", "zh-Hans": "坐下", "zh-Hant": "坐下"},
    "fall": {"en": "Fall", "zh-Hans": "下落", "zh-Hant": "下落"},
    "drag": {"en": "Drag", "zh-Hans": "拖拽", "zh-Hant": "拖曳"},
}

SPRITE_PICKER_OPTIONAL_LABELS: dict[str, str] = {
    "en": "optional",
    "zh-Hans": "可选",
    "zh-Hant": "選用",
}

SPRITE_PICKER_BROWSE_LABELS: dict[str, str] = {
    "en": "Browse folder…",
    "zh-Hans": "浏览文件夹…",
    "zh-Hant": "瀏覽資料夾…",
}

SPRITE_PICKER_APPLY_LABELS: dict[str, str] = {
    "en": "Apply",
    "zh-Hans": "应用",
    "zh-Hant": "套用",
}

SPRITE_PICKER_CANCEL_LABELS: dict[str, str] = {
    "en": "Cancel",
    "zh-Hans": "取消",
    "zh-Hant": "取消",
}

SPRITE_PICKER_INVALID_FOLDER_LABELS: dict[str, str] = {
    "en": "That folder does not contain any supported sprite PNGs.",
    "zh-Hans": "该文件夹不包含任何支持的形象 PNG 文件。",
    "zh-Hant": "該資料夾不包含任何支援的形象 PNG 檔案。",
}

TRAY_CHAT_LABELS: dict[str, str] = {
    "en": "Chat with bubu",
    "zh-Hans": "与 bubu 聊天",
    "zh-Hant": "與 bubu 聊天",
}

TRAY_PREFERENCE_LABELS: dict[str, str] = {
    "en": "Preference",
    "zh-Hans": "偏好设置",
    "zh-Hant": "偏好設定",
}

TRAY_BEHAVIOR_LABELS: dict[str, str] = {
    "en": "Pet behavior...",
    "zh-Hans": "宠物行为...",
    "zh-Hant": "寵物行為...",
}

TRAY_BEHAVIOR_SAVED_MESSAGE_LABELS: dict[str, str] = {
    "en": "Pet behavior settings saved.",
    "zh-Hans": "宠物行为设置已保存。",
    "zh-Hant": "寵物行為設定已儲存。",
}

BEHAVIOR_DIALOG_TITLE_LABELS: dict[str, str] = {
    "en": "Pet behavior",
    "zh-Hans": "宠物行为",
    "zh-Hant": "寵物行為",
}

BEHAVIOR_DIALOG_INTRO_LABELS: dict[str, str] = {
    "en": "Adjust how pets move and interact on your desktop.",
    "zh-Hans": "调整宠物在桌面上的移动与互动方式。",
    "zh-Hant": "調整寵物在桌面上的移動與互動方式。",
}

BEHAVIOR_SPEED_LABELS: dict[str, str] = {
    "en": "Movement speed: {value}%",
    "zh-Hans": "移动速度：{value}%",
    "zh-Hant": "移動速度：{value}%",
}

BEHAVIOR_SPEED_HINT_LABELS: dict[str, str] = {
    "en": "Walk, climb, and fall speed.",
    "zh-Hans": "行走、攀爬与下落速度。",
    "zh-Hant": "行走、攀爬與下落速度。",
}

BEHAVIOR_CHASE_LABELS: dict[str, str] = {
    "en": "Cursor chase chance: {value}%",
    "zh-Hans": "追逐鼠标概率：{value}%",
    "zh-Hant": "追逐滑鼠機率：{value}%",
}

BEHAVIOR_CHASE_HINT_LABELS: dict[str, str] = {
    "en": "How often idle pets walk toward your cursor.",
    "zh-Hans": "待机宠物走向鼠标的频率。",
    "zh-Hant": "待機寵物走向滑鼠的頻率。",
}

BEHAVIOR_PET_COUNT_LABELS: dict[str, str] = {
    "en": "Number of pets",
    "zh-Hans": "宠物数量",
    "zh-Hant": "寵物數量",
}

BEHAVIOR_PET_COUNT_HINT_LABELS: dict[str, str] = {
    "en": "Between {min} and {max}. Extra pets appear immediately.",
    "zh-Hans": "范围 {min}–{max}。额外的宠物会立即出现。",
    "zh-Hant": "範圍 {min}–{max}。額外的寵物會立即出現。",
}

BEHAVIOR_AMBIENT_LABELS: dict[str, str] = {
    "en": "Ambient speech bubbles",
    "zh-Hans": "随机说话气泡",
    "zh-Hant": "隨機說話氣泡",
}

BEHAVIOR_AMBIENT_HINT_LABELS: dict[str, str] = {
    "en": "Pets occasionally say short phrases while wandering.",
    "zh-Hans": "宠物闲逛时会偶尔说些简短的话。",
    "zh-Hant": "寵物閒逛時會偶爾說些簡短的話。",
}

BEHAVIOR_SAVE_LABELS: dict[str, str] = {
    "en": "Save",
    "zh-Hans": "保存",
    "zh-Hant": "儲存",
}

BEHAVIOR_CANCEL_LABELS: dict[str, str] = {
    "en": "Cancel",
    "zh-Hans": "取消",
    "zh-Hant": "取消",
}

TRAY_CLICK_THROUGH_LABELS: dict[str, str] = {
    "en": "Click-through (pass mouse clicks)",
    "zh-Hans": "穿透点击（鼠标穿透）",
    "zh-Hant": "穿透點擊（滑鼠穿透）",
}

TRAY_CLICK_THROUGH_TOOLTIP_LABELS: dict[str, str] = {
    "en": "When enabled, pets ignore the mouse. Disable to drag them.",
    "zh-Hans": "启用后宠物会忽略鼠标。关闭后可拖动。",
    "zh-Hant": "啟用後寵物會忽略滑鼠。關閉後可拖動。",
}

TRAY_PAUSE_PETS_LABELS: dict[str, str] = {
    "en": "Pause pets (reduce motion)",
    "zh-Hans": "暂停宠物（减少动画）",
    "zh-Hant": "暫停寵物（減少動畫）",
}

TRAY_PAUSE_PETS_TOOLTIP_LABELS: dict[str, str] = {
    "en": (
        "Pets stay still for meetings or accessibility. "
        "Disable click-through to drag them while paused."
    ),
    "zh-Hans": "宠物保持静止，适合开会或无障碍使用。关闭穿透点击后可拖动它们。",
    "zh-Hant": "寵物保持靜止，適合開會或無障礙使用。關閉穿透點擊後可拖動牠們。",
}

TRAY_QUIT_LABELS: dict[str, str] = {
    "en": "Quit",
    "zh-Hans": "退出",
    "zh-Hant": "退出",
}

PREFERENCES_TITLE_LABELS: dict[str, str] = {
    "en": "Preferences",
    "zh-Hans": "偏好设置",
    "zh-Hant": "偏好設定",
}

PREFERENCES_OPENROUTER_HEADING_LABELS: dict[str, str] = {
    "en": "OpenRouter configuration",
    "zh-Hans": "OpenRouter 配置",
    "zh-Hant": "OpenRouter 設定",
}

PREFERENCES_OPENROUTER_INTRO_LABELS: dict[str, str] = {
    "en": (
        "Bubu uses OpenRouter for chat. Your key is stored locally in "
        "<b>.env</b> and is only sent to OpenRouter when you message Bubu."
    ),
    "zh-Hans": (
        "Bubu 使用 OpenRouter 进行聊天。你的密钥保存在本地 "
        "<b>.env</b> 文件中，仅在你向 Bubu 发送消息时才会发送给 OpenRouter。"
    ),
    "zh-Hant": (
        "Bubu 使用 OpenRouter 進行聊天。你的金鑰保存在本機 "
        "<b>.env</b> 檔案中，僅在你向 Bubu 傳送訊息時才會傳送給 OpenRouter。"
    ),
}

PREFERENCES_API_KEY_LABELS: dict[str, str] = {
    "en": "API key",
    "zh-Hans": "API 密钥",
    "zh-Hant": "API 金鑰",
}

PREFERENCES_KEY_HINT_LABELS: dict[str, str] = {
    "en": "Leave blank and click Save to keep the current key.",
    "zh-Hans": "留空并点击保存以保留当前密钥。",
    "zh-Hant": "留空並點擊儲存以保留目前金鑰。",
}

PREFERENCES_KEY_LINK_LABELS: dict[str, str] = {
    "en": '<a href="https://openrouter.ai/keys">Get a key at openrouter.ai/keys</a>',
    "zh-Hans": '<a href="https://openrouter.ai/keys">在 openrouter.ai/keys 获取密钥</a>',
    "zh-Hant": '<a href="https://openrouter.ai/keys">在 openrouter.ai/keys 取得金鑰</a>',
}

PREFERENCES_LANGUAGE_HEADING_LABELS: dict[str, str] = {
    "en": "Language",
    "zh-Hans": "语言",
    "zh-Hant": "語言",
}

PREFERENCES_LANGUAGE_HINT_LABELS: dict[str, str] = {
    "en": "Choose the language Bubu uses when replying in chat.",
    "zh-Hans": "选择 Bubu 在聊天中回复时使用的语言。",
    "zh-Hant": "選擇 Bubu 在聊天中回覆時使用的語言。",
}

PREFERENCES_CLEAR_KEY_LABELS: dict[str, str] = {
    "en": "Clear key",
    "zh-Hans": "清除密钥",
    "zh-Hant": "清除金鑰",
}

PREFERENCES_SAVE_LABELS: dict[str, str] = {
    "en": "Save",
    "zh-Hans": "保存",
    "zh-Hant": "儲存",
}

PREFERENCES_CANCEL_LABELS: dict[str, str] = {
    "en": "Cancel",
    "zh-Hans": "取消",
    "zh-Hant": "取消",
}

PREFERENCES_STATUS_CONFIGURED_LABELS: dict[str, str] = {
    "en": "Status: configured ({masked})",
    "zh-Hans": "状态：已配置（{masked}）",
    "zh-Hant": "狀態：已設定（{masked}）",
}

PREFERENCES_STATUS_NOT_CONFIGURED_LABELS: dict[str, str] = {
    "en": "Status: not configured",
    "zh-Hans": "状态：未配置",
    "zh-Hant": "狀態：未設定",
}

PREFERENCES_STATUS_ENTER_KEY_LABELS: dict[str, str] = {
    "en": "Status: enter a key before saving.",
    "zh-Hans": "状态：保存前请输入密钥。",
    "zh-Hant": "狀態：儲存前請輸入金鑰。",
}

UI_LANGUAGE_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "en": "English",
        "zh-Hans": "Simplified Chinese",
        "zh-Hant": "Traditional Chinese",
    },
    "zh-Hans": {
        "en": "英语",
        "zh-Hans": "简体中文",
        "zh-Hant": "繁体中文",
    },
    "zh-Hant": {
        "en": "英語",
        "zh-Hans": "簡體中文",
        "zh-Hant": "繁體中文",
    },
}

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


def localized(labels: dict[str, str], language: str | None = None) -> str:
    """Return a UI string for the given or current language."""
    lang = language if language in _valid_chat_language_ids() else get_chat_language()
    return labels.get(lang, labels["en"])


def language_option_labels(ui_language: str | None = None) -> list[tuple[str, str]]:
    """Return (language_id, display_label) pairs for language pickers."""
    ui_lang = ui_language if ui_language in _valid_chat_language_ids() else get_chat_language()
    names = UI_LANGUAGE_LABELS.get(ui_lang, UI_LANGUAGE_LABELS["en"])
    return [(lang_id, names.get(lang_id, fallback)) for lang_id, fallback in CHAT_LANGUAGES]


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

# User-tunable behavior defaults (overridden via tray settings / .app_settings.json).
BEHAVIOR_SPEED_PERCENT_DEFAULT: int = 100
BEHAVIOR_SPEED_PERCENT_MIN: int = 50
BEHAVIOR_SPEED_PERCENT_MAX: int = 200

BEHAVIOR_CURSOR_CHASE_DEFAULT: float = CURSOR_CHASE_CHANCE
BEHAVIOR_CURSOR_CHASE_MIN: float = 0.0
BEHAVIOR_CURSOR_CHASE_MAX: float = 1.0

AMBIENT_SPEECH_ENABLED_DEFAULT: bool = True
AMBIENT_SPEECH_INTERVAL_MIN_MS: int = 45_000
AMBIENT_SPEECH_INTERVAL_MAX_MS: int = 120_000
AMBIENT_SPEECH_EVENT_CHANCE: float = 0.35

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

    Uses a persisted path when saved and still valid, otherwise the default
    ``assets/sprites/pet_N/`` folder (with legacy fallback for pet 1).
    """
    saved = get_saved_pet_sprites_dir(pet_index)
    if saved is not None:
        return saved
    return _default_pet_sprites_dir(pet_index)


def _default_pet_sprites_dir(pet_index: int) -> Path:
    """
    Default sprite folder for a pet without persisted overrides.

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


def iter_sprite_file_entries() -> list[tuple[str, str, bool]]:
    """Return ``(state, filename, optional)`` for every expected sprite PNG."""
    entries: list[tuple[str, str, bool]] = []
    for state, filenames in SPRITE_FILES.items():
        optional = state in SPRITE_OPTIONAL_STATES
        for filename in filenames:
            entries.append((state, filename, optional))
    return entries


def sprite_state_label(state: str, language: str | None = None) -> str:
    """Localized label for a sprite animation state."""
    labels = SPRITE_STATE_LABELS.get(state, {})
    if language and language in labels:
        return labels[language]
    return labels.get("en", state)


def discover_sprite_packs(extra_dirs: Path | list[Path] | None = None) -> list[Path]:
    """
    Return sprite folders that contain at least one valid PNG.

    Scans built-in ``assets/sprites/`` (including one level of subfolders) and
    any extra paths supplied by the caller (e.g. the pet's current folder).
    """
    found: dict[str, Path] = {}

    def add_if_valid(path: Path) -> None:
        resolved = path.resolve()
        if pet_has_sprites(resolved):
            found[str(resolved)] = resolved

    if SPRITES_ROOT.is_dir():
        add_if_valid(SPRITES_ROOT)
        for child in sorted(SPRITES_ROOT.iterdir()):
            if not child.is_dir():
                continue
            add_if_valid(child)
            for sub in sorted(child.iterdir()):
                if sub.is_dir():
                    add_if_valid(sub)

    extras = extra_dirs if isinstance(extra_dirs, list) else ([extra_dirs] if extra_dirs else [])
    for path in extras:
        if path is not None:
            add_if_valid(path)

    return sorted(found.values(), key=_sprite_pack_sort_key)


def sprite_pack_display_name(path: Path, language: str | None = None) -> str:
    """Human-readable label for a sprite folder in the picker grid."""
    _ = language
    try:
        rel = path.resolve().relative_to(SPRITES_ROOT.resolve())
        return str(rel).replace("\\", " / ")
    except ValueError:
        return path.name or str(path)


def _sprite_pack_sort_key(path: Path) -> tuple[int, str]:
    try:
        rel = path.resolve().relative_to(SPRITES_ROOT.resolve())
        return (0, str(rel).lower())
    except ValueError:
        return (1, str(path).lower())


# ---------------------------------------------------------------------------
# App settings (pet sprites, visibility)
# ---------------------------------------------------------------------------

_APP_SETTINGS_PATH: Path = PROJECT_ROOT / ".app_settings.json"


def _load_app_settings() -> dict:
    if _APP_SETTINGS_PATH.is_file():
        try:
            data = json.loads(_APP_SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return {}


def _save_app_settings(data: dict) -> None:
    _APP_SETTINGS_PATH.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )


def _pet_settings_entry(pet_index: int) -> dict:
    pets = _load_app_settings().get("pets", {})
    if not isinstance(pets, dict):
        return {}
    entry = pets.get(str(pet_index), {})
    return entry if isinstance(entry, dict) else {}


def get_saved_pet_sprites_dir(pet_index: int) -> Path | None:
    """Return a persisted sprite folder when it still exists on disk."""
    raw = _pet_settings_entry(pet_index).get("sprites_dir")
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    return path if path.is_dir() else None


def set_saved_pet_sprites_dir(pet_index: int, sprites_dir: Path) -> None:
    """Persist the sprite folder for a pet."""
    data = _load_app_settings()
    pets = data.setdefault("pets", {})
    if not isinstance(pets, dict):
        pets = {}
        data["pets"] = pets
    entry = pets.setdefault(str(pet_index), {})
    if not isinstance(entry, dict):
        entry = {}
        pets[str(pet_index)] = entry
    entry["sprites_dir"] = str(sprites_dir.resolve())
    _save_app_settings(data)


def get_saved_pet_visible(pet_index: int) -> bool | None:
    """Return persisted visibility, or None to use the startup default."""
    entry = _pet_settings_entry(pet_index)
    if "visible" not in entry:
        return None
    return bool(entry["visible"])


def set_saved_pet_visible(pet_index: int, visible: bool) -> None:
    """Persist whether a pet should be shown on startup."""
    data = _load_app_settings()
    pets = data.setdefault("pets", {})
    if not isinstance(pets, dict):
        pets = {}
        data["pets"] = pets
    entry = pets.setdefault(str(pet_index), {})
    if not isinstance(entry, dict):
        entry = {}
        pets[str(pet_index)] = entry
    entry["visible"] = visible
    _save_app_settings(data)


def get_saved_pets_paused() -> bool:
    """Return whether pets should start in reduce-motion pause mode."""
    return bool(_load_app_settings().get("pets_paused", False))


def set_saved_pets_paused(paused: bool) -> None:
    """Persist reduce-motion pause mode for the next launch."""
    data = _load_app_settings()
    data["pets_paused"] = paused
    _save_app_settings(data)


def _behavior_settings() -> dict:
    behavior = _load_app_settings().get("behavior", {})
    return behavior if isinstance(behavior, dict) else {}


def _clamp_int(value: object, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def _clamp_float(value: object, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def get_speed_percent() -> int:
    """Return the user movement speed as a percentage of the base speed."""
    raw = _behavior_settings().get("speed_percent", BEHAVIOR_SPEED_PERCENT_DEFAULT)
    return _clamp_int(
        raw,
        BEHAVIOR_SPEED_PERCENT_MIN,
        BEHAVIOR_SPEED_PERCENT_MAX,
        BEHAVIOR_SPEED_PERCENT_DEFAULT,
    )


def get_cursor_chase_chance() -> float:
    """Return the probability (0–1) that an idle pet starts chasing the cursor."""
    raw = _behavior_settings().get("cursor_chase_chance", BEHAVIOR_CURSOR_CHASE_DEFAULT)
    return _clamp_float(
        raw,
        BEHAVIOR_CURSOR_CHASE_MIN,
        BEHAVIOR_CURSOR_CHASE_MAX,
        BEHAVIOR_CURSOR_CHASE_DEFAULT,
    )


def get_saved_pet_count() -> int:
    """Return how many pets to spawn (persisted, or MAX_PETS by default)."""
    raw = _behavior_settings().get("pet_count", MAX_PETS)
    return _clamp_int(raw, MIN_PET_COUNT, MAX_PET_COUNT, MAX_PETS)


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
    data = _load_app_settings()
    data["behavior"] = {
        "speed_percent": _clamp_int(
            speed_percent,
            BEHAVIOR_SPEED_PERCENT_MIN,
            BEHAVIOR_SPEED_PERCENT_MAX,
            BEHAVIOR_SPEED_PERCENT_DEFAULT,
        ),
        "cursor_chase_chance": _clamp_float(
            cursor_chase_chance,
            BEHAVIOR_CURSOR_CHASE_MIN,
            BEHAVIOR_CURSOR_CHASE_MAX,
            BEHAVIOR_CURSOR_CHASE_DEFAULT,
        ),
        "pet_count": _clamp_int(pet_count, MIN_PET_COUNT, MAX_PET_COUNT, MAX_PETS),
        "ambient_speech_enabled": bool(ambient_speech_enabled),
    }
    _save_app_settings(data)


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


# ---------------------------------------------------------------------------
# On-pet speech bubbles (short chat replies)
# ---------------------------------------------------------------------------

SPEECH_BUBBLE_MAX_CHARS: int = 120
SPEECH_BUBBLE_DURATION_MS: int = 7_000
SPEECH_BUBBLE_GAP_PX: int = 6
SPEECH_BUBBLE_MAX_WIDTH: int = 210
SPEECH_BUBBLE_PADDING_PX: int = 10


def format_speech_bubble_text(text: str) -> str | None:
    """Return bubble text for short replies, or None when too long for a bubble."""
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    if len(collapsed) > SPEECH_BUBBLE_MAX_CHARS:
        return None
    return collapsed
