"""System tray icon and context menu for the desktop pet."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from api_key_dialog import open_preferences_dialog
from behavior_settings_dialog import open_behavior_settings_dialog
from chat_window import ChatWindow
from config import (
    FALLBACK_BODY_COLOR,
    FALLBACK_OUTLINE_COLOR,
    MAX_PET_COUNT,
    MIN_PET_COUNT,
    TRAY_API_KEY_CLEARED_MESSAGE_LABELS,
    TRAY_API_KEY_SAVED_MESSAGE_LABELS,
    TRAY_BEHAVIOR_LABELS,
    TRAY_BEHAVIOR_SAVED_MESSAGE_LABELS,
    TRAY_CHANGE_SPRITES_LABELS,
    TRAY_CHAT_LABELS,
    TRAY_CLICK_THROUGH_LABELS,
    TRAY_CLICK_THROUGH_TOOLTIP_LABELS,
    TRAY_HIDE_PET_LABELS,
    TRAY_NO_API_KEY_MESSAGE_LABELS,
    TRAY_NO_API_KEY_TITLE_LABELS,
    TRAY_OUTLOOK_CONNECT_FAILED_MESSAGE_LABELS,
    TRAY_OUTLOOK_CONNECT_FAILED_TITLE_LABELS,
    TRAY_OUTLOOK_CONNECT_LABELS,
    TRAY_OUTLOOK_CONNECTED_MESSAGE_LABELS,
    TRAY_OUTLOOK_DISCONNECTED_MESSAGE_LABELS,
    TRAY_OUTLOOK_DISCONNECT_LABELS,
    TRAY_OUTLOOK_MENU_LABELS,
    TRAY_OUTLOOK_SETTINGS_LABELS,
    TRAY_OUTLOOK_SETTINGS_SAVED_MESSAGE_LABELS,
    TRAY_PAUSE_PETS_LABELS,
    TRAY_PAUSE_PETS_TOOLTIP_LABELS,
    TRAY_PREFERENCE_LABELS,
    TRAY_PREFERENCES_SAVED_MESSAGE_LABELS,
    TRAY_QUIT_LABELS,
    TRAY_SHOW_PET_LABELS,
    TRAY_TOOLTIP_OUTLOOK_UNREAD_LABELS,
    TRAY_TOOLTIP_OUTLOOK_UNAVAILABLE_LABELS,
    get_chat_language,
    get_hotkey_binding,
    get_outlook_enabled,
    get_pet_sprites_dir,
    get_saved_pet_visible,
    get_saved_pets_paused,
    has_openrouter_api_key,
    localized,
    outlook_integration_available,
    outlook_ui_available,
    set_saved_pet_visible,
    set_saved_pets_paused,
)
from hotkeys import GlobalHotkeyManager
from outlook_settings_dialog import open_outlook_settings_dialog
from pet_window import PetWindow
from sprite_picker_dialog import open_sprite_picker_dialog

if TYPE_CHECKING:
    from display import DisplayChangeWatcher
    from outlook_monitor import OutlookMonitor
    from outlook_status import OutlookStatusManager


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

    def __init__(
        self,
        app: QApplication,
        pets: list[PetWindow],
        *,
        exclude_hwnds: set[int] | None = None,
        display_watcher: DisplayChangeWatcher | None = None,
        outlook_status: OutlookStatusManager | None = None,
        outlook_monitor: OutlookMonitor | None = None,
    ) -> None:
        self._app = app
        self._pets = pets
        self._exclude_hwnds = exclude_hwnds if exclude_hwnds is not None else set()
        self._display_watcher = display_watcher
        self._outlook_status = outlook_status
        self._outlook_monitor = outlook_monitor
        self._tray = QSystemTrayIcon(_build_tray_icon(), parent=pets[0] if pets else None)
        self._update_tray_tooltip()

        self._visibility_actions: dict[int, QAction] = {}
        self._change_sprites_actions: dict[int, QAction] = {}
        self._chat_action: QAction | None = None
        self._preferences_action: QAction | None = None
        self._behavior_action: QAction | None = None
        self._outlook_menu: QMenu | None = None
        self._outlook_connect_action: QAction | None = None
        self._outlook_disconnect_action: QAction | None = None
        self._outlook_settings_action: QAction | None = None
        self._pause_pets_action: QAction | None = None
        self._click_through_action: QAction | None = None
        self._quit_action: QAction | None = None
        self._hotkeys = GlobalHotkeyManager(parent=pets[0] if pets else None)

        self._menu = self._build_menu()
        self._menu_host_pet: PetWindow | None = None
        self._menu.aboutToHide.connect(self._on_menu_closed)
        self._tray.setContextMenu(self._menu)
        self._tray.show()

        self._apply_menu_language()
        self._setup_hotkeys()
        if self._outlook_status is not None:
            self._outlook_status.status_changed.connect(self._on_outlook_status_changed)
            self._outlook_status.unread_count_changed.connect(self._on_outlook_unread_changed)

        if not has_openrouter_api_key():
            language = get_chat_language()
            self._tray.showMessage(
                localized(TRAY_NO_API_KEY_TITLE_LABELS, language),
                localized(TRAY_NO_API_KEY_MESSAGE_LABELS, language),
                QSystemTrayIcon.MessageIcon.Information,
                8_000,
            )

    @staticmethod
    def _hotkey_hint(action: str) -> str:
        binding = get_hotkey_binding(action)
        return f" ({binding})" if binding else ""

    def _setup_hotkeys(self) -> None:
        self._hotkeys.register("toggle_pause", self.toggle_motion_paused)
        self._hotkeys.register("toggle_click_through", self.toggle_click_through)
        self._hotkeys.register("toggle_pets_visible", self.toggle_all_pets_visible)
        self._hotkeys.register("open_chat", self._open_chat)
        self._hotkeys.reload()

    def _build_menu(self) -> QMenu:
        menu = QMenu()
        self._visibility_actions.clear()
        self._change_sprites_actions.clear()

        for index, pet in enumerate(self._pets, start=1):
            visible = pet.isVisible()
            action = QAction("", menu)
            action.setCheckable(True)
            action.setChecked(visible)
            action.toggled.connect(self._make_visibility_toggle(pet, action, index))
            menu.addAction(action)
            self._visibility_actions[index] = action

        if self._pets:
            menu.addSeparator()
            for index, pet in enumerate(self._pets, start=1):
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

        self._behavior_action = QAction("", menu)
        self._behavior_action.triggered.connect(self._open_behavior_settings)
        menu.addAction(self._behavior_action)

        if outlook_ui_available() and self._outlook_status is not None:
            menu.addSeparator()
            self._outlook_menu = menu.addMenu("")
            self._outlook_connect_action = self._outlook_menu.addAction("")
            self._outlook_connect_action.triggered.connect(self._connect_outlook)
            self._outlook_disconnect_action = self._outlook_menu.addAction("")
            self._outlook_disconnect_action.triggered.connect(self._disconnect_outlook)
            self._outlook_settings_action = self._outlook_menu.addAction("")
            self._outlook_settings_action.triggered.connect(self._open_outlook_settings)

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

        return menu

    def _replace_menu(self) -> None:
        old_menu = self._menu
        self._menu = self._build_menu()
        self._menu.aboutToHide.connect(self._on_menu_closed)
        self._tray.setContextMenu(self._menu)
        if old_menu is not None:
            old_menu.deleteLater()

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

        if self._chat_action is not None:
            self._chat_action.setText(localized(TRAY_CHAT_LABELS, lang))
        if self._preferences_action is not None:
            self._preferences_action.setText(localized(TRAY_PREFERENCE_LABELS, lang))
        if self._behavior_action is not None:
            self._behavior_action.setText(localized(TRAY_BEHAVIOR_LABELS, lang))
        if self._outlook_menu is not None:
            self._outlook_menu.setTitle(localized(TRAY_OUTLOOK_MENU_LABELS, lang))
        if self._outlook_connect_action is not None:
            self._outlook_connect_action.setText(localized(TRAY_OUTLOOK_CONNECT_LABELS, lang))
        if self._outlook_disconnect_action is not None:
            self._outlook_disconnect_action.setText(
                localized(TRAY_OUTLOOK_DISCONNECT_LABELS, lang)
            )
        if self._outlook_settings_action is not None:
            self._outlook_settings_action.setText(
                localized(TRAY_OUTLOOK_SETTINGS_LABELS, lang)
            )
        if self._pause_pets_action is not None:
            self._pause_pets_action.setText(localized(TRAY_PAUSE_PETS_LABELS, lang))
            self._pause_pets_action.setToolTip(
                localized(TRAY_PAUSE_PETS_TOOLTIP_LABELS, lang)
                + self._hotkey_hint("toggle_pause")
            )
        if self._click_through_action is not None:
            self._click_through_action.setText(localized(TRAY_CLICK_THROUGH_LABELS, lang))
            self._click_through_action.setToolTip(
                localized(TRAY_CLICK_THROUGH_TOOLTIP_LABELS, lang)
                + self._hotkey_hint("toggle_click_through")
            )
        if self._quit_action is not None:
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

        if self._click_through_action is not None:
            click_through = bool(self._pets) and all(pet.click_through for pet in self._pets)
            self._click_through_action.blockSignals(True)
            self._click_through_action.setChecked(click_through)
            self._click_through_action.blockSignals(False)

        if self._pause_pets_action is not None:
            motion_paused = bool(self._pets) and all(pet.motion_paused for pet in self._pets)
            self._pause_pets_action.blockSignals(True)
            self._pause_pets_action.setChecked(motion_paused)
            self._pause_pets_action.blockSignals(False)

        if self._chat_action is not None:
            if has_openrouter_api_key():
                tooltip = ""
            else:
                tooltip = localized(TRAY_NO_API_KEY_MESSAGE_LABELS, language)
            self._chat_action.setToolTip(tooltip + self._hotkey_hint("open_chat"))

        self._refresh_outlook_menu_state()

    def _refresh_outlook_menu_state(self) -> None:
        if self._outlook_status is None:
            return
        connected = self._outlook_status.is_connected
        if self._outlook_connect_action is not None:
            self._outlook_connect_action.setVisible(not connected)
        if self._outlook_disconnect_action is not None:
            self._outlook_disconnect_action.setVisible(connected)

    def _update_tray_tooltip(self, language: str | None = None) -> None:
        lang = language or get_chat_language()
        if self._outlook_status is not None and self._outlook_status.is_connected:
            self._tray.setToolTip(
                localized(TRAY_TOOLTIP_OUTLOOK_UNREAD_LABELS, lang).format(
                    count=self._outlook_status.unread_count
                )
            )
        elif self._outlook_status is not None and get_outlook_enabled():
            self._tray.setToolTip(
                localized(TRAY_TOOLTIP_OUTLOOK_UNAVAILABLE_LABELS, lang)
            )
        else:
            self._tray.setToolTip("py-shimeji")

    def show_outlook_tray_message(self, title: str, body: str) -> None:
        self._tray.showMessage(
            title,
            body,
            QSystemTrayIcon.MessageIcon.Information,
            8_000,
        )

    def _on_outlook_status_changed(self) -> None:
        self._refresh_outlook_menu_state()
        self._update_tray_tooltip()

    def _on_outlook_unread_changed(self, _count: int) -> None:
        self._update_tray_tooltip()

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

    def toggle_click_through(self) -> None:
        current = bool(self._pets) and all(pet.click_through for pet in self._pets)
        new_state = not current
        self._set_click_through(new_state)
        if self._click_through_action is not None:
            self._click_through_action.blockSignals(True)
            self._click_through_action.setChecked(new_state)
            self._click_through_action.blockSignals(False)

    def toggle_motion_paused(self) -> None:
        current = bool(self._pets) and all(pet.motion_paused for pet in self._pets)
        new_state = not current
        self._set_motion_paused(new_state)
        if self._pause_pets_action is not None:
            self._pause_pets_action.blockSignals(True)
            self._pause_pets_action.setChecked(new_state)
            self._pause_pets_action.blockSignals(False)

    def toggle_all_pets_visible(self) -> None:
        if not self._pets:
            return
        show = not any(pet.isVisible() for pet in self._pets)
        language = get_chat_language()
        for index, pet in enumerate(self._pets, start=1):
            pet.setVisible(show)
            set_saved_pet_visible(index - 1, show)
            action = self._visibility_actions.get(index)
            if action is not None:
                action.blockSignals(True)
                action.setChecked(show)
                action.setText(self._pet_visibility_label(index, show, language))
                action.blockSignals(False)

    def _sync_peer_pets(self) -> None:
        total = len(self._pets)
        for index, pet in enumerate(self._pets):
            pet.set_total_pet_count(total)
            pet.set_peer_pets(
                [other for other_index, other in enumerate(self._pets) if other_index != index]
            )

    def apply_pet_count(self, target: int) -> None:
        """Add or remove pets to match *target* without restarting."""
        target = max(MIN_PET_COUNT, min(MAX_PET_COUNT, target))
        click_through = bool(self._pets) and all(pet.click_through for pet in self._pets)
        motion_paused = bool(self._pets) and all(pet.motion_paused for pet in self._pets)

        while len(self._pets) < target:
            index = len(self._pets)
            pet = PetWindow(
                pet_index=index,
                pet_count=target,
                exclude_hwnds=self._exclude_hwnds,
                sprites_dir=get_pet_sprites_dir(index),
            )
            pet.set_click_through(click_through)
            pet.set_motion_paused(motion_paused)
            pet.set_context_menu_handler(self.show_context_menu)
            pet.apply_behavior_settings()
            visible = get_saved_pet_visible(index)
            if visible is None:
                visible = pet.has_sprites
            if visible:
                pet.show()
            self._pets.append(pet)

        while len(self._pets) > target:
            pet = self._pets.pop()
            pet.hide()
            pet.deleteLater()

        self._sync_peer_pets()
        if self._display_watcher is not None:
            self._display_watcher.set_pets(self._pets)
        self._replace_menu()
        self._apply_menu_language()

    def _open_chat(self) -> None:
        pet = self._menu_host_pet or (self._pets[0] if self._pets else None)
        parent = self._pets[0] if self._pets else None
        ChatWindow.open_chat(parent, pet=pet)

    def _open_behavior_settings(self) -> None:
        parent = self._pets[0] if self._pets else None
        pet = self._menu_host_pet or (self._pets[0] if self._pets else None)
        dialog = open_behavior_settings_dialog(parent, pet=pet)
        if dialog is None:
            return

        for existing_pet in self._pets:
            existing_pet.apply_behavior_settings()

        if dialog.pet_count != len(self._pets):
            self.apply_pet_count(dialog.pet_count)

        language = get_chat_language()
        self._refresh_menu_state()
        self._tray.showMessage(
            "py-shimeji",
            localized(TRAY_BEHAVIOR_SAVED_MESSAGE_LABELS, language),
            QSystemTrayIcon.MessageIcon.Information,
            5_000,
        )

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

    def _connect_outlook(self) -> None:
        if self._outlook_status is None:
            return
        language = get_chat_language()
        if self._outlook_status.connect_outlook():
            email = self._outlook_status.email or "(unknown)"
            if self._outlook_monitor is not None:
                self._outlook_monitor.start()
            self._refresh_menu_state()
            self._tray.showMessage(
                "py-shimeji",
                localized(TRAY_OUTLOOK_CONNECTED_MESSAGE_LABELS, language).format(
                    email=email
                ),
                QSystemTrayIcon.MessageIcon.Information,
                5_000,
            )
            return

        self._refresh_menu_state()
        self._tray.showMessage(
            localized(TRAY_OUTLOOK_CONNECT_FAILED_TITLE_LABELS, language),
            localized(TRAY_OUTLOOK_CONNECT_FAILED_MESSAGE_LABELS, language),
            QSystemTrayIcon.MessageIcon.Warning,
            8_000,
        )

    def _disconnect_outlook(self) -> None:
        if self._outlook_status is None:
            return
        if self._outlook_monitor is not None:
            self._outlook_monitor.stop()
        self._outlook_status.disconnect_outlook()
        language = get_chat_language()
        self._refresh_menu_state()
        self._tray.showMessage(
            "py-shimeji",
            localized(TRAY_OUTLOOK_DISCONNECTED_MESSAGE_LABELS, language),
            QSystemTrayIcon.MessageIcon.Information,
            5_000,
        )

    def _open_outlook_settings(self) -> None:
        parent = self._pets[0] if self._pets else None
        pet = self._menu_host_pet or (self._pets[0] if self._pets else None)
        dialog = open_outlook_settings_dialog(
            parent,
            pet=pet,
            outlook_status=self._outlook_status,
            outlook_monitor=self._outlook_monitor,
        )
        if dialog is None:
            return
        language = get_chat_language()
        self._refresh_menu_state()
        self._tray.showMessage(
            "py-shimeji",
            localized(TRAY_OUTLOOK_SETTINGS_SAVED_MESSAGE_LABELS, language),
            QSystemTrayIcon.MessageIcon.Information,
            5_000,
        )

    def _quit(self) -> None:
        self._hotkeys.shutdown()
        if self._outlook_monitor is not None:
            self._outlook_monitor.shutdown()
        if self._outlook_status is not None:
            self._outlook_status.shutdown()
        self._tray.hide()
        self._app.quit()
