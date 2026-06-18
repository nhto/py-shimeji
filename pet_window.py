"""Frameless transparent pet window with rendering, input, and physics."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
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
    ASSETS_DIR,
    FALLBACK_BODY_COLOR,
    FALLBACK_EYE_COLOR,
    FALLBACK_OUTLINE_COLOR,
    FALLBACK_PUPIL_COLOR,
    FALL_TICK_MS,
    GRAVITY_PX,
    PET_HEIGHT,
    PET_WIDTH,
    SPRITE_FILES,
    WALK_SPEED_PX,
)
from states import PetState, PetStateMachine


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

    def frames_for_state(self, state: PetState) -> list[QPixmap | None]:
        mapping = {
            PetState.IDLE: "idle",
            PetState.WALKING: "walk",
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sprites = SpriteCache(ASSETS_DIR)
        self._frame_index: int = 0
        self._drag_offset = QPoint(0, 0)
        self._is_dragging: bool = False
        self._play_area: QRect = QRect()

        self._fsm = PetStateMachine(self._on_fsm_state_changed, parent=self)

        self._setup_window()
        self._setup_timers()
        self._place_on_floor_centered()

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
        self._move_timer.timeout.connect(self._on_walk_tick)
        self._move_timer.start()

    def _place_on_floor_centered(self) -> None:
        self._refresh_play_area()
        x = self._play_area.left() + (self._play_area.width() - PET_WIDTH) // 2
        y = self._play_area.bottom() - PET_HEIGHT + 1
        self.move(x, y)

    def _refresh_play_area(self) -> None:
        """Use available geometry so the pet rests above the taskbar/dock."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self._play_area = QRect(0, 0, 1920, 1080)
            return
        self._play_area = screen.availableGeometry()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._refresh_play_area()

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

    def _on_walk_tick(self) -> None:
        if self._fsm.state != PetState.WALKING or self._is_dragging:
            return
        self._refresh_play_area()
        pos = self.pos()
        new_x = pos.x() + WALK_SPEED_PX * self._fsm.direction

        left_bound = self._play_area.left()
        right_bound = self._play_area.right() - PET_WIDTH + 1

        if new_x <= left_bound:
            new_x = left_bound
            self._fsm.set_direction(1)
            self._fsm.notify_boundary_hit()
        elif new_x >= right_bound:
            new_x = right_bound
            self._fsm.set_direction(-1)
            self._fsm.notify_boundary_hit()
        else:
            self.move(new_x, pos.y())
            return

        self.move(new_x, pos.y())

    def _on_fall_tick(self) -> None:
        if self._fsm.state != PetState.FALLING:
            return
        self._refresh_play_area()
        floor_y = self._play_area.bottom() - PET_HEIGHT + 1
        new_y = self.pos().y() + GRAVITY_PX
        if new_y >= floor_y:
            self.move(self.pos().x(), floor_y)
            self._fall_timer.stop()
            self._fsm.resume()
            self._fsm.force_state(PetState.IDLE)
        else:
            self.move(self.pos().x(), new_y)

    def _is_on_floor(self) -> bool:
        self._refresh_play_area()
        floor_y = self._play_area.bottom() - PET_HEIGHT + 1
        return self.pos().y() >= floor_y

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
        if self._is_on_floor():
            self._fsm.force_state(PetState.IDLE)
        else:
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

        body = QColor(FALLBACK_BODY_COLOR)
        outline = QColor(FALLBACK_OUTLINE_COLOR)
        eye_white = QColor(FALLBACK_EYE_COLOR)
        pupil = QColor(FALLBACK_PUPIL_COLOR)

        # Slight squash when falling, stretch when walking.
        scale_y = 1.0
        if self._fsm.state == PetState.FALLING:
            scale_y = 1.12
        elif self._fsm.state == PetState.WALKING:
            scale_y = 0.95

        painter.save()
        painter.translate(cx, cy)
        painter.scale(1.0, scale_y)

        path = QPainterPath()
        path.addEllipse(QPoint(0, 0), int(radius), int(radius * 1.05))
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
            painter.drawEllipse(QPoint(int(ex), eye_y), 6, 7)
            painter.setBrush(QBrush(pupil))
            pupil_dx = 2 * self._fsm.direction
            painter.drawEllipse(QPoint(int(ex + pupil_dx), eye_y + 1), 3, 4)

        # Simple feet for walk animation alternation.
        if self._fsm.state == PetState.WALKING:
            painter.setPen(QPen(outline, 2))
            painter.setBrush(QBrush(body))
            step = 4 if self._frame_index % 2 == 0 else -4
            for side in (-1, 1):
                fx = side * 14
                fy = int(radius * 0.75) + (step if side > 0 else -step)
                painter.drawEllipse(QPoint(fx, fy), 5, 4)

        # Grab indicator while dragged.
        if self._fsm.state == PetState.DRAGGED:
            painter.setPen(QPen(outline, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(int(-radius - 4), int(-radius - 10), 12, 12, 0, 180 * 16)
            painter.drawArc(int(radius - 8), int(-radius - 10), 12, 12, 0, 180 * 16)

        painter.restore()
