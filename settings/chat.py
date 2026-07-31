"""OpenRouter API key and chat model/language persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path

from i18n.strings import CHAT_DEFAULT_LANGUAGE, CHAT_LANGUAGE_INSTRUCTIONS, CHAT_LANGUAGES
from settings.core import (
    CHAT_SYSTEM_PROMPT_TEMPLATE,
    DEFAULT_PERSONALITY_LINE,
    DEFAULT_PET_NAME,
)
from settings.paths import ENV_FILE_PATH, PROJECT_ROOT
from settings.persistence import (
    get_saved_pet_display_name,
    get_saved_pet_personality,
    set_saved_pet_display_name,
    set_saved_pet_personality,
)

OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"

_OPENROUTER_KEY_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "",
        "your-openrouter-api-key-here",
    }
)

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
_PET_NAME_MAX_LEN: int = 24
_PET_PERSONALITY_MAX_LEN: int = 500


def persist_env_var(name: str, value: str) -> None:
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


def get_openrouter_api_key() -> str:
    """Return the current OpenRouter API key from the process environment."""
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


OPENROUTER_API_KEY: str = get_openrouter_api_key()


def has_openrouter_api_key() -> bool:
    """True when a non-placeholder OpenRouter API key is configured."""
    key = get_openrouter_api_key()
    return key.lower() not in {p.lower() for p in _OPENROUTER_KEY_PLACEHOLDERS}


def set_openrouter_api_key(key: str) -> None:
    """Persist an OpenRouter API key to .env and apply it for this session."""
    normalized = key.strip()
    os.environ["OPENROUTER_API_KEY"] = normalized
    persist_env_var("OPENROUTER_API_KEY", normalized)


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


def valid_chat_language_ids() -> set[str]:
    return {lang_id for lang_id, _ in CHAT_LANGUAGES}


def valid_chat_model_ids() -> set[str]:
    return {model_id for model_id, _ in CHAT_MODELS}


def get_chat_model() -> str:
    """Return the persisted chat model, or a sensible default."""
    model = _load_chat_settings().get("model", "")
    if isinstance(model, str) and model in valid_chat_model_ids():
        return model

    env_model = os.environ.get("OPENROUTER_MODEL", "")
    if env_model in valid_chat_model_ids():
        return env_model

    return CHAT_MODELS[0][0]


def set_chat_model(model_id: str) -> None:
    """Persist the user's chat model choice."""
    if model_id not in valid_chat_model_ids():
        return
    _save_chat_settings(model=model_id)


def chat_model_supports_images(model_id: str) -> bool:
    """Return whether the model accepts image input via OpenRouter."""
    return model_id in CHAT_MODEL_SUPPORTS_IMAGES


def get_chat_language() -> str:
    """Return the persisted reply language, or Traditional Chinese by default."""
    language = _load_chat_settings().get("language", "")
    if isinstance(language, str) and language in valid_chat_language_ids():
        return language
    return CHAT_DEFAULT_LANGUAGE


def set_chat_language(language_id: str) -> None:
    """Persist the user's preferred reply language."""
    if language_id not in valid_chat_language_ids():
        return
    _save_chat_settings(language=language_id)


def get_chat_context_include_active_window() -> bool:
    """True when chat may include the foreground window title."""
    return bool(_load_chat_settings().get("context_active_window", False))


def set_chat_context_include_active_window(enabled: bool) -> None:
    """Persist opt-in for sharing the active window title with chat."""
    _save_chat_settings(context_active_window=bool(enabled))


def get_chat_context_include_clipboard() -> bool:
    """True when chat may include a short clipboard text preview."""
    return bool(_load_chat_settings().get("context_clipboard", False))


def set_chat_context_include_clipboard(enabled: bool) -> None:
    """Persist opt-in for sharing clipboard text with chat."""
    _save_chat_settings(context_clipboard=bool(enabled))


def _normalize_pet_name(name: str) -> str | None:
    stripped = " ".join(name.split())
    if not stripped:
        return None
    return stripped[:_PET_NAME_MAX_LEN]


def _normalize_pet_personality(personality: str) -> str | None:
    stripped = " ".join(personality.split())
    if not stripped:
        return None
    return stripped[:_PET_PERSONALITY_MAX_LEN]


def _legacy_global_pet_name() -> str | None:
    name = _load_chat_settings().get("pet_name", "")
    if isinstance(name, str):
        return _normalize_pet_name(name)
    return None


def _codex_metadata_for_pet(pet_index: int):
    from codex_pet import load_codex_pet_metadata
    from settings.sprites import get_pet_sprites_dir

    return load_codex_pet_metadata(get_pet_sprites_dir(pet_index))


def default_pet_name(pet_index: int = 0) -> str:
    """Return the default display name before any user override."""
    codex = _codex_metadata_for_pet(pet_index)
    if codex is not None and codex.display_name:
        return codex.display_name[:_PET_NAME_MAX_LEN]
    if pet_index == 0:
        legacy = _legacy_global_pet_name()
        if legacy:
            return legacy
        return DEFAULT_PET_NAME
    return f"{DEFAULT_PET_NAME} {pet_index + 1}"


def get_pet_name(pet_index: int = 0) -> str:
    """Return the display name for a pet, using saved or default values."""
    saved = get_saved_pet_display_name(pet_index)
    if saved:
        return saved[:_PET_NAME_MAX_LEN]
    return default_pet_name(pet_index)


def set_pet_name(name: str, pet_index: int = 0) -> str:
    """Persist a pet's display name and return the effective name."""
    normalized = _normalize_pet_name(name)
    set_saved_pet_display_name(pet_index, normalized)
    effective = normalized or default_pet_name(pet_index)
    if pet_index == 0:
        _save_chat_settings(pet_name=effective)
    return effective


def default_pet_personality_line(pet_index: int = 0) -> str:
    """Return the default personality instruction for a pet's system prompt."""
    codex = _codex_metadata_for_pet(pet_index)
    if codex is not None and codex.description:
        description = codex.description.strip()
        if description and not description.endswith("."):
            description += "."
        return f"{description} "
    return DEFAULT_PERSONALITY_LINE


def get_pet_personality(pet_index: int = 0) -> str | None:
    """Return a saved custom personality line, or None for pack/default."""
    return get_saved_pet_personality(pet_index)


def set_pet_personality(personality: str, pet_index: int = 0) -> str | None:
    """Persist a pet's custom personality line (empty clears the override)."""
    normalized = _normalize_pet_personality(personality)
    set_saved_pet_personality(pet_index, normalized)
    return normalized


def pet_personality_line(pet_index: int = 0) -> str:
    """Return the effective personality line used in the chat system prompt."""
    custom = get_saved_pet_personality(pet_index)
    if custom:
        line = custom.strip()
        if line and not line.endswith("."):
            line += "."
        return f"{line} "
    return default_pet_personality_line(pet_index)


def build_chat_system_prompt(language: str | None = None, pet_index: int = 0) -> str:
    """Build the system prompt with a language-specific reply instruction."""
    from chat_context import build_live_chat_context

    lang = language if language in valid_chat_language_ids() else get_chat_language()
    instruction = CHAT_LANGUAGE_INSTRUCTIONS.get(lang, CHAT_LANGUAGE_INSTRUCTIONS["en"])
    prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
        name=get_pet_name(pet_index),
        personality_line=pet_personality_line(pet_index),
    )
    parts = [f"{prompt} {instruction}"]
    live_context = build_live_chat_context()
    if live_context:
        parts.append(live_context)
    return "\n\n".join(parts)
