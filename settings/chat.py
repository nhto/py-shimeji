"""OpenRouter API key and chat model/language persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path

from i18n.strings import CHAT_DEFAULT_LANGUAGE, CHAT_LANGUAGE_INSTRUCTIONS, CHAT_LANGUAGES
from settings.core import CHAT_SYSTEM_PROMPT_TEMPLATE, DEFAULT_PET_NAME
from settings.paths import ENV_FILE_PATH, PROJECT_ROOT

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


def _normalize_pet_name(name: str) -> str | None:
    stripped = " ".join(name.split())
    if not stripped:
        return None
    return stripped[:_PET_NAME_MAX_LEN]


def get_pet_name() -> str:
    """Return the persisted pet name, or the default when unset."""
    name = _load_chat_settings().get("pet_name", "")
    if isinstance(name, str):
        normalized = _normalize_pet_name(name)
        if normalized:
            return normalized
    return DEFAULT_PET_NAME


def set_pet_name(name: str) -> str:
    """Persist the user's chosen pet name and return the normalized value."""
    normalized = _normalize_pet_name(name) or DEFAULT_PET_NAME
    _save_chat_settings(pet_name=normalized)
    return normalized


def build_chat_system_prompt(language: str | None = None) -> str:
    """Build the system prompt with a language-specific reply instruction."""
    lang = language if language in valid_chat_language_ids() else get_chat_language()
    instruction = CHAT_LANGUAGE_INSTRUCTIONS.get(lang, CHAT_LANGUAGE_INSTRUCTIONS["en"])
    prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(name=get_pet_name())
    return f"{prompt} {instruction}"
