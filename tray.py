"""System tray icon and context menu for the desktop pet."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from api_key_dialog import open_preferences_dialog
from chat_window import ChatWindow
from config import (
    FALLBACK_BODY_COLOR,
    FALLBACK_OUTLINE_COLOR,
    TRAY_API_KEY_CLEARED_MESSAGE_LABELS,
    TRAY_API_KEY_SAVED_MESSAGE_LABELS,
    TRAY_CHANGE_SPRITES_LABELS,
    TRAY_CHAT_LABELS,
    TRAY_CLICK_THROUGH_LABELS,
    TRAY_CLICK_THROUGH_TOOLTIP_LABELS,
    TRAY_HIDE_PET_LABELS,
    TRAY_NO_API_KEY_MESSAGE_LABELS,
    TRAY_NO_API_KEY_TITLE_LABELS,
    TRAY_PAUSE_PETS_LABELS,
    TRAY_PAUSE_PETS_TOOLTIP_LABELS,
    TRAY_PREFERENCE_LABELS,
    TRAY_PREFERENCES_SAVED_MESSAGE_LABELS,
    TRAY_QUIT_LABELS,
    TRAY_SHOW_PET_LABELS,
    get_chat_language,
    get_pet_sprites_dir,
    get_saved_pets_paused,
    has_openrouter_api_key,
    localized,
    set_saved_pet_visible,
    set_saved_pets_paused,
)
from pet_window import PetWindow
from sprite_picker_dialog import open_sprite_picker_dialog


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
            action = QAction("", menu)
            action.setCheckable(True)
            action.setChecked(visible)
            action.toggled.connect(self._make_visibility_toggle(pet, action, index))
            menu.addAction(action)
            self._visibility_actions[index] = action

        self._change_sprites_actions: dict[int, QAction] = {}
        if pets:
            menu.addSeparator()
            for index, pet in enumerate(pets, start=1):
                change_action = QAction("", menu)
                change_action.triggered.connect(
                    self._make_change_sprites_handler(pet, index)
                )
                menu.addAction(change_action)
                self._change_sprites_actions[index] = change_action

        menu.addSeparator()

        self._chat_action = QAction("", menu)
        self._chat_action.triggered.connect(self._open_chat)
        menu.addAction(self._chat_action)

        self._preferences_action = QAction("", menu)
        self._preferences_action.triggered.connect(self._open_preferences)
        menu.addAction(self._preferences_action)

        menu.addSeparator()

        self._pause_pets_action = QAction("", menu)
        self._pause_pets_action.setCheckable(True)
        self._pause_pets_action.setChecked(get_saved_pets_paused())
        self._pause_pets_action.toggled.connect(self._set_motion_paused)
        menu.addAction(self._pause_pets_action)

        self._click_through_action = QAction("", menu)
        self._click_through_action.setCheckable(True)
        self._click_through_action.setChecked(False)
        self._click_through_action.toggled.connect(self._set_click_through)
        menu.addAction(self._click_through_action)

        menu.addSeparator()

        self._quit_action = QAction("", menu)
        self._quit_action.triggered.connect(self._quit)
        menu.addAction(self._quit_action)

        self._menu = menu
        self._menu_host_pet: PetWindow | None = None
        menu.aboutToHide.connect(self._on_menu_closed)
        self._tray.setContextMenu(menu)
        self._tray.show()

        self._apply_menu_language()

        if not has_openrouter_api_key():
            language = get_chat_language()
            self._tray.showMessage(
                localized(TRAY_NO_API_KEY_TITLE_LABELS, language),
                localized(TRAY_NO_API_KEY_MESSAGE_LABELS, language),
                QSystemTrayIcon.MessageIcon.Information,
                8_000,
            )

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

    def _pet_visibility_label(self, index: int, visible: bool, language: str | None = None) -> str:
        labels = TRAY_HIDE_PET_LABELS if visible else TRAY_SHOW_PET_LABELS
        return localized(labels, language).format(index=index)

    def _apply_menu_language(self, language: str | None = None) -> None:
        lang = language or get_chat_language()

        for index, pet in enumerate(self._pets, start=1):
            action = self._visibility_actions[index]
            action.setText(self._pet_visibility_label(index, pet.isVisible(), lang))

        for index, action in self._change_sprites_actions.items():
            action.setText(
                localized(TRAY_CHANGE_SPRITES_LABELS, lang).format(index=index)
            )

        self._chat_action.setText(localized(TRAY_CHAT_LABELS, lang))
        self._preferences_action.setText(localized(TRAY_PREFERENCE_LABELS, lang))
        self._pause_pets_action.setText(localized(TRAY_PAUSE_PETS_LABELS, lang))
        self._pause_pets_action.setToolTip(
            localized(TRAY_PAUSE_PETS_TOOLTIP_LABELS, lang)
        )
        self._click_through_action.setText(localized(TRAY_CLICK_THROUGH_LABELS, lang))
        self._click_through_action.setToolTip(
            localized(TRAY_CLICK_THROUGH_TOOLTIP_LABELS, lang)
        )
        self._quit_action.setText(localized(TRAY_QUIT_LABELS, lang))

    def _refresh_menu_state(self) -> None:
        language = get_chat_language()
        self._apply_menu_language(language)

        for index, pet in enumerate(self._pets, start=1):
            action = self._visibility_actions[index]
            visible = pet.isVisible()
            action.blockSignals(True)
            action.setChecked(visible)
            action.setText(self._pet_visibility_label(index, visible, language))
            action.blockSignals(False)

        click_through = bool(self._pets) and all(pet.click_through for pet in self._pets)
        self._click_through_action.blockSignals(True)
        self._click_through_action.setChecked(click_through)
        self._click_through_action.blockSignals(False)

        motion_paused = bool(self._pets) and all(pet.motion_paused for pet in self._pets)
        self._pause_pets_action.blockSignals(True)
        self._pause_pets_action.setChecked(motion_paused)
        self._pause_pets_action.blockSignals(False)

        if has_openrouter_api_key():
            self._chat_action.setToolTip("")
        else:
            self._chat_action.setToolTip(
                localized(TRAY_NO_API_KEY_MESSAGE_LABELS, language)
            )

    @staticmethod
    def _make_visibility_toggle(pet: PetWindow, action: QAction, index: int):
        def toggle(visible: bool) -> None:
            pet.setVisible(visible)
            set_saved_pet_visible(index - 1, visible)
            language = get_chat_language()
            labels = TRAY_HIDE_PET_LABELS if visible else TRAY_SHOW_PET_LABELS
            action.setText(localized(labels, language).format(index=index))

        return toggle

    def _make_change_sprites_handler(self, pet: PetWindow, index: int):
        def change_sprites() -> None:
            folder = open_sprite_picker_dialog(
                index,
                pet.sprites_dir,
                parent=self._pets[0] if self._pets else None,
                pet=pet,
            )
            if folder is None:
                return
            pet.reload_sprites(folder)
            if pet.has_sprites:
                pet.show()
                set_saved_pet_visible(index - 1, True)
                action = self._visibility_actions.get(index)
                if action is not None:
                    language = get_chat_language()
                    action.blockSignals(True)
                    action.setChecked(True)
                    action.setText(
                        localized(TRAY_HIDE_PET_LABELS, language).format(index=index)
                    )
                    action.blockSignals(False)

        return change_sprites

    def _set_click_through(self, enabled: bool) -> None:
        for pet in self._pets:
            pet.set_click_through(enabled)

    def _set_motion_paused(self, enabled: bool) -> None:
        for pet in self._pets:
            pet.set_motion_paused(enabled)
        set_saved_pets_paused(enabled)

    def _open_chat(self) -> None:
        pet = self._menu_host_pet or (self._pets[0] if self._pets else None)
        parent = self._pets[0] if self._pets else None
        ChatWindow.open_chat(parent, pet=pet)

    def _open_preferences(self) -> None:
        parent = self._pets[0] if self._pets else None
        pet = self._menu_host_pet or (self._pets[0] if self._pets else None)
        had_key = has_openrouter_api_key()
        if not open_preferences_dialog(parent, pet=pet):
            return

        language = get_chat_language()
        has_key = has_openrouter_api_key()
        self._refresh_menu_state()
        ChatWindow.refresh_preferences_state()

        if has_key and not had_key:
            self._tray.showMessage(
                "py-shimeji",
                localized(TRAY_API_KEY_SAVED_MESSAGE_LABELS, language),
                QSystemTrayIcon.MessageIcon.Information,
                5_000,
            )
        elif not has_key and had_key:
            self._tray.showMessage(
                "py-shimeji",
                localized(TRAY_API_KEY_CLEARED_MESSAGE_LABELS, language),
                QSystemTrayIcon.MessageIcon.Information,
                5_000,
            )
        else:
            self._tray.showMessage(
                "py-shimeji",
                localized(TRAY_PREFERENCES_SAVED_MESSAGE_LABELS, language),
                QSystemTrayIcon.MessageIcon.Information,
                5_000,
            )

    def _quit(self) -> None:
        self._tray.hide()
        self._app.quit()
