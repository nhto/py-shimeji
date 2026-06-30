"""Language selection and localized string lookup."""

from __future__ import annotations

from i18n.strings import CHAT_LANGUAGES, UI_LANGUAGE_LABELS
from settings.chat import get_chat_language, valid_chat_language_ids


def localized(labels: dict[str, str], language: str | None = None) -> str:
    """Return a UI string for the given or current language."""
    lang = language if language in valid_chat_language_ids() else get_chat_language()
    return labels.get(lang, labels["en"])


def language_option_labels(ui_language: str | None = None) -> list[tuple[str, str]]:
    """Return (language_id, display_label) pairs for language pickers."""
    ui_lang = ui_language if ui_language in valid_chat_language_ids() else get_chat_language()
    names = UI_LANGUAGE_LABELS.get(ui_lang, UI_LANGUAGE_LABELS["en"])
    return [(lang_id, names.get(lang_id, fallback)) for lang_id, fallback in CHAT_LANGUAGES]


def sprite_state_label(state: str, language: str | None = None) -> str:
    """Localized label for a sprite animation state."""
    from i18n.strings import SPRITE_STATE_LABELS

    labels = SPRITE_STATE_LABELS.get(state, {})
    if language and language in labels:
        return labels[language]
    return labels.get("en", state)
