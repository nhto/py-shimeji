"""System tray icon and context menu for the desktop pet."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from config import ASSETS_DIR, FALLBACK_BODY_COLOR, FALLBACK_OUTLINE_COLOR


def _build_tray_icon() -> QIcon:
    """Use the idle sprite when available; otherwise draw a small fallback blob."""
    sprite_path = ASSETS_DIR / "idle_1.png"
    if sprite_path.is_file():
        icon = QIcon(str(sprite_path))
        if not icon.isNull():
            return icon

    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(QColor(FALLBACK_OUTLINE_COLOR), 2))
    painter.setBrush(QBrush(QColor(FALLBACK_BODY_COLOR)))
    margin = 3
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.end()

    return QIcon(pixmap)


class SystemTray:
    """Owns the tray icon and menu for the lifetime of the application."""

    def __init__(self, app: QApplication, pet: QWidget) -> None:
        self._app = app
        self._tray = QSystemTrayIcon(_build_tray_icon(), parent=pet)
        self._tray.setToolTip("py-shimeji")

        menu = QMenu()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.show()

    def _quit(self) -> None:
        self._tray.hide()
        self._app.quit()
