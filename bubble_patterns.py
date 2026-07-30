"""Decorative patterns for chat and speech bubbles."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

CHAT_BUBBLE_PATTERN_IDS: tuple[str, ...] = (
    "accent_bar",
    "dot_strip",
    "dash_edge",
    "corner_dots",
    "soft_frame",
)

SPEECH_BUBBLE_PATTERN_IDS: tuple[str, ...] = (
    "dots",
    "stripes",
    "crosshatch",
    "waves",
    "grid",
)


def chat_bubble_pattern_count() -> int:
    return len(CHAT_BUBBLE_PATTERN_IDS)


def speech_bubble_pattern_count() -> int:
    return len(SPEECH_BUBBLE_PATTERN_IDS)


def _pattern_id(pattern_index: int, pattern_ids: tuple[str, ...]) -> str:
    if not pattern_ids:
        return "solid"
    return pattern_ids[pattern_index % len(pattern_ids)]


def _accent_cell(color: str, width: int = 4) -> str:
    return f'<td width="{width}" bgcolor="{color}"></td>'


def _dot_cells(color: str, count: int, size: int = 4) -> str:
    return "".join(
        f'<td width="{size}" height="{size}" bgcolor="{color}"></td>' for _ in range(count)
    )


def wrap_chat_bubble_content(
    body_html: str,
    *,
    is_user: bool,
    pattern_index: int,
    bubble_bg: str,
    bubble_fg: str,
    border: str,
) -> str:
    """Wrap bubble body HTML with a QTextEdit-friendly decorative pattern."""
    pattern = _pattern_id(pattern_index, CHAT_BUBBLE_PATTERN_IDS)
    accent = "#a5b4fc" if is_user else "#fdba74"
    accent_soft = "#c7d2fe" if is_user else "#fed7aa"
    accent_dark = "#6366f1" if is_user else "#f97316"
    content_style = (
        f"padding:10px 14px; color:{bubble_fg}; font-size:13px; line-height:1.55; {border}"
    )

    if pattern == "accent_bar":
        accent_side = _accent_cell(accent_dark, 4)
        if is_user:
            inner = (
                "<table cellspacing=\"0\" cellpadding=\"0\">"
                f"<tr><td bgcolor=\"{bubble_bg}\" style=\"{content_style}\">{body_html}</td>"
                f"{accent_side}</tr></table>"
            )
        else:
            inner = (
                "<table cellspacing=\"0\" cellpadding=\"0\">"
                f"<tr>{accent_side}"
                f"<td bgcolor=\"{bubble_bg}\" style=\"{content_style}\">{body_html}</td></tr></table>"
            )
        return inner

    if pattern == "dot_strip":
        dot_row = f"<tr>{_dot_cells(accent, 14)}</tr>"
        return (
            "<table cellspacing=\"1\" cellpadding=\"0\">"
            f"{dot_row}"
            f"<tr><td colspan=\"14\" bgcolor=\"{bubble_bg}\" style=\"{content_style}\">"
            f"{body_html}</td></tr></table>"
        )

    if pattern == "dash_edge":
        ticks = "".join(
            f'<tr><td width="3" height="5" bgcolor="{accent if index % 2 == 0 else accent_soft}"></td></tr>'
            for index in range(4)
        )
        return (
            "<table cellspacing=\"0\" cellpadding=\"0\"><tr>"
            f"<td valign=\"top\"><table cellspacing=\"0\" cellpadding=\"0\">{ticks}</table></td>"
            f"<td bgcolor=\"{bubble_bg}\" style=\"{content_style}\">{body_html}</td>"
            "</tr></table>"
        )

    if pattern == "corner_dots":
        corner = _dot_cells(accent_dark, 1, 5)
        return (
            "<table cellspacing=\"0\" cellpadding=\"0\">"
            f"<tr>{corner}<td colspan=\"12\" bgcolor=\"{bubble_bg}\" style=\"{content_style}\">"
            f"{body_html}</td>{corner}</tr>"
            f"<tr>{corner}<td colspan=\"12\" bgcolor=\"{accent_soft}\" height=\"2\"></td>"
            f"{corner}</tr></table>"
        )

    if pattern == "soft_frame":
        frame = _accent_cell(accent_soft, 2)
        return (
            "<table cellspacing=\"0\" cellpadding=\"0\">"
            f"<tr>{frame}<td colspan=\"12\" bgcolor=\"{accent_soft}\" height=\"2\"></td>{frame}</tr>"
            f"<tr>{frame}<td bgcolor=\"{bubble_bg}\" style=\"{content_style}\">{body_html}</td>"
            f"{frame}</tr>"
            f"<tr>{frame}<td colspan=\"12\" bgcolor=\"{accent_soft}\" height=\"2\"></td>{frame}</tr>"
            "</table>"
        )

    return f'<span style="background-color:{bubble_bg}; {content_style}">{body_html}</span>'


def paint_speech_bubble_pattern(
    painter: QPainter,
    clip_path: QPainterPath,
    *,
    pattern_index: int,
    fill_color: QColor,
    accent_color: QColor,
) -> None:
    """Paint a subtle fill pattern inside a speech bubble clip path."""
    pattern = _pattern_id(pattern_index, SPEECH_BUBBLE_PATTERN_IDS)
    bounds = clip_path.boundingRect()
    if bounds.isEmpty():
        return

    painter.save()
    painter.setClipPath(clip_path)
    painter.fillPath(clip_path, fill_color)

    accent = QColor(accent_color)
    accent.setAlpha(36)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)

    left = int(bounds.left())
    top = int(bounds.top())
    right = int(bounds.right())
    bottom = int(bounds.bottom())

    if pattern == "dots":
        step = 10
        radius = 1.6
        for y in range(top + 6, bottom - 4, step):
            offset = step // 2 if ((y - top) // step) % 2 else 0
            for x in range(left + 6 + offset, right - 4, step):
                painter.drawEllipse(x, y, int(radius * 2), int(radius * 2))
    elif pattern == "stripes":
        painter.setPen(QPen(accent, 1.0))
        for x in range(left - bottom + top, right + bottom - top, 8):
            painter.drawLine(x, bottom, x + (bottom - top), top)
    elif pattern == "crosshatch":
        painter.setPen(QPen(accent, 1.0))
        for x in range(left - bottom + top, right + bottom - top, 10):
            painter.drawLine(x, bottom, x + (bottom - top), top)
        for x in range(left, right + bottom - top, 10):
            painter.drawLine(x, top, x - (bottom - top), bottom)
    elif pattern == "waves":
        painter.setPen(QPen(accent, 1.2))
        wave_height = 4
        wave_length = 14
        for y in range(top + 8, bottom - 4, 10):
            for x in range(left + 4, right - 4, wave_length):
                path = QPainterPath()
                path.moveTo(x, y)
                path.cubicTo(
                    x + wave_length * 0.25,
                    y - wave_height,
                    x + wave_length * 0.75,
                    y + wave_height,
                    x + wave_length,
                    y,
                )
                painter.drawPath(path)
    elif pattern == "grid":
        painter.setPen(QPen(accent, 1.0))
        for x in range(left + 6, right - 2, 12):
            painter.drawLine(x, top + 4, x, bottom - 4)
        for y in range(top + 6, bottom - 2, 12):
            painter.drawLine(left + 4, y, right - 4, y)

    painter.restore()
