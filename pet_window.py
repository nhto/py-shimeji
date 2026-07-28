"""Frameless transparent pet window with rendering, input, and physics."""

from __future__ import annotations

import sys
import random
from collections import deque
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PyQt6.QtGui import (
    QBitmap,
    QBrush,
    QColor,
    QContextMenuEvent,
    QCursor,
    QGuiApplication,
    QHideEvent,
    QImage,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QScreen,
    QShowEvent,
)
from PyQt6.QtWidgets import QWidget

from config import (
    ANIMATION_INTERVAL_MS,
    BEHAVIOR_INTERVAL_MS,
    CURSOR_CHASE_MAX_MS,
    CURSOR_CHASE_MIN_MS,
    CURSOR_SIT_DISTANCE_PX,
    CURSOR_STILL_MS,
    CURSOR_STILL_TOLERANCE_PX,
    CURSOR_Y_TOLERANCE_PX,
    PEER_INTERACTION_Y_TOLERANCE_PX,
    PEER_NUDGE_PX,
    PEER_SIT_ON_BUMP_CHANCE,
    PET_FALLBACK_PALETTES,
    SPRITE_FILES,
    TOP_PERCH_MARGIN_PX,
    get_ambient_phrase,
    get_ambient_speech_enabled,
    get_cursor_chase_chance,
    get_effective_climb_speed_px,
    get_effective_gravity_px,
    get_effective_walk_speed_px,
    get_move_tick_ms,
    get_pet_sprites_dir,
    get_sprite_scale_percent,
    effective_pet_size,
    set_saved_pet_sprite_scale_percent,
    set_saved_pet_sprites_dir,
    AMBIENT_SPEECH_EVENT_CHANCE,
    AMBIENT_SPEECH_INTERVAL_MAX_MS,
    AMBIENT_SPEECH_INTERVAL_MIN_MS,
    DRAG_THRESHOLD_PX,
    POKE_ANIMATION_MS,
    POKE_SIT_DURATION_MS,
)
from settings.core import format_speech_bubble_text
from speech_bubble import SpeechBubbleWindow
from states import PetState, PetStateMachine
from surfaces import (
    HorizontalLedge,
    SharedSurfaceCoordinator,
    SurfaceTracker,
    VerticalLedge,
    WindowRect,
)


def _is_background_pixel(color: QColor, threshold: int = 200) -> bool:
    """Heuristic for opaque white/gray export backgrounds."""
    return (
        color.alpha() > 0
        and color.red() >= threshold
        and color.green() >= threshold
        and color.blue() >= threshold
    )


def _key_out_background(image: QImage, threshold: int = 200) -> QImage:
    """
    Remove edge-connected light pixels.

    Many "transparent" PNG exports keep a solid white/gray backdrop with a
    fully opaque alpha channel; flood-filling from the image border fixes that.
    """
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    width, height = image.width(), image.height()
    if width == 0 or height == 0:
        return image

    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))

        color = image.pixelColor(x, y)
        if not _is_background_pixel(color, threshold):
            continue

        image.setPixelColor(x, y, QColor(color.red(), color.green(), color.blue(), 0))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height:
                queue.append((nx, ny))

    return image


def _has_transparent_border(image: QImage, *, alpha_threshold: int = 128) -> bool:
    """True when any image border pixel is already transparent."""
    width, height = image.width(), image.height()
    if width == 0 or height == 0:
        return False

    def transparent(x: int, y: int) -> bool:
        return image.pixelColor(x, y).alpha() < alpha_threshold

    for x in range(width):
        if transparent(x, 0) or transparent(x, height - 1):
            return True
    for y in range(height):
        if transparent(0, y) or transparent(width - 1, y):
            return True
    return False


