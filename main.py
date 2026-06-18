"""Entry point for the Shimeji desktop pet application."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from pet_window import PetWindow
from tray import SystemTray


def main() -> int:
    """Create the Qt application and show the pet window."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    pet = PetWindow()
    pet.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        SystemTray(app, pet)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
