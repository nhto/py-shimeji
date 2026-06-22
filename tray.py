"""System tray icon and context menu for the desktop pet."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog, QMenu, QSystemTrayIcon

from chat_window import ChatWindow
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

        chat_action = QAction("Chat with bubu", menu)
        chat_action.triggered.connect(self._open_chat)
        menu.addAction(chat_action)

        menu.addSeparator()

        self._click_through_action = QAction("Click-through (pass mouse clicks)", menu)
        self._click_through_action.setCheckable(True)
        self._click_through_action.setChecked(False)
        self._click_through_action.setToolTip(
            "When enabled, pets ignore the mouse. Disable to drag them."
        )
        self._click_through_action.toggled.connect(self._set_click_through)
        menu.addAction(self._click_through_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._menu = menu
        self._menu_host_pet: PetWindow | None = None
        menu.aboutToHide.connect(self._on_menu_closed)
        self._tray.setContextMenu(menu)
        self._tray.show()

    def show_context_menu(self, global_pos: QPoint, pet: PetWindow | None = None) -> None:
        """Show the app menu at a screen position (e.g. pet right-click)."""
        if self._menu_host_pet is not None and self._menu_host_pet is not pet:
            self._menu_host_pet.end_menu_hold()
        self._menu_host_pet = pet
        self._refresh_menu_state()
        self._menu.popup(global_pos)

    def _on_menu_closed(self) -> None:
        if self._menu_host_pet is not None:
            self._menu_host_pet.end_menu_hold()
            self._menu_host_pet = None

    def _refresh_menu_state(self) -> None:
        for index, pet in enumerate(self._pets, start=1):
            action = self._visibility_actions[index]
            visible = pet.isVisible()
            action.blockSignals(True)
            action.setChecked(visible)
            action.setText(f"{'Hide' if visible else 'Show'} Pet {index}")
            action.blockSignals(False)

        click_through = bool(self._pets) and all(pet.click_through for pet in self._pets)
        self._click_through_action.blockSignals(True)
        self._click_through_action.setChecked(click_through)
        self._click_through_action.blockSignals(False)

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

    def _set_click_through(self, enabled: bool) -> None:
        for pet in self._pets:
            pet.set_click_through(enabled)

    def _open_chat(self) -> None:
        pet = self._menu_host_pet or (self._pets[0] if self._pets else None)
        parent = self._pets[0] if self._pets else None
        ChatWindow.open_chat(parent, pet=pet)

    def _quit(self) -> None:
        self._tray.hide()
        self._app.quit()
