"""Entry point for the Shimeji desktop pet application."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from pet_window import PetWindow


def main() -> int:
    """Create the Qt application and show the pet window."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    pet = PetWindow()
    pet.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
