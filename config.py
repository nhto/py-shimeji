"""Application-wide constants and paths for the Shimeji desktop pet.

This module re-exports the split settings and i18n packages so existing
``from config import …`` statements keep working.
"""

from __future__ import annotations

from i18n.locale import language_option_labels, localized, localized_with_pet, sprite_state_label
from i18n.strings import *  # noqa: F403
from settings.behavior import (
    AMBIENT_BUMP_PHRASES,
    AMBIENT_LAND_PHRASES,
    AMBIENT_SPEECH_PHRASES,
    get_ambient_phrase,
    get_ambient_speech_enabled,
    get_cursor_chase_chance,
    get_effective_climb_speed_px,
    get_effective_gravity_px,
    get_effective_walk_speed_px,
    get_move_tick_ms,
    get_saved_pet_count,
    get_speed_percent,
    set_behavior_settings,
)
from settings.chat import (
    CHAT_MODELS,
    CHAT_MODEL_SUPPORTS_IMAGES,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    build_chat_system_prompt,
    chat_model_supports_images,
    get_chat_language,
    get_chat_model,
    get_openrouter_api_key,
    get_pet_name,
    has_openrouter_api_key,
    set_chat_language,
    set_chat_model,
    set_openrouter_api_key,
    set_pet_name,
)
from settings.core import *  # noqa: F403
from settings.hotkeys import HOTKEY_ACTIONS, get_hotkey_binding, set_hotkey_binding
from settings.outlook import *  # noqa: F403
from settings.paths import ASSETS_DIR, BUNDLE_ROOT, ENV_FILE_PATH, PROJECT_ROOT, SPRITES_ROOT
from settings.paths import SPRITE_FILES, SPRITE_OPTIONAL_STATES
from settings.update import get_skipped_version, get_update_check_enabled, set_skipped_version, set_update_check_enabled
from settings.persistence import (
    get_saved_pet_visible,
    get_saved_pet_sprites_dir,
    get_saved_pets_paused,
    set_saved_pet_sprites_dir,
    set_saved_pet_visible,
    set_saved_pets_paused,
)
from settings.sprites import (
    discover_sprite_packs,
    effective_pet_size,
    get_pet_sprites_dir,
    get_sprite_scale_percent,
    iter_sprite_file_entries,
    pet_has_sprites,
    set_saved_pet_sprite_scale_percent,
    set_saved_pet_sprites_dir,
    sprite_pack_display_name,
)
from settings.core import format_speech_bubble_text  # noqa: F401 — re-export
from version import GITHUB_REPO, __version__

__all__ = [name for name in globals() if not name.startswith("_")]
