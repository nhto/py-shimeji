"""React to monitor and workspace geometry changes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QGuiApplication, QScreen

if TYPE_CHECKING:
    from pet_window import PetWindow


class DisplayChangeWatcher(QObject):
    """Notify all pets when screens are added, removed, or resized."""

    def __init__(
        self,
        pets: list[PetWindow],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pets = pets
        app = QGuiApplication.instance()
        if app is None:
            return

        app.screenAdded.connect(self._on_screen_added)
        app.screenRemoved.connect(self._on_screen_removed)
        app.primaryScreenChanged.connect(self._on_display_changed)
        for screen in app.screens():
            self._on_screen_added(screen)

    def _on_screen_added(self, screen: QScreen) -> None:
        screen.geometryChanged.connect(self._on_display_changed)
        screen.availableGeometryChanged.connect(self._on_display_changed)
        self._on_display_changed()

    def _on_screen_removed(self, screen: QScreen) -> None:
        try:
            screen.geometryChanged.disconnect(self._on_display_changed)
        except TypeError:
            pass
        try:
            screen.availableGeometryChanged.disconnect(self._on_display_changed)
        except TypeError:
            pass
        self._on_display_changed()

    def _on_display_changed(self, *_args: object) -> None:
        for pet in self._pets:
            pet.handle_display_changed()
