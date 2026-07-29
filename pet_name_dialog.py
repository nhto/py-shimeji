"""Dialog for changing the desktop pet's display name."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from config import (
    CHAT_WINDOW_GAP_PX,
    PET_NAME_DIALOG_CANCEL_LABELS,
    PET_NAME_DIALOG_FIELD_LABELS,
    PET_NAME_DIALOG_INTRO_LABELS,
    PET_NAME_DIALOG_SAVE_LABELS,
    PET_NAME_DIALOG_TITLE_LABELS,
    get_chat_language,
    get_pet_name,
    localized,
    set_pet_name,
)
from dialog_theme import DIALOG_HINT_STYLE, apply_light_dialog_theme
from pet_window import PetWindow


class PetNameDialog(QDialog):
    """Let the user choose a custom name for the desktop pet."""

    def __init__(
        self,
        parent: QWidget | None = None,
        pet: PetWindow | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet = pet
        self._positioned = False
        self._initial_name = get_pet_name()
        self._saved_name = self._initial_name
        self._ui_language = get_chat_language()
        self._setup_window()
        self._build_ui()
        self._apply_language(self._ui_language)

    @property
    def saved_name(self) -> str:
        return self._saved_name

    @property
    def name_changed(self) -> bool:
        return self._saved_name != self._initial_name

    def _setup_window(self) -> None:
        self.setModal(True)
        self.setMinimumWidth(360)
        apply_light_dialog_theme(self)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if not self._positioned:
            self._position_above_pet(self._pet)
            self._positioned = True

    def _position_above_pet(self, pet: PetWindow | None) -> None:
        screen = None
        anchor = pet.frameGeometry().center() if pet is not None and pet.isVisible() else None

        if anchor is not None:
            screen = QGuiApplication.screenAt(anchor)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        width = self.width()
        height = self.height()

        if anchor is not None and pet is not None:
            pet_rect = pet.frameGeometry()
            x = pet_rect.center().x() - width // 2
            y = pet_rect.top() - height - CHAT_WINDOW_GAP_PX
        else:
            x = available.center().x() - width // 2
            y = available.center().y() - height // 2

        x = max(available.left(), min(x, available.right() - width + 1))
        y = max(available.top(), min(y, available.bottom() - height + 1))
        self.move(x, y)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._intro = QLabel()
        self._intro.setWordWrap(True)
        self._intro.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._intro)

        self._name_label = QLabel()
        layout.addWidget(self._name_label)

        self._name_input = QLineEdit()
        self._name_input.setText(self._initial_name)
        self._name_input.setClearButtonEnabled(True)
        self._name_input.returnPressed.connect(self._save_name)
        layout.addWidget(self._name_input)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._save_name)
        self._button_box.rejected.connect(self.reject)
        self._save_button = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        self._cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self._button_box)

    def _apply_language(self, language: str) -> None:
        self.setWindowTitle(localized(PET_NAME_DIALOG_TITLE_LABELS, language))
        self._intro.setText(localized(PET_NAME_DIALOG_INTRO_LABELS, language))
        self._name_label.setText(localized(PET_NAME_DIALOG_FIELD_LABELS, language))
        if self._save_button is not None:
            self._save_button.setText(localized(PET_NAME_DIALOG_SAVE_LABELS, language))
        if self._cancel_button is not None:
            self._cancel_button.setText(localized(PET_NAME_DIALOG_CANCEL_LABELS, language))

    def _save_name(self) -> None:
        self._saved_name = set_pet_name(self._name_input.text())
        self._name_input.setText(self._saved_name)
        self.accept()


def open_pet_name_dialog(
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
) -> PetNameDialog | None:
    """Show the pet name dialog and return it when saved, otherwise None."""
    if pet is not None:
        pet.begin_chat_hold()
    try:
        dialog = PetNameDialog(parent, pet=pet)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog
    finally:
        if pet is not None:
            pet.end_chat_hold()
