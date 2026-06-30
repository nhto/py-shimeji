"""Core gameplay constants (dimensions, timers, physics)."""

from __future__ import annotations

PET_WIDTH: int = 64
PET_HEIGHT: int = 64

SPRITE_SCALE_PERCENT_DEFAULT: int = 100
SPRITE_SCALE_PERCENT_MIN: int = 50
SPRITE_SCALE_PERCENT_MAX: int = 200


def effective_pet_size(scale_percent: int) -> tuple[int, int]:
    """Return widget width/height for a sprite scale percentage."""
    width = max(1, round(PET_WIDTH * scale_percent / 100))
    height = max(1, round(PET_HEIGHT * scale_percent / 100))
    return width, height

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

MOVEMENT_SPEED_SCALE: float = 0.8

WALK_SPEED_PX: int = 3
CLIMB_SPEED_PX: int = 4
GRAVITY_PX: int = 8
_BASE_MOVE_TICK_MS: int = 16
FALL_TICK_MS: int = max(1, round(_BASE_MOVE_TICK_MS / MOVEMENT_SPEED_SCALE))
SURFACE_REFRESH_MS: int = 400

MIN_WINDOW_WIDTH: int = 120
MIN_WINDOW_HEIGHT: int = 80

MAX_PETS: int = 2
MIN_PET_COUNT: int = 1
MAX_PET_COUNT: int = 4

PEER_INTERACTION_Y_TOLERANCE_PX: int = 16
PEER_NUDGE_PX: int = 5
PEER_SIT_ON_BUMP_CHANCE: float = 0.2

CURSOR_CHASE_CHANCE: float = 0.12
CURSOR_CHASE_MIN_MS: int = 3_000
CURSOR_CHASE_MAX_MS: int = 10_000
CURSOR_SIT_DISTANCE_PX: int = 28
CURSOR_STILL_MS: int = 700
CURSOR_STILL_TOLERANCE_PX: int = 10
CURSOR_Y_TOLERANCE_PX: int = 56

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

FALLBACK_BODY_COLOR: str = "#FF6B9D"
FALLBACK_OUTLINE_COLOR: str = "#2D1B2E"
FALLBACK_EYE_COLOR: str = "#FFFFFF"
FALLBACK_PUPIL_COLOR: str = "#1A1A2E"

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

SPEECH_BUBBLE_MAX_CHARS: int = 220
SPEECH_BUBBLE_DURATION_MS: int = 7_000
SPEECH_BUBBLE_GAP_PX: int = 6
SPEECH_BUBBLE_MAX_WIDTH: int = 260
SPEECH_BUBBLE_PADDING_PX: int = 10
MEETING_SNOOZE_MINUTES: int = 5
MAIL_BODY_PREVIEW_MAX_CHARS: int = 60
MEETING_LOCATION_MAX_CHARS: int = 70


def format_speech_bubble_text(text: str) -> str | None:
    """Return bubble text for short replies, or None when too long for a bubble."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    collapsed = "\n".join(lines)
    if len(collapsed) > SPEECH_BUBBLE_MAX_CHARS:
        return None
    return collapsed
