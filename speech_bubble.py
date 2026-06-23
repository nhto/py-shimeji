"""Floating speech bubble shown above a desktop pet."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from config import (
    SPEECH_BUBBLE_DURATION_MS,
    SPEECH_BUBBLE_GAP_PX,
    SPEECH_BUBBLE_MAX_WIDTH,
    SPEECH_BUBBLE_PADDING_PX,
)

if TYPE_CHECKING:
    from pet_window import PetWindow


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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_text(self, text: str) -> None:
        """Display text above the pet for a few seconds."""
        self._text = text
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

    def _resize_to_content(self) -> None:
        font = QFont("Segoe UI", 10)
        metrics = QFontMetrics(font)
        inner_width = SPEECH_BUBBLE_MAX_WIDTH - 2 * SPEECH_BUBBLE_PADDING_PX
        text_rect = metrics.boundingRect(
            0,
            0,
            inner_width,
            0,
            int(Qt.TextFlag.TextWordWrap),
            self._text,
        )
        tail_height = 8
        width = min(
            SPEECH_BUBBLE_MAX_WIDTH,
            max(72, text_rect.width() + 2 * SPEECH_BUBBLE_PADDING_PX),
        )
        height = text_rect.height() + 2 * SPEECH_BUBBLE_PADDING_PX + tail_height
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
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawPath(bubble)

        font = QFont("Segoe UI", 10)
        painter.setFont(font)
        painter.setPen(QColor("#1e293b"))
        painter.drawText(
            SPEECH_BUBBLE_PADDING_PX,
            SPEECH_BUBBLE_PADDING_PX,
            self.width() - 2 * SPEECH_BUBBLE_PADDING_PX,
            body_bottom - 2 * SPEECH_BUBBLE_PADDING_PX,
            int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            self._text,
        )
        painter.end()