def _prepare_sprite(path: Path, width: int, height: int) -> QPixmap | None:
    """Load, scale, de-background, and center a sprite frame."""
    image = QImage(str(path))
    if image.isNull():
        return None

    scale_mode = (
        Qt.TransformationMode.FastTransformation
        if image.width() > width or image.height() > height
        else Qt.TransformationMode.SmoothTransformation
    )
    scaled = image.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        scale_mode,
    )
    if not _has_transparent_border(scaled):
        scaled = _key_out_background(scaled)

    canvas = QImage(width, height, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.drawImage(
        (width - scaled.width()) // 2,
        (height - scaled.height()) // 2,
        scaled,
    )
    painter.end()

    pixmap = QPixmap.fromImage(canvas)
    return pixmap if not pixmap.isNull() else None


class SpriteCache:
    """Loads sprite frames from disk; missing files are represented as None."""

    def __init__(self, assets_dir: Path, *, width: int, height: int) -> None:
        self._assets_dir = assets_dir
        self._width = width
        self._height = height
        self._cache: dict[str, list[QPixmap | None]] = {}
        self._load_all()

    def _load_all(self) -> None:
        from shimeji_pack import resolve_sprite_frame_paths

        frame_paths = resolve_sprite_frame_paths(self._assets_dir)
        for group, filenames in SPRITE_FILES.items():
            paths = frame_paths.get(group, [])
            frames: list[QPixmap | None] = []
            for index, _name in enumerate(filenames):
                path = paths[index] if index < len(paths) else None
                frames.append(
                    _prepare_sprite(path, self._width, self._height)
                    if path is not None and path.is_file()
                    else None
                )
            self._cache[group] = frames

    def reload(
        self,
        assets_dir: Path | None = None,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Reload sprite frames from disk (optionally from a new folder or size)."""
        if assets_dir is not None:
            self._assets_dir = assets_dir
        if width is not None:
            self._width = width
        if height is not None:
            self._height = height
        self._cache.clear()
        self._load_all()

    @property
    def has_sprites(self) -> bool:
        """True when at least one sprite frame loaded successfully."""
        return any(
            frame is not None
            for frames in self._cache.values()
            for frame in frames
        )

    def frames_for_state(self, state: PetState) -> list[QPixmap | None]:
        mapping = {
            PetState.IDLE: "idle",
            PetState.SIT: "sit",
            PetState.WALKING: "walk",
            PetState.CHASING_CURSOR: "walk",
            PetState.CLIMBING: "walk",
            PetState.FALLING: "fall",
            PetState.DRAGGED: "drag",
        }
        key = mapping.get(state, "idle")
        frames = self._cache.get(key, self._cache["idle"])
        if state == PetState.SIT and not any(frame is not None for frame in frames):
            return self._cache["idle"]
        return frames

    def has_any_sprites(self, state: PetState) -> bool:
        return any(frame is not None for frame in self.frames_for_state(state))


class PetWindow(QWidget):
    """
    Transparent, always-on-top desktop pet widget.

    Handles FSM-driven movement, drag-and-drop, gravity, sprite animation,
    and vector fallback rendering when assets are unavailable.
    """

    def __init__(
        self,
        pet_index: int = 0,
        pet_count: int = 1,
        exclude_hwnds: set[int] | None = None,
        sprites_dir: Path | None = None,
        surface_coordinator: SharedSurfaceCoordinator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet_index = pet_index
        self._pet_count = max(1, pet_count)
        self._exclude_hwnds = exclude_hwnds if exclude_hwnds is not None else set()
        self._surface_coordinator = surface_coordinator
        self._sprites_dir = sprites_dir or get_pet_sprites_dir(pet_index)
        self._start_fraction = (pet_index + 1) / (self._pet_count + 1)
        self._sprite_scale_percent = get_sprite_scale_percent(pet_index)
        self._pet_width, self._pet_height = effective_pet_size(self._sprite_scale_percent)
        palette = PET_FALLBACK_PALETTES[pet_index % len(PET_FALLBACK_PALETTES)]
        self._fallback_body = palette["body"]
        self._fallback_outline = palette["outline"]
        self._fallback_eye = palette["eye"]
        self._fallback_pupil = palette["pupil"]

        self._sprites = SpriteCache(
            self._sprites_dir,
            width=self._pet_width,
            height=self._pet_height,
        )
        self._frame_index: int = 0
        self._drag_offset = QPoint(0, 0)
        self._is_dragging: bool = False
        self._drag_pending: bool = False
        self._press_global_pos: QPoint | None = None
        self._poke_anim_active: bool = False
        self._poke_anim_token: int = 0
        self._play_area: QRect = QRect()
        self._surfaces = SurfaceTracker()
        self._surfaces.set_pet_dimensions(self._pet_width, self._pet_height)
        self._active_ledge: HorizontalLedge | None = None
        self._fall_exclude_ledge_id: str | None = None
        self._climb_ledge: VerticalLedge | None = None
        self._climb_direction: int = -1  # -1 = up, 1 = down
        self._click_through: bool = False
        self._motion_paused: bool = False
        self._context_menu_handler: Callable[[QPoint, PetWindow], None] | None = None
        self._right_click_handled: bool = False
        self._peer_pets: list[PetWindow] = []
        self._menu_hold: bool = False
        self._chat_hold: bool = False
        self._cursor_sit_active: bool = False
        self._cursor_still_ms: int = 0
        self._last_cursor_pos: QPoint | None = None
        self._cursor_chase_ms_left: int = 0
        self._idle_chase_accum_ms: int = 0
        self._speech_bubble: SpeechBubbleWindow | None = None
        self._was_falling: bool = False

        self._fsm = PetStateMachine(self._on_fsm_state_changed, parent=self)

        self._setup_window()
        self._setup_timers()
        self._place_on_floor()

    @property
    def pet_index(self) -> int:
        return self._pet_index

    @property
    def sprites_dir(self) -> Path:
        return self._sprites_dir

    @property
    def has_sprites(self) -> bool:
        return self._sprites.has_sprites

    @property
    def click_through(self) -> bool:
        return self._click_through

    @property
    def motion_paused(self) -> bool:
        return self._motion_paused

    def set_context_menu_handler(
        self, handler: Callable[[QPoint, PetWindow], None] | None
    ) -> None:
        self._context_menu_handler = handler

    def set_click_through(self, enabled: bool) -> None:
        """Pass mouse clicks to windows below when enabled."""
        self._click_through = enabled
        self._apply_click_through()

    def set_motion_paused(self, enabled: bool) -> None:
        """Freeze autonomous movement and animation (accessibility / meetings)."""
        if enabled == self._motion_paused:
            return
        self._motion_paused = enabled
        if enabled:
            self._enter_motion_pause()
        else:
            self._leave_motion_pause()

    @property
    def sprite_scale_percent(self) -> int:
        return self._sprite_scale_percent

    def reload_sprites(
        self,
        sprites_dir: Path,
        *,
        sprite_scale_percent: int | None = None,
    ) -> None:
        """Load a new PNG set for this pet and refresh the window."""
        if sprite_scale_percent is not None:
            from settings.core import (
                SPRITE_SCALE_PERCENT_DEFAULT,
                SPRITE_SCALE_PERCENT_MAX,
                SPRITE_SCALE_PERCENT_MIN,
            )
            from settings.persistence import clamp_int

            self._sprite_scale_percent = clamp_int(
                sprite_scale_percent,
                SPRITE_SCALE_PERCENT_MIN,
                SPRITE_SCALE_PERCENT_MAX,
                SPRITE_SCALE_PERCENT_DEFAULT,
            )
            self._update_pet_dimensions()
            set_saved_pet_sprite_scale_percent(self._pet_index, self._sprite_scale_percent)
        self._sprites_dir = sprites_dir
        self._sprites.reload(
            sprites_dir,
            width=self._pet_width,
            height=self._pet_height,
        )
        self._frame_index = 0
        set_saved_pet_sprites_dir(self._pet_index, sprites_dir)
        self._refresh_play_area()
        if self._surface_coordinator is not None:
            self._surface_coordinator.rebuild_pet(self)
        else:
            self._surfaces.refresh(self._play_area, self._exclude_hwnds)
        pos = self.pos()
        self.move(*self._clamp_position(pos.x(), pos.y()))
        self.update()

    def apply_sprite_scale(self, scale_percent: int) -> None:
        """Resize the pet widget and reload sprites at the new scale."""
        from settings.core import (
            SPRITE_SCALE_PERCENT_DEFAULT,
            SPRITE_SCALE_PERCENT_MAX,
            SPRITE_SCALE_PERCENT_MIN,
        )
        from settings.persistence import clamp_int

        scale_percent = clamp_int(
            scale_percent,
            SPRITE_SCALE_PERCENT_MIN,
            SPRITE_SCALE_PERCENT_MAX,
            SPRITE_SCALE_PERCENT_DEFAULT,
        )
        if scale_percent == self._sprite_scale_percent:
            return
        self._sprite_scale_percent = scale_percent
        self._update_pet_dimensions()
        self._sprites.reload(width=self._pet_width, height=self._pet_height)
        set_saved_pet_sprite_scale_percent(self._pet_index, self._sprite_scale_percent)
        self._frame_index = 0
        self._refresh_play_area()
        if self._surface_coordinator is not None:
            self._surface_coordinator.rebuild_pet(self)
        else:
            self._surfaces.refresh(self._play_area, self._exclude_hwnds)
        pos = self.pos()
        self.move(*self._clamp_position(pos.x(), pos.y()))
        self.update()

    def _update_pet_dimensions(self) -> None:
        self._pet_width, self._pet_height = effective_pet_size(self._sprite_scale_percent)
        self.setFixedSize(self._pet_width, self._pet_height)
        self._surfaces.set_pet_dimensions(self._pet_width, self._pet_height)

    def show_speech_bubble(
        self,
        text: str,
        *,
        actions: list[tuple[str, Callable[[], None]]] | None = None,
    ) -> None:
        """Show a short-lived speech bubble above the pet."""
        bubble_text = format_speech_bubble_text(text)
        if bubble_text is None or not self.isVisible():
            return
        if self._speech_bubble is None:
            self._speech_bubble = SpeechBubbleWindow(self)
        self._speech_bubble.show_text(bubble_text, actions=actions)

    def _reposition_speech_bubble(self) -> None:
        if self._speech_bubble is not None and self._speech_bubble.isVisible():
            self._speech_bubble.reposition()

    def _hide_speech_bubble(self) -> None:
        if self._speech_bubble is not None:
            self._speech_bubble.hide()

    def move(self, *args) -> None:  # noqa: ANN002
        super().move(*args)
        self._reposition_speech_bubble()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        self._hide_speech_bubble()
        super().hideEvent(event)

    def set_peer_pets(self, peers: list[PetWindow]) -> None:
        """Register other pets for overlap detection and nudging."""
        self._peer_pets = peers

    def set_total_pet_count(self, total: int) -> None:
        """Update spacing metadata when pets are added or removed."""
        self._pet_count = max(1, total)

    def apply_behavior_settings(self) -> None:
        """Apply movement speed and ambient-speech settings from config."""
        interval = get_move_tick_ms()
        self._fall_timer.setInterval(interval)
        self._move_timer.setInterval(interval)
        if get_ambient_speech_enabled():
            self._schedule_ambient_speech()
        else:
            self._ambient_timer.stop()

    def try_ambient_speech(self, event: str | None = None) -> None:
        """Show a short ambient phrase when appropriate."""
        if not get_ambient_speech_enabled():
            return
        if not self.isVisible() or self._motion_paused or self._menu_hold or self._chat_hold:
            return
        if self._is_dragging or self._fsm.state in (
            PetState.DRAGGED,
            PetState.FALLING,
            PetState.CLIMBING,
        ):
            return
        if self._speech_bubble is not None and self._speech_bubble.isVisible():
            return
        if event is None:
            if self._fsm.state not in (PetState.IDLE, PetState.SIT, PetState.WALKING):
                return
        elif random.random() >= AMBIENT_SPEECH_EVENT_CHANCE:
            return

        phrase = get_ambient_phrase(event)
        if phrase is not None:
            self.show_speech_bubble(phrase)

    def handle_display_changed(self) -> None:
        """Re-clamp position and refresh surfaces after monitor or taskbar changes."""
        self._refresh_play_area()
        if not self.isVisible():
            return

        pos = self.pos()
        clamped_x, clamped_y = self._clamp_position(pos.x(), pos.y())
        if clamped_x != pos.x() or clamped_y != pos.y():
            self.move(clamped_x, clamped_y)

        if self._surface_coordinator is not None:
            self._surface_coordinator.rebuild_pet(self)
        else:
            self._surfaces.refresh(self._play_area, self._exclude_hwnds)
        if self._is_dragging:
            return
        if self._motion_paused:
            self._snap_to_nearest_support()
            return
        if self._fsm.state in (PetState.FALLING, PetState.CLIMBING):
            return
        self._sync_support()

    def begin_menu_hold(self) -> None:
        """Sit still and pause behavior while the context menu is open."""
        if self._fsm.state in (PetState.DRAGGED, PetState.FALLING):
            return

        self._menu_hold = True
        self._enter_hold()

    def end_menu_hold(self) -> None:
        """Resume behavior after the context menu closes."""
        if not self._menu_hold:
            return
        self._menu_hold = False
        self._leave_hold_if_idle()

    def begin_chat_hold(self) -> None:
        """Sit still and pause behavior while the chat window is open."""
        if self._fsm.state in (PetState.DRAGGED, PetState.FALLING):
            return

        self._chat_hold = True
        self._enter_hold()

    def end_chat_hold(self) -> None:
        """Resume behavior after the chat window closes."""
        if not self._chat_hold:
            return
        self._chat_hold = False
        self._leave_hold_if_idle()

    def _enter_hold(self) -> None:
        self._cursor_sit_active = False
        self._cursor_still_ms = 0
        self._cursor_chase_ms_left = 0
        self._climb_ledge = None
        if self._surface_coordinator is not None:
            self._surface_coordinator.rebuild_pet(self)
        else:
            self._refresh_surfaces()
        ledge = self._surfaces.find_ledge_at(self.pos().x(), self.pos().y())
        if ledge is not None:
            self._active_ledge = ledge
            self.move(self._clamp_x(self.pos().x()), self._clamp_y(ledge.stand_y))
        self._fsm.pause()
        self._fsm.begin_sit()
        self._frame_index = 0
        self._anim_timer.stop()
        self.update()

    def _leave_hold_if_idle(self) -> None:
        if self._menu_hold or self._chat_hold or self._motion_paused:
            return
        self._fsm.resume()
        self._anim_timer.start()
        self._move_timer.start()
        self.update()

    def _enter_motion_pause(self) -> None:
        """Stop movement and sit still; dragging remains available."""
        self._hide_speech_bubble()
        self._fall_timer.stop()
        self._anim_timer.stop()
        self._move_timer.stop()

        if self._is_dragging:
            return

        self._cursor_sit_active = False
        self._cursor_still_ms = 0
        self._cursor_chase_ms_left = 0
        self._climb_ledge = None
        self._idle_chase_accum_ms = 0
        self._snap_to_nearest_support()
        self._fsm.pause()
        self._fsm.begin_sit()
        self._frame_index = 0
        self.update()

    def _leave_motion_pause(self) -> None:
        if self._menu_hold or self._chat_hold:
            return
        self._fsm.resume()
        self._anim_timer.start()
        self._move_timer.start()
        self.update()

    def _snap_to_nearest_support(self) -> None:
        """Move the pet onto the current ledge or the screen floor."""
        self._refresh_play_area()
        if self._surface_coordinator is not None:
            self._surface_coordinator.rebuild_pet(self)
        else:
            self._surfaces.refresh(self._play_area, self._exclude_hwnds)
        pos = self.pos()
        ledge = self._surfaces.find_ledge_at(pos.x(), pos.y())
        if ledge is None:
            floor = self._surfaces.floor_ledge(self._play_area)
            self._active_ledge = floor
            self.move(self._clamp_x(pos.x()), self._clamp_y(floor.stand_y))
            return
        self._active_ledge = ledge
        self.move(self._clamp_x(pos.x()), self._clamp_y(ledge.stand_y))

    def _finish_drag_while_paused(self) -> None:
        """Land after a manual drag while reduce-motion pause is active."""
        self._snap_to_nearest_support()
        self._fsm.pause()
        self._fsm.begin_sit()
        self._frame_index = 0
        self._fall_timer.stop()
        self._anim_timer.stop()
        self._move_timer.stop()
        self.update()

    def apply_peer_nudge(self, dx: int) -> None:
        """Shift horizontally when bumped by another pet on the same ledge."""
        if self._fsm.state in (PetState.DRAGGED, PetState.FALLING, PetState.CLIMBING):
            return

        pos = self.pos()
        ledge = self._active_ledge or self._surfaces.find_ledge_at(pos.x(), pos.y())
        if ledge is None:
            return

        new_x = self._clamp_x(pos.x() + dx)
        new_x = max(ledge.left, min(new_x, ledge.max_pet_x()))
        self.move(new_x, self._clamp_y(ledge.stand_y))

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setFixedSize(self._pet_width, self._pet_height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

    def _setup_timers(self) -> None:
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(ANIMATION_INTERVAL_MS)
        self._anim_timer.timeout.connect(self._on_animation_tick)
        self._anim_timer.start()

        self._fall_timer = QTimer(self)
        self._fall_timer.setInterval(get_move_tick_ms())
        self._fall_timer.timeout.connect(self._on_fall_tick)

        self._move_timer = QTimer(self)
        self._move_timer.setInterval(get_move_tick_ms())
        self._move_timer.timeout.connect(self._on_movement_tick)
        self._move_timer.start()

        if self._surface_coordinator is None:
            from settings.core import SURFACE_REFRESH_MS

            self._surface_timer = QTimer(self)
            self._surface_timer.setInterval(SURFACE_REFRESH_MS)
            self._surface_timer.timeout.connect(self._refresh_surfaces)
            self._surface_timer.start()

        self._ambient_timer = QTimer(self)
        self._ambient_timer.setSingleShot(True)
        self._ambient_timer.timeout.connect(self._on_ambient_timer)
        self._schedule_ambient_speech()

    def _schedule_ambient_speech(self) -> None:
        if not get_ambient_speech_enabled():
            return
        delay = random.randint(
            AMBIENT_SPEECH_INTERVAL_MIN_MS,
            AMBIENT_SPEECH_INTERVAL_MAX_MS,
        )
        self._ambient_timer.start(delay)

    def _on_ambient_timer(self) -> None:
        self.try_ambient_speech()
        self._schedule_ambient_speech()

    def _place_on_floor(self) -> None:
        self._refresh_play_area()
        x = self._play_area.left() + int(
            (self._play_area.width() - self._pet_width) * self._start_fraction
        )
        x = self._clamp_x(x)
        y = self._play_area.bottom() - self._pet_height + 1
        self.move(x, y)

    def _refresh_play_area(self) -> None:
        """Use available geometry so the pet rests above the taskbar/dock."""
        self._refresh_play_area_at(None)

    def _refresh_play_area_at(self, global_point: QPoint | None) -> None:
        """Pick the play area for *global_point* or the pet's current position."""
        if (
            global_point is None
            and self._fsm.state in (PetState.FALLING, PetState.CLIMBING)
            and self._play_area.isValid()
        ):
            # Keep the current monitor while airborne so corner probes do not
            # hop to an adjacent display and teleport the pet off-screen.
            return

        screen: QScreen | None = None
        if global_point is not None:
            screen = QGuiApplication.screenAt(global_point)

        if screen is None:
            probe = self._pet_screen_probe()
            screen = QGuiApplication.screenAt(probe)
            if screen is None:
                frame = self.frameGeometry()
                screen = QGuiApplication.screenAt(frame.topLeft())
            if screen is None:
                screen = self._nearest_screen(probe)
            if screen is None:
                screen = QGuiApplication.primaryScreen()

        if screen is None:
            self._play_area = QRect(0, 0, 1920, 1080)
            return
        self._play_area = screen.availableGeometry()

    def _pet_screen_probe(self) -> QPoint:
        """Return a screen point that stays on the pet's current display."""
        frame = self.frameGeometry()
        return QPoint(
            frame.left() + self._pet_width // 2,
            frame.top() + self._pet_height - 1,
        )

    def _nearest_screen(self, point: QPoint) -> QScreen | None:
        """Return the screen whose bounds are closest to *point*."""
        screens = QGuiApplication.screens()
        if not screens:
            return None
        best: QScreen | None = None
        best_dist = float("inf")
        for screen in screens:
            geo = screen.availableGeometry()
            dx = 0
            if point.x() < geo.left():
                dx = geo.left() - point.x()
            elif point.x() > geo.right():
                dx = point.x() - geo.right()
            dy = 0
            if point.y() < geo.top():
                dy = geo.top() - point.y()
            elif point.y() > geo.bottom():
                dy = point.y() - geo.bottom()
            dist = dx * dx + dy * dy
            if dist < best_dist:
                best_dist = dist
                best = screen
        return best

    def _min_pet_x(self) -> int:
        return self._play_area.left()

    def _max_pet_x(self) -> int:
        return self._play_area.right() - self._pet_width + 1

    def _clamp_x(self, x: int) -> int:
        return max(self._min_pet_x(), min(x, self._max_pet_x()))

    def _min_pet_y(self) -> int:
        return self._play_area.top()

    def _max_pet_y(self) -> int:
        return self._play_area.bottom() - self._pet_height + 1

    def _clamp_y(self, y: int) -> int:
        return max(self._min_pet_y(), min(y, self._max_pet_y()))

    def _clamp_y_during_fall(self, y: int) -> int:
        """Allow falling in from above the play area; only cap the bottom edge."""
        return min(y, self._max_pet_y())

    def _clamp_position(self, x: int, y: int) -> tuple[int, int]:
        return self._clamp_x(x), self._clamp_y(y)

    def _clamp_x_on_ledge(self, x: int, ledge: HorizontalLedge) -> int:
        """Clamp *x* to both the screen and a horizontal ledge."""
        return self._clamp_x(max(ledge.left, min(x, ledge.max_pet_x())))

    def rebuild_surfaces_from_cache(self, windows: list[WindowRect]) -> None:
        """Rebuild ledges from a shared window scan and sync pet support."""
        self._refresh_play_area()
        self._surfaces.rebuild_ledges(self._play_area, windows)
        self._after_surface_rebuild()

    def _refresh_surfaces(self) -> None:
        if self._surface_coordinator is not None:
            self._surface_coordinator.refresh()
            return
        self._refresh_play_area()
        self._surfaces.refresh(self._play_area, self._exclude_hwnds)
        self._after_surface_rebuild()

    def _rebuild_surfaces_from_cache(self) -> None:
        if self._surface_coordinator is not None:
            self._surface_coordinator.rebuild_pet(self)
            return
        self._refresh_surfaces()

    def _after_surface_rebuild(self) -> None:
        if not self._is_dragging and self._fsm.state not in (
            PetState.CLIMBING,
            PetState.FALLING,
        ):
            pos = self.pos()
            clamped_x, clamped_y = self._clamp_position(pos.x(), pos.y())
            if clamped_x != pos.x() or clamped_y != pos.y():
                self.move(clamped_x, clamped_y)
        if not self._is_dragging:
            self._sync_support()

    def _sync_support(self) -> None:
        """Keep ledge state in sync; fall when the pet has no surface beneath it."""
        if self._fsm.state in (
            PetState.FALLING,
            PetState.DRAGGED,
            PetState.CLIMBING,
        ):
            return

        pos = self.pos()
        ledge = self._surfaces.find_ledge_at(pos.x(), pos.y())
        if ledge is not None:
            top_zone = self._play_area.top() + TOP_PERCH_MARGIN_PX
            if ledge.ledge_id != "screen" and ledge.stand_y < top_zone:
                self._active_ledge = None
                self._start_fall()
                return
            self._active_ledge = ledge
            if self._fsm.state in (PetState.SIT, PetState.IDLE):
                stand_y = self._clamp_y(ledge.stand_y)
                if pos.y() != stand_y:
                    self.move(self._clamp_x(pos.x()), stand_y)
                return
            return

        self._active_ledge = None
        self._start_fall()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._exclude_hwnds.add(int(self.winId()))
        self._refresh_surfaces()
        self._active_ledge = self._surfaces.floor_ledge(self._play_area)
        self._apply_click_through()

    def _apply_click_through(self) -> None:
        """Make the window ignore mouse hits when click-through is on."""
        if sys.platform == "win32":
            import ctypes

            hwnd = int(self.winId())
            gwl_exstyle = -20
            ws_ex_transparent = 0x00000020
            style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
            if self._click_through:
                style |= ws_ex_transparent
            else:
                style &= ~ws_ex_transparent
            ctypes.windll.user32.SetWindowLongW(hwnd, gwl_exstyle, style)
        else:
            self.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                self._click_through,
            )

    # ------------------------------------------------------------------
    # State machine callbacks
    # ------------------------------------------------------------------

    def _on_fsm_state_changed(self, old: PetState, new: PetState) -> None:
        self._frame_index = 0
        if new == PetState.SIT and old != PetState.CHASING_CURSOR:
            self._cursor_sit_active = False
        if new != PetState.CHASING_CURSOR and old == PetState.CHASING_CURSOR:
            self._cursor_chase_ms_left = 0
        if new == PetState.FALLING:
            self._fall_timer.start()
        elif old == PetState.FALLING:
            self._fall_timer.stop()
        self.update()

    # ------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------

    def _on_animation_tick(self) -> None:
        if (
            self._motion_paused
            or self._menu_hold
            or self._chat_hold
            or self._fsm.state == PetState.DRAGGED
        ):
            return
        frames = self._sprites.frames_for_state(self._fsm.state)
        if frames:
            self._frame_index = (self._frame_index + 1) % len(frames)
        self.update()

    def _on_movement_tick(self) -> None:
        if (
            self._is_dragging
            or self._motion_paused
            or self._menu_hold
            or self._chat_hold
        ):
            return
        if self._fsm.state == PetState.WALKING:
            if not self._poke_anim_active:
                self._horizontal_walk_tick()
                self._handle_peer_interactions()
        elif self._fsm.state == PetState.CHASING_CURSOR:
            self._cursor_chase_tick()
            self._handle_peer_interactions()
        elif self._fsm.state == PetState.CLIMBING:
            self._climb_tick()
        elif self._fsm.state == PetState.IDLE:
            self._idle_chase_accum_ms += get_move_tick_ms()
            if self._idle_chase_accum_ms >= BEHAVIOR_INTERVAL_MS:
                self._idle_chase_accum_ms = 0
                self._maybe_start_cursor_chase()
        elif self._fsm.state == PetState.SIT and self._cursor_sit_active:
            self._monitor_cursor_sit()

    def _horizontal_walk_tick(self) -> None:
        self._move_on_ledge(self._fsm.direction, allow_climb=True)

    def _move_on_ledge(self, direction: int, *, allow_climb: bool) -> None:
        pos = self.pos()
        direction = self._fsm.direction
        new_x = pos.x() + get_effective_walk_speed_px() * direction
        pet_top = pos.y()
        pet_bottom = pos.y() + self._pet_height

        ledge = self._surfaces.find_ledge_at(pos.x(), pos.y())
        if ledge is None:
            self._start_fall()
            return
        self._active_ledge = ledge

        climb = self._surfaces.climb_candidate(
            pos.x(),
            pet_top,
            pet_bottom,
            direction,
            new_x,
            standing_on_hwnd=ledge.hwnd,
        )
        if climb is not None:
            if allow_climb:
                self._start_climb(climb, direction=-1)
            elif self._fsm.state == PetState.CHASING_CURSOR:
                self._end_cursor_chase()
            return

        pet_left_min = ledge.left
        pet_left_max = ledge.max_pet_x()

        if new_x < pet_left_min:
            if ledge.ledge_id != "screen" and direction < 0:
                vertical = self._surfaces.vertical_for_window(ledge.hwnd, "left")
                if vertical is not None:
                    if allow_climb:
                        self._start_climb(vertical, direction=1)
                    elif self._fsm.state == PetState.CHASING_CURSOR:
                        self._end_cursor_chase()
                    return
            if ledge.ledge_id != "screen":
                if not allow_climb:
                    self._end_cursor_chase()
                    return
                # Turn at window ledge ends; falling re-lands on the same perch
                # (find_landing_ledge matches the current surface on the first tick).
                new_x = pet_left_min
                self._fsm.set_direction(1)
                self._fsm.notify_boundary_hit()
            else:
                if not allow_climb:
                    self._end_cursor_chase()
                    return
                new_x = self._min_pet_x()
                self._fsm.set_direction(1)
                self._fsm.notify_boundary_hit()
        elif new_x > pet_left_max:
            if ledge.ledge_id != "screen" and direction > 0:
                vertical = self._surfaces.vertical_for_window(ledge.hwnd, "right")
                if vertical is not None:
                    if allow_climb:
                        self._start_climb(vertical, direction=1)
                    elif self._fsm.state == PetState.CHASING_CURSOR:
                        self._end_cursor_chase()
                    return
            if ledge.ledge_id != "screen":
                if not allow_climb:
                    self._end_cursor_chase()
                    return
                new_x = pet_left_max
                self._fsm.set_direction(-1)
                self._fsm.notify_boundary_hit()
            else:
                if not allow_climb:
                    self._end_cursor_chase()
                    return
                new_x = self._max_pet_x()
                self._fsm.set_direction(-1)
                self._fsm.notify_boundary_hit()

        new_x = self._clamp_x(new_x)
        self.move(new_x, self._clamp_y(ledge.stand_y))

    def _maybe_start_cursor_chase(self) -> None:
        if not self.isVisible() or random.random() >= get_cursor_chase_chance():
            return
        cursor = QCursor.pos()
        if not self._is_cursor_on_same_ledge(cursor):
            return
        pet_center_x = self.pos().x() + self._pet_width // 2
        if abs(cursor.x() - pet_center_x) <= CURSOR_SIT_DISTANCE_PX:
            return
        self._cursor_still_ms = 0
        self._last_cursor_pos = cursor
        self._cursor_chase_ms_left = random.randint(
            CURSOR_CHASE_MIN_MS,
            CURSOR_CHASE_MAX_MS,
        )
        self._fsm.begin_cursor_chase()

    def _cursor_chase_tick(self) -> None:
        self._cursor_chase_ms_left -= get_move_tick_ms()
        if self._cursor_chase_ms_left <= 0:
            self._end_cursor_chase()
            return

        cursor = QCursor.pos()
        if not self._is_cursor_on_same_ledge(cursor):
            self._end_cursor_chase()
            return

        pet_center_x = self.pos().x() + self._pet_width // 2
        dx = cursor.x() - pet_center_x
        self._track_cursor_stillness(cursor)

        if abs(dx) <= CURSOR_SIT_DISTANCE_PX and self._cursor_still_ms >= CURSOR_STILL_MS:
            self._cursor_sit_active = True
            self._fsm.begin_sit()
            return

        direction = 1 if dx > 0 else -1
        if dx == 0:
            direction = self._fsm.direction
        self._fsm.set_direction(direction)
        self._move_on_ledge(direction, allow_climb=False)

    def _monitor_cursor_sit(self) -> None:
        cursor = QCursor.pos()
        if not self._is_cursor_on_same_ledge(cursor):
            self._cursor_sit_active = False
            self._fsm.resume()
            self._fsm.force_state(PetState.IDLE)
            return

        self._track_cursor_stillness(cursor)
        if self._cursor_still_ms < CURSOR_STILL_MS:
            self._cursor_sit_active = False
            self._cursor_chase_ms_left = random.randint(
                CURSOR_CHASE_MIN_MS,
                CURSOR_CHASE_MAX_MS,
            )
            self._fsm.begin_cursor_chase()
            return

        self._fsm.extend_sit()

    def _end_cursor_chase(self) -> None:
        self._cursor_still_ms = 0
        self._last_cursor_pos = None
        self._cursor_chase_ms_left = 0
        self._fsm.force_state(PetState.IDLE)

    def _is_cursor_on_same_ledge(self, cursor: QPoint) -> bool:
        pos = self.pos()
        ledge = self._active_ledge or self._surfaces.find_ledge_at(pos.x(), pos.y())
        if ledge is None:
            return False

        pet_screen = self._nearest_screen(pos)
        cursor_screen = QGuiApplication.screenAt(cursor)
        if pet_screen is None or cursor_screen != pet_screen:
            return False

        feet_y = pos.y() + self._pet_height
        if abs(cursor.y() - feet_y) > CURSOR_Y_TOLERANCE_PX:
            return False

        cursor_x = cursor.x()
        return ledge.left <= cursor_x <= ledge.right

    def _track_cursor_stillness(self, cursor: QPoint) -> None:
        if self._last_cursor_pos is not None:
            moved_x = abs(cursor.x() - self._last_cursor_pos.x())
            moved_y = abs(cursor.y() - self._last_cursor_pos.y())
            if (
                moved_x <= CURSOR_STILL_TOLERANCE_PX
                and moved_y <= CURSOR_STILL_TOLERANCE_PX
            ):
                self._cursor_still_ms += get_move_tick_ms()
            else:
                self._cursor_still_ms = 0
        self._last_cursor_pos = cursor

    def _nudge_on_ledge(self, dx: int) -> None:
        """Move horizontally while staying on the current ledge."""
        pos = self.pos()
        ledge = self._active_ledge or self._surfaces.find_ledge_at(pos.x(), pos.y())
        if ledge is None:
            return

        new_x = self._clamp_x(pos.x() + dx)
        new_x = max(ledge.left, min(new_x, ledge.max_pet_x()))
        self.move(new_x, self._clamp_y(ledge.stand_y))

    def _handle_peer_interactions(self) -> None:
        """Bump, nudge, and turn around when walking into another pet."""
        if self._fsm.state not in (PetState.WALKING, PetState.CHASING_CURSOR) or not self.isVisible():
            return

        my_rect = self.frameGeometry()
        my_center_x = my_rect.center().x()
        my_y = self.pos().y()

        for peer in self._peer_pets:
            if not peer.isVisible():
                continue
            if peer._fsm.state in (
                PetState.DRAGGED,
                PetState.FALLING,
                PetState.CLIMBING,
            ):
                continue
            if abs(my_y - peer.pos().y()) > PEER_INTERACTION_Y_TOLERANCE_PX:
                continue

            peer_rect = peer.frameGeometry()
            if not my_rect.intersects(peer_rect):
                continue

            if (
                peer._fsm.state == PetState.WALKING
                and self._pet_index >= peer._pet_index
            ):
                continue
            if (
                peer._fsm.state == PetState.CHASING_CURSOR
                and self._fsm.state == PetState.CHASING_CURSOR
                and self._pet_index >= peer._pet_index
            ):
                continue

            peer_center_x = peer_rect.center().x()
            dx = my_center_x - peer_center_x
            if dx == 0:
                dx = self._fsm.direction
            nudge = PEER_NUDGE_PX if dx > 0 else -PEER_NUDGE_PX

            self._nudge_on_ledge(nudge)
            peer.apply_peer_nudge(-nudge)
            self.try_ambient_speech("bump")
            self._fsm.flip_direction()
            if self._fsm.state == PetState.CHASING_CURSOR:
                self._end_cursor_chase()
                return

            if peer._fsm.state == PetState.WALKING:
                peer._fsm.flip_direction()
            elif peer._fsm.state == PetState.CHASING_CURSOR:
                peer._end_cursor_chase()
            elif (
                peer._fsm.state in (PetState.IDLE, PetState.SIT)
                and random.random() < PEER_SIT_ON_BUMP_CHANCE
            ):
                self._fsm.begin_sit()

            break

    def _climb_tick(self) -> None:
        climb = self._climb_ledge
        if climb is None:
            self._start_fall()
            return

        pos = self.pos()
        pet_x = self._clamp_x(climb.pet_x())

        if self._climb_direction < 0:
            new_y = max(pos.y() - get_effective_climb_speed_px(), self._min_pet_y())
            climb_top = max(climb.top, self._play_area.top())
            if new_y <= climb_top - self._pet_height + 8:
                top_ledge = self._horizontal_ledge_for_hwnd(climb.hwnd)
                if top_ledge is None:
                    self._start_fall()
                    return
                self._active_ledge = top_ledge
                land_x = self._clamp_x(
                    max(
                        top_ledge.left,
                        min(pet_x, top_ledge.max_pet_x()),
                    )
                )
                self.move(land_x, self._clamp_y(top_ledge.stand_y))
                self._climb_ledge = None
                self._fsm.begin_walking()
            elif new_y <= self._min_pet_y():
                self.move(pet_x, self._min_pet_y())
                self._climb_ledge = None
                self._start_fall()
            else:
                self.move(pet_x, new_y)
            return

        new_y = pos.y() + get_effective_climb_speed_px()
        if new_y + self._pet_height >= climb.bottom - 4:
            floor = self._surfaces.floor_ledge(self._play_area)
            self._active_ledge = floor
            land_x = self._clamp_x(
                max(floor.left, min(pet_x, floor.max_pet_x()))
            )
            self.move(land_x, self._clamp_y(floor.stand_y))
            self._climb_ledge = None
            self._fsm.begin_walking()
        else:
            self.move(pet_x, new_y)

    def _horizontal_ledge_for_hwnd(self, hwnd: int) -> HorizontalLedge | None:
        for ledge in self._surfaces.horizontal_ledges():
            if ledge.hwnd == hwnd:
                return ledge
        return None

    def _start_climb(self, vertical: VerticalLedge, direction: int) -> None:
        self._climb_ledge = vertical
        self._climb_direction = -1 if direction < 0 else 1
        self.move(self._clamp_x(vertical.pet_x()), self.pos().y())
        self._fsm.force_state(PetState.CLIMBING)

    def _start_fall(self) -> None:
        self._was_falling = True
        self._fall_exclude_ledge_id = (
            self._active_ledge.ledge_id if self._active_ledge is not None else None
        )
        self._active_ledge = None
        self._climb_ledge = None
        self._fsm.force_state(PetState.FALLING)

    def _on_fall_tick(self) -> None:
        if self._motion_paused:
            self._enter_motion_pause()
            return
        if self._fsm.state != PetState.FALLING:
            return
        self._rebuild_surfaces_from_cache()
        pos = self.pos()
        new_y = pos.y() + get_effective_gravity_px()
        next_feet_y = new_y + self._pet_height - 1
        landing = self._surfaces.find_landing_ledge(
            pos.x(),
            pos.y(),
            next_feet_y,
            exclude_ledge_id=self._fall_exclude_ledge_id,
        )
        if landing is not None:
            land_x = self._clamp_x_on_ledge(pos.x(), landing)
            self.move(land_x, self._clamp_y(landing.stand_y))
            self._active_ledge = landing
            self._fall_exclude_ledge_id = None
            self._fall_timer.stop()
            self._fsm.resume()
            self._fsm.begin_walking()
            if self._was_falling:
                self._was_falling = False
                self.try_ambient_speech("land")
        elif next_feet_y >= self._play_area.bottom():
            floor = self._surfaces.floor_ledge(self._play_area)
            land_x = self._clamp_x_on_ledge(pos.x(), floor)
            self.move(land_x, self._clamp_y(floor.stand_y))
            self._active_ledge = floor
            self._fall_exclude_ledge_id = None
            self._fall_timer.stop()
            self._fsm.resume()
            self._fsm.begin_walking()
            if self._was_falling:
                self._was_falling = False
                self.try_ambient_speech("land")
        else:
            self.move(self._clamp_x(pos.x()), self._clamp_y_during_fall(new_y))
            if self._fall_exclude_ledge_id is not None:
                excluded = next(
                    (
                        ledge
                        for ledge in self._surfaces.horizontal_ledges()
                        if ledge.ledge_id == self._fall_exclude_ledge_id
                    ),
                    None,
                )
                if excluded is not None:
                    excluded_feet = excluded.stand_y + self._pet_height - 1
                    if next_feet_y > excluded_feet:
                        self._fall_exclude_ledge_id = None

    def _is_on_support(self) -> bool:
        self._rebuild_surfaces_from_cache()
        return self._surfaces.find_ledge_at(self.pos().x(), self.pos().y()) is not None

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        if self._click_through:
            return
        if self._right_click_handled:
            self._right_click_handled = False
            event.accept()
            return
        self._right_click_at(event.globalPos())
        event.accept()

    def _right_click_at(self, global_pos: QPoint) -> None:
        self.begin_menu_hold()
        if self._context_menu_handler is not None:
            self._context_menu_handler(global_pos, self)

    def poke(self) -> None:
        """React to a double-click poke: phrase, brief sit, or walk-in-place."""
        if self._click_through or self._is_dragging:
            return
        if self._menu_hold or self._chat_hold:
            return
        if self._fsm.state in (PetState.FALLING, PetState.CLIMBING, PetState.DRAGGED):
            return

        self._drag_pending = False
        self._press_global_pos = None
        self._cancel_poke_animation()

        roll = random.random()
        if roll < 1 / 3:
            self._poke_phrase()
        elif roll < 2 / 3:
            self._poke_sit()
        else:
            self._poke_brief_animation()

    def _poke_phrase(self) -> None:
        if self._speech_bubble is not None and self._speech_bubble.isVisible():
            return
        phrase = get_ambient_phrase("poke")
        if phrase is not None:
            self.show_speech_bubble(phrase)

    def _poke_sit(self) -> None:
        if self._menu_hold or self._chat_hold:
            return
        if self._fsm.state == PetState.SIT:
            self._fsm.extend_sit()
        elif not self._motion_paused:
            self._fsm.begin_sit_for(POKE_SIT_DURATION_MS)
        self._frame_index = 0
        self._anim_timer.start()
        self.update()

    def _poke_brief_animation(self) -> None:
        if self._motion_paused or self._menu_hold or self._chat_hold:
            self._poke_sit()
            return
        self._poke_anim_active = True
        self._frame_index = 0
        self._fsm.force_state(PetState.WALKING)
        self._anim_timer.start()
        self._poke_anim_token += 1
        token = self._poke_anim_token
        QTimer.singleShot(POKE_ANIMATION_MS, lambda: self._end_poke_animation(token))
        self.update()

    def _cancel_poke_animation(self) -> None:
        self._poke_anim_token += 1
        self._poke_anim_active = False

    def _end_poke_animation(self, token: int | None = None) -> None:
        if token is not None and token != self._poke_anim_token:
            return
        if not self._poke_anim_active:
            return
        self._poke_anim_active = False
        if self._fsm.state != PetState.WALKING:
            return
        if self._motion_paused or self._menu_hold or self._chat_hold:
            return
        if self._is_on_support():
            self._fsm.force_state(PetState.IDLE)
        else:
            self._active_ledge = None
            self._fsm.force_state(PetState.FALLING)
        self.update()

    def _start_drag_at(self, global_pos: QPoint) -> None:
        self._is_dragging = True
        self._drag_pending = False
        self._cursor_sit_active = False
        self._cursor_still_ms = 0
        self._cursor_chase_ms_left = 0
        self._cancel_poke_animation()
        self._drag_offset = global_pos - self.frameGeometry().topLeft()
        self._fsm.pause()
        self._fsm.force_state(PetState.DRAGGED)
        self._fall_timer.stop()
        self._climb_ledge = None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            if not self._click_through:
                self._right_click_at(event.globalPosition().toPoint())
                self._right_click_handled = True
            event.accept()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag_pending = True
        self._press_global_pos = event.globalPosition().toPoint()
        self._drag_offset = self._press_global_pos - self.frameGeometry().topLeft()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._click_through:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.poke()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_pending and not self._is_dragging:
            if self._press_global_pos is not None:
                pos = event.globalPosition().toPoint()
                if (
                    pos - self._press_global_pos
                ).manhattanLength() >= DRAG_THRESHOLD_PX:
                    self._start_drag_at(self._press_global_pos)
            if not self._is_dragging:
                return
        if not self._is_dragging:
            return
        new_pos = event.globalPosition().toPoint() - self._drag_offset
        self._refresh_play_area_at(new_pos)
        clamped_x, clamped_y = self._clamp_position(new_pos.x(), new_pos.y())
        self.move(clamped_x, clamped_y)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag_pending and not self._is_dragging:
            self._drag_pending = False
            self._press_global_pos = None
            event.accept()
            return
        if not self._is_dragging:
            return
        self._is_dragging = False
        self._drag_pending = False
        self._press_global_pos = None
        if self._motion_paused:
            self._finish_drag_while_paused()
            event.accept()
            return
        self._fsm.resume()
        if self._is_on_support():
            ledge = self._surfaces.find_ledge_at(self.pos().x(), self.pos().y())
            self._active_ledge = ledge
            self._fsm.begin_walking()
        else:
            self._active_ledge = None
            self._fsm.force_state(PetState.FALLING)
        event.accept()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        frames = self._sprites.frames_for_state(self._fsm.state)
        pixmap: QPixmap | None = None
        if frames:
            pixmap = frames[self._frame_index % len(frames)]

        if pixmap is not None and not pixmap.isNull():
            display_pixmap = self._pixmap_for_direction(pixmap)
            self._paint_sprite(painter, display_pixmap)
            self._apply_sprite_mask(display_pixmap)
        else:
            self._paint_fallback(painter)
            self.clearMask()

        painter.end()

    def _pixmap_for_direction(self, pixmap: QPixmap) -> QPixmap:
        """Mirror sprite frames when facing left so paint and mask stay aligned."""
        if self._fsm.direction >= 0:
            return pixmap
        flipped = QPixmap.fromImage(pixmap.toImage().mirrored(True, False))
        return flipped if not flipped.isNull() else pixmap

    def _apply_sprite_mask(self, pixmap: QPixmap) -> None:
        """Clip the native window to the sprite alpha (needed on Windows)."""
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        mask_image = image.createAlphaMask()
        mask = QBitmap.fromImage(mask_image)
        if not mask.isNull():
            self.setMask(mask)

    def _paint_sprite(self, painter: QPainter, pixmap: QPixmap) -> None:
        target = QRect(0, 0, self._pet_width, self._pet_height)
        painter.drawPixmap(target, pixmap)

    def _paint_fallback(self, painter: QPainter) -> None:
        """Draw a simple cartoon blob when sprite PNGs are missing."""
        cx, cy = self._pet_width / 2, self._pet_height / 2
        radius = min(self._pet_width, self._pet_height) * 0.38

        body = QColor(self._fallback_body)
        outline = QColor(self._fallback_outline)
        eye_white = QColor(self._fallback_eye)
        pupil = QColor(self._fallback_pupil)

        # Slight squash when falling, stretch when walking, wider when sitting.
        scale_y = 1.0
        scale_x = 1.0
        body_offset_y = 0.0
        if self._fsm.state == PetState.FALLING:
            scale_y = 1.12
        elif self._fsm.state in (PetState.WALKING, PetState.CLIMBING):
            scale_y = 0.95
        elif self._fsm.state == PetState.SIT:
            scale_x = 1.15
            scale_y = 0.72
            body_offset_y = 8.0

        painter.save()
        painter.translate(cx, cy + body_offset_y)
        painter.scale(scale_x, scale_y)

        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), radius, radius * 1.05)
        painter.setPen(QPen(outline, 2))
        painter.setBrush(QBrush(body))
        painter.drawPath(path)

        # Eyes shift with facing direction; half-lidded while sitting.
        eye_dx = 7 * self._fsm.direction
        eye_y = -6
        eye_h = 7 if self._fsm.state != PetState.SIT else 4
        for side in (-1, 1):
            ex = side * 10 + eye_dx * 0.3
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(eye_white))
            painter.drawEllipse(QPointF(ex, eye_y), 6, eye_h)
            painter.setBrush(QBrush(pupil))
            pupil_dx = 2 * self._fsm.direction
            painter.drawEllipse(QPointF(ex + pupil_dx, eye_y + 1), 3, 4)

        # Simple feet for walk animation alternation.
        if self._fsm.state in (PetState.WALKING, PetState.CLIMBING):
            painter.setPen(QPen(outline, 2))
            painter.setBrush(QBrush(body))
            step = 4 if self._frame_index % 2 == 0 else -4
            for side in (-1, 1):
                fx = side * 14
                fy = int(radius * 0.75) + (step if side > 0 else -step)
                painter.drawEllipse(QPointF(fx, fy), 5, 4)

        # Grab indicator while dragged.
        if self._fsm.state == PetState.DRAGGED:
            painter.setPen(QPen(outline, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(int(-radius - 4), int(-radius - 10), 12, 12, 0, 180 * 16)
            painter.drawArc(int(radius - 8), int(-radius - 10), 12, 12, 0, 180 * 16)

        painter.restore()
