"""Frameless transparent pet window with rendering, input, and physics."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QImage,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QShowEvent,
)
from PyQt6.QtWidgets import QWidget

from config import (
    ANIMATION_INTERVAL_MS,
    CLIMB_SPEED_PX,
    FALL_TICK_MS,
    GRAVITY_PX,
    PET_FALLBACK_PALETTES,
    PET_HEIGHT,
    PET_WIDTH,
    SPRITE_FILES,
    SURFACE_REFRESH_MS,
    WALK_SPEED_PX,
    get_pet_sprites_dir,
)
from states import PetState, PetStateMachine
from surfaces import HorizontalLedge, SurfaceTracker, VerticalLedge


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


def _prepare_sprite(path: Path) -> QPixmap | None:
    """Load, scale, de-background, and center a sprite frame."""
    image = QImage(str(path))
    if image.isNull():
        return None

    scaled = image.scaled(
        PET_WIDTH,
        PET_HEIGHT,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled = _key_out_background(scaled)

    canvas = QImage(PET_WIDTH, PET_HEIGHT, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.drawImage(
        (PET_WIDTH - scaled.width()) // 2,
        (PET_HEIGHT - scaled.height()) // 2,
        scaled,
    )
    painter.end()

    pixmap = QPixmap.fromImage(canvas)
    return pixmap if not pixmap.isNull() else None


class SpriteCache:
    """Loads sprite frames from disk; missing files are represented as None."""

    def __init__(self, assets_dir: Path) -> None:
        self._assets_dir = assets_dir
        self._cache: dict[str, list[QPixmap | None]] = {}
        self._load_all()

    def _load_all(self) -> None:
        for group, filenames in SPRITE_FILES.items():
            frames: list[QPixmap | None] = []
            for name in filenames:
                path = self._assets_dir / name
                frames.append(_prepare_sprite(path) if path.is_file() else None)
            self._cache[group] = frames

    def reload(self, assets_dir: Path | None = None) -> None:
        """Reload sprite frames from disk (optionally from a new folder)."""
        if assets_dir is not None:
            self._assets_dir = assets_dir
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
            PetState.WALKING: "walk",
            PetState.CLIMBING: "walk",
            PetState.FALLING: "fall",
            PetState.DRAGGED: "drag",
        }
        return self._cache.get(mapping[state], self._cache["idle"])

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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet_index = pet_index
        self._pet_count = max(1, pet_count)
        self._exclude_hwnds = exclude_hwnds if exclude_hwnds is not None else set()
        self._sprites_dir = sprites_dir or get_pet_sprites_dir(pet_index)
        self._start_fraction = (pet_index + 1) / (self._pet_count + 1)
        palette = PET_FALLBACK_PALETTES[pet_index % len(PET_FALLBACK_PALETTES)]
        self._fallback_body = palette["body"]
        self._fallback_outline = palette["outline"]
        self._fallback_eye = palette["eye"]
        self._fallback_pupil = palette["pupil"]

        self._sprites = SpriteCache(self._sprites_dir)
        self._frame_index: int = 0
        self._drag_offset = QPoint(0, 0)
        self._is_dragging: bool = False
        self._play_area: QRect = QRect()
        self._surfaces = SurfaceTracker()
        self._active_ledge: HorizontalLedge | None = None
        self._climb_ledge: VerticalLedge | None = None
        self._climb_direction: int = -1  # -1 = up, 1 = down

        self._fsm = PetStateMachine(self._on_fsm_state_changed, parent=self)

        self._setup_window()
        self._setup_timers()
        self._place_on_floor()

    @property
    def sprites_dir(self) -> Path:
        return self._sprites_dir

    @property
    def has_sprites(self) -> bool:
        return self._sprites.has_sprites

    def reload_sprites(self, sprites_dir: Path) -> None:
        """Load a new PNG set for this pet and refresh the window."""
        self._sprites_dir = sprites_dir
        self._sprites.reload(sprites_dir)
        self._frame_index = 0
        self.update()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setFixedSize(PET_WIDTH, PET_HEIGHT)
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
        self._fall_timer.setInterval(FALL_TICK_MS)
        self._fall_timer.timeout.connect(self._on_fall_tick)

        self._move_timer = QTimer(self)
        self._move_timer.setInterval(FALL_TICK_MS)
        self._move_timer.timeout.connect(self._on_movement_tick)
        self._move_timer.start()

        self._surface_timer = QTimer(self)
        self._surface_timer.setInterval(SURFACE_REFRESH_MS)
        self._surface_timer.timeout.connect(self._refresh_surfaces)
        self._surface_timer.start()

    def _place_on_floor(self) -> None:
        self._refresh_play_area()
        x = self._play_area.left() + int(
            (self._play_area.width() - PET_WIDTH) * self._start_fraction
        )
        y = self._play_area.bottom() - PET_HEIGHT + 1
        self.move(x, y)

    def _refresh_play_area(self) -> None:
        """Use available geometry so the pet rests above the taskbar/dock."""
        screen = QGuiApplication.screenAt(self.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            self._play_area = QRect(0, 0, 1920, 1080)
            return
        self._play_area = screen.availableGeometry()

    def _refresh_surfaces(self) -> None:
        self._refresh_play_area()
        self._surfaces.refresh(self._play_area, self._exclude_hwnds)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._exclude_hwnds.add(int(self.winId()))
        self._refresh_surfaces()
        self._active_ledge = self._surfaces.floor_ledge(self._play_area)

    # ------------------------------------------------------------------
    # State machine callbacks
    # ------------------------------------------------------------------

    def _on_fsm_state_changed(self, old: PetState, new: PetState) -> None:
        self._frame_index = 0
        if new == PetState.FALLING:
            self._fall_timer.start()
        elif old == PetState.FALLING:
            self._fall_timer.stop()
        self.update()

    # ------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------

    def _on_animation_tick(self) -> None:
        if self._fsm.state == PetState.DRAGGED:
            return
        frames = self._sprites.frames_for_state(self._fsm.state)
        if frames:
            self._frame_index = (self._frame_index + 1) % len(frames)
        self.update()

    def _on_movement_tick(self) -> None:
        if self._is_dragging:
            return
        self._refresh_surfaces()
        if self._fsm.state == PetState.WALKING:
            self._horizontal_walk_tick()
        elif self._fsm.state == PetState.CLIMBING:
            self._climb_tick()

    def _horizontal_walk_tick(self) -> None:
        pos = self.pos()
        direction = self._fsm.direction
        new_x = pos.x() + WALK_SPEED_PX * direction
        pet_top = pos.y()
        pet_bottom = pos.y() + PET_HEIGHT

        ledge = self._active_ledge
        if ledge is None:
            ledge = self._surfaces.floor_ledge(self._play_area)
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
            self._start_climb(climb, direction=-1)
            return

        pet_left_min = ledge.left
        pet_left_max = ledge.right - PET_WIDTH

        if new_x < pet_left_min:
            if ledge.ledge_id != "screen" and direction < 0:
                vertical = self._surfaces.vertical_for_window(ledge.hwnd, "left")
                if vertical is not None:
                    self._start_climb(vertical, direction=1)
                    return
            if ledge.ledge_id != "screen":
                self._start_fall()
                return
            new_x = self._play_area.left()
            self._fsm.set_direction(1)
            self._fsm.notify_boundary_hit()
        elif new_x > pet_left_max:
            if ledge.ledge_id != "screen":
                self._start_fall()
                return
            new_x = self._play_area.right() - PET_WIDTH + 1
            self._fsm.set_direction(-1)
            self._fsm.notify_boundary_hit()

        self.move(new_x, ledge.stand_y)

    def _climb_tick(self) -> None:
        climb = self._climb_ledge
        if climb is None:
            self._start_fall()
            return

        pos = self.pos()
        pet_x = climb.pet_x()

        if self._climb_direction < 0:
            new_y = pos.y() - CLIMB_SPEED_PX
            if new_y <= climb.top - PET_HEIGHT + 8:
                top_ledge = self._horizontal_ledge_for_hwnd(climb.hwnd)
                if top_ledge is None:
                    self._start_fall()
                    return
                self._active_ledge = top_ledge
                land_x = max(
                    top_ledge.left,
                    min(pet_x, top_ledge.right - PET_WIDTH),
                )
                self.move(land_x, top_ledge.stand_y)
                self._climb_ledge = None
                self._fsm.force_state(PetState.WALKING)
            else:
                self.move(pet_x, new_y)
            return

        new_y = pos.y() + CLIMB_SPEED_PX
        if new_y + PET_HEIGHT >= climb.bottom - 4:
            floor = self._surfaces.floor_ledge(self._play_area)
            self._active_ledge = floor
            land_x = max(floor.left, min(pet_x, floor.right - PET_WIDTH))
            self.move(land_x, floor.stand_y)
            self._climb_ledge = None
            self._fsm.force_state(PetState.WALKING)
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
        self.move(vertical.pet_x(), self.pos().y())
        self._fsm.force_state(PetState.CLIMBING)

    def _start_fall(self) -> None:
        self._active_ledge = None
        self._climb_ledge = None
        self._fsm.force_state(PetState.FALLING)

    def _on_fall_tick(self) -> None:
        if self._fsm.state != PetState.FALLING:
            return
        self._refresh_surfaces()
        pos = self.pos()
        new_y = pos.y() + GRAVITY_PX
        next_feet_y = new_y + PET_HEIGHT - 1
        landing = self._surfaces.find_landing_ledge(pos.x(), pos.y(), next_feet_y)
        if landing is not None:
            self.move(pos.x(), landing.stand_y)
            self._active_ledge = landing
            self._fall_timer.stop()
            self._fsm.resume()
            self._fsm.force_state(PetState.IDLE)
        else:
            self.move(pos.x(), new_y)

    def _is_on_support(self) -> bool:
        self._refresh_surfaces()
        return self._surfaces.find_ledge_at(self.pos().x(), self.pos().y()) is not None

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._is_dragging = True
        self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self._fsm.pause()
        self._fsm.force_state(PetState.DRAGGED)
        self._fall_timer.stop()
        self._climb_ledge = None
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self._is_dragging:
            return
        new_pos = event.globalPosition().toPoint() - self._drag_offset
        self.move(new_pos)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or not self._is_dragging:
            return
        self._is_dragging = False
        self._fsm.resume()
        if self._is_on_support():
            ledge = self._surfaces.find_ledge_at(self.pos().x(), self.pos().y())
            self._active_ledge = ledge
            self._fsm.force_state(PetState.IDLE)
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
            self._paint_sprite(painter, pixmap)
            self._apply_sprite_mask(pixmap)
        else:
            self._paint_fallback(painter)
            self.clearMask()

        painter.end()

    def _apply_sprite_mask(self, pixmap: QPixmap) -> None:
        """Clip the native window to the sprite silhouette (needed on Windows)."""
        mask = pixmap.createHeuristicMask()
        if not mask.isNull():
            self.setMask(mask)

    def _paint_sprite(self, painter: QPainter, pixmap: QPixmap) -> None:
        target = QRect(0, 0, PET_WIDTH, PET_HEIGHT)
        if self._fsm.direction < 0:
            painter.save()
            painter.translate(PET_WIDTH, 0)
            painter.scale(-1, 1)
            painter.drawPixmap(target, pixmap)
            painter.restore()
        else:
            painter.drawPixmap(target, pixmap)

    def _paint_fallback(self, painter: QPainter) -> None:
        """Draw a simple cartoon blob when sprite PNGs are missing."""
        cx, cy = PET_WIDTH / 2, PET_HEIGHT / 2
        radius = min(PET_WIDTH, PET_HEIGHT) * 0.38

        body = QColor(self._fallback_body)
        outline = QColor(self._fallback_outline)
        eye_white = QColor(self._fallback_eye)
        pupil = QColor(self._fallback_pupil)

        # Slight squash when falling, stretch when walking.
        scale_y = 1.0
        if self._fsm.state == PetState.FALLING:
            scale_y = 1.12
        elif self._fsm.state in (PetState.WALKING, PetState.CLIMBING):
            scale_y = 0.95

        painter.save()
        painter.translate(cx, cy)
        painter.scale(1.0, scale_y)

        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), radius, radius * 1.05)
        painter.setPen(QPen(outline, 2))
        painter.setBrush(QBrush(body))
        painter.drawPath(path)

        # Eyes shift with facing direction.
        eye_dx = 7 * self._fsm.direction
        eye_y = -6
        for side in (-1, 1):
            ex = side * 10 + eye_dx * 0.3
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(eye_white))
            painter.drawEllipse(QPointF(ex, eye_y), 6, 7)
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
