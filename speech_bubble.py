"""Floating speech bubble shown above a desktop pet."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from bubble_patterns import paint_speech_bubble_pattern
from settings.core import (
    SPEECH_BUBBLE_DURATION_MS,
    SPEECH_BUBBLE_GAP_PX,
    SPEECH_BUBBLE_MAX_WIDTH,
    SPEECH_BUBBLE_PADDING_PX,
    format_speech_bubble_text,
)

if TYPE_CHECKING:
    from pet_window import PetWindow

BubbleAction = tuple[str, Callable[[], None]]


class SpeechBubbleWindow(QWidget):
    """Small always-on-top bubble that follows a pet window."""

    def __init__(self, pet: PetWindow) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._pet = pet
        self._text = ""
        self._pattern_index = 0
        self._actions: list[BubbleAction] = []
        self._action_rects: list[tuple[object, Callable[[], None]]] = []
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_text(
        self,
        text: str,
        *,
        actions: list[BubbleAction] | None = None,
    ) -> None:
        """Display text above the pet for a few seconds."""
        self._text = text
        self._pattern_index = sum(ord(char) for char in text)
        self._actions = list(actions or [])
        self._action_rects = []
        self._resize_to_content()
        self.reposition()
        self.show()
        self.raise_()
        self._hide_timer.start(SPEECH_BUBBLE_DURATION_MS)

    def reposition(self) -> None:
        """Keep the bubble centered above the pet."""
        if not self._pet.isVisible():
            self.hide()
            return

        pet_geo = self._pet.frameGeometry()
        x = pet_geo.center().x() - self.width() // 2
        y = pet_geo.top() - self.height() - SPEECH_BUBBLE_GAP_PX
        self.move(x, y)

    def _content_font(self) -> QFont:
        return QFont("Segoe UI", 10)

    def _action_font(self) -> QFont:
        font = QFont("Segoe UI", 9)
        font.setUnderline(True)
        return font

    def _resize_to_content(self) -> None:
        content_font = self._content_font()
        action_font = self._action_font()
        content_metrics = QFontMetrics(content_font)
        action_metrics = QFontMetrics(action_font)
        inner_width = SPEECH_BUBBLE_MAX_WIDTH - 2 * SPEECH_BUBBLE_PADDING_PX

        text_rect = content_metrics.boundingRect(
            0,
            0,
            inner_width,
            0,
            int(Qt.TextFlag.TextWordWrap),
            self._text,
        )

        action_height = 0
        action_width = 0
        if self._actions:
            action_height = 6 + sum(
                action_metrics.boundingRect(
                    0,
                    0,
                    inner_width,
                    0,
                    int(Qt.TextFlag.TextWordWrap),
                    label,
                ).height()
                for label, _callback in self._actions
            )
            action_width = max(
                action_metrics.horizontalAdvance(label) for label, _callback in self._actions
            )

        tail_height = 8
        width = min(
            SPEECH_BUBBLE_MAX_WIDTH,
            max(
                72,
                text_rect.width() + 2 * SPEECH_BUBBLE_PADDING_PX,
                action_width + 2 * SPEECH_BUBBLE_PADDING_PX,
            ),
        )
        height = (
            text_rect.height()
            + action_height
            + 2 * SPEECH_BUBBLE_PADDING_PX
            + tail_height
        )
        self.setFixedSize(width, height)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        tail_height = 8
        body_bottom = self.height() - tail_height
        radius = 10
        center_x = self.width() // 2

        body = QPainterPath()
        body.addRoundedRect(0, 0, self.width(), body_bottom, radius, radius)

        tail = QPainterPath()
        tail.moveTo(center_x - 7, body_bottom - 1)
        tail.lineTo(center_x, self.height())
        tail.lineTo(center_x + 7, body_bottom - 1)
        tail.closeSubpath()

        bubble = body.united(tail)
        paint_speech_bubble_pattern(
            painter,
            bubble,
            pattern_index=self._pattern_index,
            fill_color=QColor("#ffffff"),
            accent_color=QColor("#f97316"),
        )
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(bubble)

        content_font = self._content_font()
        painter.setFont(content_font)
        painter.setPen(QColor("#1e293b"))
        text_bottom = SPEECH_BUBBLE_PADDING_PX
        if self._text:
            text_rect = QFontMetrics(content_font).boundingRect(
                SPEECH_BUBBLE_PADDING_PX,
                SPEECH_BUBBLE_PADDING_PX,
                self.width() - 2 * SPEECH_BUBBLE_PADDING_PX,
                body_bottom - 2 * SPEECH_BUBBLE_PADDING_PX,
                int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                self._text,
            )
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                self._text,
            )
            text_bottom = text_rect.bottom()

        if self._actions:
            painter.setFont(self._action_font())
            painter.setPen(QColor("#2563eb"))
            y = text_bottom + 6
            inner_width = self.width() - 2 * SPEECH_BUBBLE_PADDING_PX
            self._action_rects = []
            metrics = QFontMetrics(self._action_font())
            for label, callback in self._actions:
                rect = metrics.boundingRect(
                    SPEECH_BUBBLE_PADDING_PX,
                    y,
                    inner_width,
                    0,
                    int(Qt.TextFlag.TextWordWrap),
                    label,
                )
                painter.drawText(
                    rect,
                    int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                    label,
                )
                self._action_rects.append((rect, callback))
                y = rect.bottom() + 2

        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        for rect, callback in self._action_rects:
            if rect.contains(event.pos()):
                callback()
                self.hide()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        over_action = any(rect.contains(event.pos()) for rect, _callback in self._action_rects)
        self.setCursor(
            QCursor(
                Qt.CursorShape.PointingHandCursor
                if over_action
                else Qt.CursorShape.ArrowCursor
            )
        )
        super().mouseMoveEvent(event)
