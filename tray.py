"""System tray icon and context menu for the desktop pet."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog, QMenu, QSystemTrayIcon

from config import FALLBACK_BODY_COLOR, FALLBACK_OUTLINE_COLOR, get_pet_sprites_dir
from pet_window import PetWindow


def _build_tray_icon() -> QIcon:
    """Use the first pet's idle sprite when available; otherwise draw a fallback blob."""
    sprite_path = get_pet_sprites_dir(0) / "idle_1.png"
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

    def __init__(self, app: QApplication, pets: list[PetWindow]) -> None:
        self._app = app
        self._pets = pets
        self._tray = QSystemTrayIcon(_build_tray_icon(), parent=pets[0] if pets else None)
        self._tray.setToolTip("py-shimeji")

        menu = QMenu()
        self._visibility_actions: dict[int, QAction] = {}
        for index, pet in enumerate(pets, start=1):
            visible = pet.isVisible()
            action = QAction(
                f"{'Hide' if visible else 'Show'} Pet {index}",
                menu,
            )
            action.setCheckable(True)
            action.setChecked(visible)
            action.toggled.connect(self._make_visibility_toggle(pet, action, index))
            menu.addAction(action)
            self._visibility_actions[index] = action

        if pets:
            menu.addSeparator()
            for index, pet in enumerate(pets, start=1):
                change_action = QAction(f"Change Pet {index} sprites...", menu)
                change_action.triggered.connect(
                    self._make_change_sprites_handler(pet, index)
                )
                menu.addAction(change_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.show()

    @staticmethod
    def _make_visibility_toggle(pet: PetWindow, action: QAction, index: int):
        def toggle(visible: bool) -> None:
            pet.setVisible(visible)
            action.setText(f"{'Hide' if visible else 'Show'} Pet {index}")

        return toggle

    def _make_change_sprites_handler(self, pet: PetWindow, index: int):
        def change_sprites() -> None:
            folder = QFileDialog.getExistingDirectory(
                None,
                f"Select sprite folder for Pet {index}",
                str(pet.sprites_dir),
            )
            if not folder:
                return
            pet.reload_sprites(Path(folder))
            if pet.has_sprites:
                pet.show()
                action = self._visibility_actions.get(index)
                if action is not None:
                    action.blockSignals(True)
                    action.setChecked(True)
                    action.setText(f"Hide Pet {index}")
                    action.blockSignals(False)

        return change_sprites

    def _quit(self) -> None:
        self._tray.hide()
        self._app.quit()
