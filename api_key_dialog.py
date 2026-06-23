"""Dialog for viewing and updating the OpenRouter API key."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import get_openrouter_api_key, has_openrouter_api_key, set_openrouter_api_key
from pet_window import PetWindow


class OpenRouterKeyDialog(QDialog):
    """Let the user save or clear their OpenRouter API key."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cleared = False
        self._setup_window()
        self._build_ui()
        self._refresh_status()

    @property
    def cleared(self) -> bool:
        return self._cleared

    def _setup_window(self) -> None:
        self.setWindowTitle("OpenRouter API key")
        self.setModal(True)
        self.setMinimumWidth(420)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        intro = QLabel(
            "Bubu uses OpenRouter for chat. Your key is stored locally in "
            "<b>.env</b> and is only sent to OpenRouter when you message Bubu."
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(intro)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        key_label = QLabel("API key")
        layout.addWidget(key_label)

        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("sk-or-v1-...")
        self._key_input.setClearButtonEnabled(True)
        layout.addWidget(self._key_input)

        hint = QLabel("Leave blank and click Save to keep the current key.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(hint)

        link = QLabel(
            '<a href="https://openrouter.ai/keys">Get a key at openrouter.ai/keys</a>'
        )
        link.setOpenExternalLinks(True)
        link.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(link)

        button_row = QHBoxLayout()
        self._clear_button = QPushButton("Clear key")
        self._clear_button.clicked.connect(self._clear_key)
        button_row.addWidget(self._clear_button)
        button_row.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_key)
        buttons.rejected.connect(self.reject)
        button_row.addWidget(buttons)
        layout.addLayout(button_row)

    def _refresh_status(self) -> None:
        if has_openrouter_api_key():
            masked = self._masked_key(get_openrouter_api_key())
            self._status_label.setText(f"Status: configured ({masked})")
            self._clear_button.setEnabled(True)
        else:
            self._status_label.setText("Status: not configured")
            self._clear_button.setEnabled(False)

    @staticmethod
    def _masked_key(key: str) -> str:
        if len(key) <= 8:
            return "••••••••"
        return f"{key[:4]}…{key[-4:]}"

    def _save_key(self) -> None:
        new_key = self._key_input.text().strip()
        if new_key:
            set_openrouter_api_key(new_key)
            self._cleared = False
            self.accept()
            return

        if has_openrouter_api_key():
            self.reject()
            return

        self._status_label.setText("Status: enter a key before saving.")
        self._key_input.setFocus()

    def _clear_key(self) -> None:
        set_openrouter_api_key("")
        self._key_input.clear()
        self._cleared = True
        self.accept()


def open_api_key_dialog(
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
) -> bool:
    """
    Show the API key dialog.

    Returns True when the key was saved or cleared.
    """
    if pet is not None:
        pet.begin_chat_hold()
    try:
        dialog = OpenRouterKeyDialog(parent)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    finally:
        if pet is not None:
            pet.end_chat_hold()
