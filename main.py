"""Entry point for the Shimeji desktop pet application."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from config import MAX_PETS, get_pet_sprites_dir
from pet_window import PetWindow
from tray import SystemTray


def main() -> int:
    """Create the Qt application and show the pet windows."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

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
    for pet in pets:
        if pet.has_sprites:
            pet.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)
        SystemTray(app, pets)
    elif not any(pet.isVisible() for pet in pets):
        return 0

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
