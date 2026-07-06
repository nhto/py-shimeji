"""Entry point for the Shimeji desktop pet application."""

from __future__ import annotations

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from config import (
    get_outlook_enabled,
    get_pet_sprites_dir,
    get_saved_pet_visible,
    get_saved_pets_paused,
    get_saved_pet_count,
    outlook_ui_available,
)
from display import DisplayChangeWatcher
from pet_window import PetWindow
from surfaces import SharedSurfaceCoordinator
from tray import SystemTray


def main() -> int:
    """Create the Qt application and show the pet windows."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # Ensure the global application font has a valid point size.
    # Some platforms/theme setups can default to pointSize -1, which triggers
    # the runtime warning "QFont::setPointSize: Point size <= 0 (-1)".
    font = app.font()
    if font.pointSize() <= 0:
        font.setPointSize(10)
        app.setFont(font)

    exclude_hwnds: set[int] = set()
    pet_count = max(1, get_saved_pet_count())
    surface_coordinator = SharedSurfaceCoordinator(exclude_hwnds)
    pets = [
        PetWindow(
            pet_index=index,
            pet_count=pet_count,
            exclude_hwnds=exclude_hwnds,
            sprites_dir=get_pet_sprites_dir(index),
            surface_coordinator=surface_coordinator,
        )
        for index in range(pet_count)
    ]
    surface_coordinator.set_pets(pets)
    surface_coordinator.refresh()
    for index, pet in enumerate(pets):
        pet.set_peer_pets([other for other_index, other in enumerate(pets) if other_index != index])
        pet.apply_behavior_settings()

    if get_saved_pets_paused():
        for pet in pets:
            pet.set_motion_paused(True)

    for index, pet in enumerate(pets):
        visible = get_saved_pet_visible(index)
        if visible is None:
            visible = pet.has_sprites
        if visible:
            pet.show()

    display_watcher = DisplayChangeWatcher(
        pets,
        surface_coordinator=surface_coordinator,
        parent=pets[0] if pets else None,
    )

    outlook_status = None
    outlook_monitor = None
    if outlook_ui_available():
        from outlook_monitor import OutlookMonitor
        from outlook_status import OutlookStatusManager

        outlook_status = OutlookStatusManager(parent=pets[0] if pets else None)
        outlook_monitor = OutlookMonitor(
            pets,
            outlook_status=outlook_status,
            parent=pets[0] if pets else None,
        )

    if QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)
        tray = SystemTray(
            app,
            pets,
            exclude_hwnds=exclude_hwnds,
            display_watcher=display_watcher,
            surface_coordinator=surface_coordinator,
            outlook_status=outlook_status,
            outlook_monitor=outlook_monitor,
        )
        if outlook_monitor is not None:
            outlook_monitor.set_tray_notifier(tray.show_outlook_tray_message)
        for pet in pets:
            pet.set_context_menu_handler(tray.show_context_menu)
        if outlook_status is not None and get_outlook_enabled():
            outlook_status.try_restore_connection()
        if outlook_monitor is not None and get_outlook_enabled():
            outlook_monitor.start()
    elif not any(pet.isVisible() for pet in pets):
        return 0

    def _shutdown_outlook() -> None:
        if outlook_monitor is not None:
            outlook_monitor.shutdown()
        if outlook_status is not None:
            outlook_status.shutdown()

    app.aboutToQuit.connect(_shutdown_outlook)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
