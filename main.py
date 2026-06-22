"""Entry point for the Shimeji desktop pet application."""

from __future__ import annotations

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from config import MAX_PETS, get_pet_sprites_dir
from display import DisplayChangeWatcher
from pet_window import PetWindow
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
    pet_count = max(1, MAX_PETS)
    pets = [
        PetWindow(
            pet_index=index,
            pet_count=pet_count,
            exclude_hwnds=exclude_hwnds,
            sprites_dir=get_pet_sprites_dir(index),
        )
        for index in range(pet_count)
    ]
    for index, pet in enumerate(pets):
        pet.set_peer_pets([other for other_index, other in enumerate(pets) if other_index != index])
        if pet.has_sprites:
            pet.show()

    DisplayChangeWatcher(pets, parent=pets[0] if pets else None)

    if QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)
        tray = SystemTray(app, pets)
        for pet in pets:
            pet.set_context_menu_handler(tray.show_context_menu)
    elif not any(pet.isVisible() for pet in pets):
        return 0

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
