"""Dialog for application preferences (OpenRouter and language)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import (
    CHAT_WINDOW_GAP_PX,
    PREFERENCES_API_KEY_LABELS,
    PREFERENCES_CANCEL_LABELS,
    PREFERENCES_CONTEXT_ACTIVE_WINDOW_LABELS,
    PREFERENCES_CONTEXT_CLIPBOARD_LABELS,
    PREFERENCES_CONTEXT_HEADING_LABELS,
    PREFERENCES_CONTEXT_HINT_LABELS,
    PREFERENCES_CLEAR_KEY_LABELS,
    PREFERENCES_KEY_HINT_LABELS,
    PREFERENCES_KEY_LINK_LABELS,
    PREFERENCES_LANGUAGE_HEADING_LABELS,
    PREFERENCES_LANGUAGE_HINT_LABELS,
    PREFERENCES_OPENROUTER_HEADING_LABELS,
    PREFERENCES_OPENROUTER_INTRO_LABELS,
    PREFERENCES_SAVE_LABELS,
    PREFERENCES_STATUS_CONFIGURED_LABELS,
    PREFERENCES_STATUS_ENTER_KEY_LABELS,
    PREFERENCES_STATUS_NOT_CONFIGURED_LABELS,
    PREFERENCES_TITLE_LABELS,
    get_chat_language,
    get_chat_context_include_active_window,
    get_chat_context_include_clipboard,
    get_openrouter_api_key,
    has_openrouter_api_key,
    language_option_labels,
    localized,
    localized_with_pet,
    set_chat_language,
    set_chat_context_include_active_window,
    set_chat_context_include_clipboard,
    set_openrouter_api_key,
)
from dialog_theme import DIALOG_HEADING_STYLE, DIALOG_HINT_STYLE, apply_light_dialog_theme
from pet_window import PetWindow


class PreferencesDialog(QDialog):
    """Let the user manage OpenRouter settings and reply language."""

    def __init__(
        self,
        parent: QWidget | None = None,
        pet: PetWindow | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet = pet
        self._positioned = False
        self._cleared = False
        self._initial_language = get_chat_language()
        self._initial_context_active_window = get_chat_context_include_active_window()
        self._initial_context_clipboard = get_chat_context_include_clipboard()
        self._ui_language = self._initial_language
        self._setup_window()
        self._build_ui()
        self._apply_language(self._ui_language)
        self._refresh_status()

    @property
    def cleared(self) -> bool:
        return self._cleared

    @property
    def language_changed(self) -> bool:
        language_id = self._language_picker.currentData()
        return isinstance(language_id, str) and language_id != self._initial_language

    @property
    def context_settings_changed(self) -> bool:
        return (
            self._context_active_window_check.isChecked()
            != self._initial_context_active_window
            or self._context_clipboard_check.isChecked()
            != self._initial_context_clipboard
        )

    def _setup_window(self) -> None:
        self.setModal(True)
        self.setMinimumWidth(420)
        apply_light_dialog_theme(self)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if not self._positioned:
            self._position_above_pet(self._pet)
            self._positioned = True

    def _position_above_pet(self, pet: PetWindow | None) -> None:
        """Place the dialog centered above the shimeji."""
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

        self._openrouter_heading = QLabel()
        self._openrouter_heading.setStyleSheet(DIALOG_HEADING_STYLE)
        layout.addWidget(self._openrouter_heading)

        self._intro = QLabel()
        self._intro.setWordWrap(True)
        self._intro.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._intro)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._key_label = QLabel()
        layout.addWidget(self._key_label)

        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("sk-or-v1-...")
        self._key_input.setClearButtonEnabled(True)
        layout.addWidget(self._key_input)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._hint)

        self._link = QLabel()
        self._link.setOpenExternalLinks(True)
        self._link.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._link)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self._language_heading = QLabel()
        self._language_heading.setStyleSheet(DIALOG_HEADING_STYLE)
        layout.addWidget(self._language_heading)

        self._language_hint = QLabel()
        self._language_hint.setWordWrap(True)
        self._language_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._language_hint)

        self._language_picker = QComboBox()
        self._language_picker.currentIndexChanged.connect(self._on_language_picker_changed)
        layout.addWidget(self._language_picker)

        context_separator = QFrame()
        context_separator.setFrameShape(QFrame.Shape.HLine)
        context_separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(context_separator)

        self._context_heading = QLabel()
        self._context_heading.setStyleSheet(DIALOG_HEADING_STYLE)
        layout.addWidget(self._context_heading)

        self._context_hint = QLabel()
        self._context_hint.setWordWrap(True)
        self._context_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._context_hint)

        self._context_active_window_check = QCheckBox()
        layout.addWidget(self._context_active_window_check)

        self._context_clipboard_check = QCheckBox()
        layout.addWidget(self._context_clipboard_check)

        button_row = QHBoxLayout()
        self._clear_button = QPushButton()
        self._clear_button.clicked.connect(self._clear_key)
        button_row.addWidget(self._clear_button)
        button_row.addStretch()

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._save_preferences)
        self._button_box.rejected.connect(self.reject)
        self._save_button = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        self._cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        button_row.addWidget(self._button_box)
        layout.addLayout(button_row)

    def _on_language_picker_changed(self, index: int) -> None:
        if index < 0:
            return
        language_id = self._language_picker.itemData(index)
        if not isinstance(language_id, str):
            return
        self._ui_language = language_id
        self._apply_language(language_id)

    def _populate_language_picker(self, ui_language: str) -> None:
        selected = self._language_picker.currentData()
        if not isinstance(selected, str):
            selected = self._initial_language
        self._language_picker.blockSignals(True)
        self._language_picker.clear()
        for lang_id, label in language_option_labels(ui_language):
            self._language_picker.addItem(label, lang_id)
        index = self._language_picker.findData(selected)
        if index >= 0:
            self._language_picker.setCurrentIndex(index)
        self._language_picker.blockSignals(False)
        self._context_active_window_check.setChecked(
            get_chat_context_include_active_window()
        )
        self._context_clipboard_check.setChecked(get_chat_context_include_clipboard())

    def _apply_language(self, language: str) -> None:
        self.setWindowTitle(localized(PREFERENCES_TITLE_LABELS, language))
        self._openrouter_heading.setText(
            localized(PREFERENCES_OPENROUTER_HEADING_LABELS, language)
        )
        self._intro.setText(localized_with_pet(PREFERENCES_OPENROUTER_INTRO_LABELS, language))
        self._key_label.setText(localized(PREFERENCES_API_KEY_LABELS, language))
        self._hint.setText(localized(PREFERENCES_KEY_HINT_LABELS, language))
        self._link.setText(localized(PREFERENCES_KEY_LINK_LABELS, language))
        self._language_heading.setText(
            localized(PREFERENCES_LANGUAGE_HEADING_LABELS, language)
        )
        self._language_hint.setText(
            localized_with_pet(PREFERENCES_LANGUAGE_HINT_LABELS, language)
        )
        self._context_heading.setText(
            localized(PREFERENCES_CONTEXT_HEADING_LABELS, language)
        )
        self._context_hint.setText(
            localized(PREFERENCES_CONTEXT_HINT_LABELS, language)
        )
        self._context_active_window_check.setText(
            localized(PREFERENCES_CONTEXT_ACTIVE_WINDOW_LABELS, language)
        )
        self._context_clipboard_check.setText(
            localized(PREFERENCES_CONTEXT_CLIPBOARD_LABELS, language)
        )
        self._clear_button.setText(localized(PREFERENCES_CLEAR_KEY_LABELS, language))
        if self._save_button is not None:
            self._save_button.setText(localized(PREFERENCES_SAVE_LABELS, language))
        if self._cancel_button is not None:
            self._cancel_button.setText(localized(PREFERENCES_CANCEL_LABELS, language))
        self._populate_language_picker(language)
        self._refresh_status()

    def _refresh_status(self) -> None:
        if has_openrouter_api_key():
            masked = self._masked_key(get_openrouter_api_key())
            self._status_label.setText(
                localized(PREFERENCES_STATUS_CONFIGURED_LABELS, self._ui_language).format(
                    masked=masked
                )
            )
            self._clear_button.setEnabled(True)
        else:
            self._status_label.setText(
                localized(PREFERENCES_STATUS_NOT_CONFIGURED_LABELS, self._ui_language)
            )
            self._clear_button.setEnabled(False)

    @staticmethod
    def _masked_key(key: str) -> str:
        if len(key) <= 8:
            return "••••••••"
        return f"{key[:4]}…{key[-4:]}"

    def _save_language(self) -> None:
        language_id = self._language_picker.currentData()
        if isinstance(language_id, str):
            set_chat_language(language_id)

    def _save_context_settings(self) -> None:
        set_chat_context_include_active_window(
            self._context_active_window_check.isChecked()
        )
        set_chat_context_include_clipboard(
            self._context_clipboard_check.isChecked()
        )

    def _save_preferences(self) -> None:
        self._save_language()
        self._save_context_settings()

        new_key = self._key_input.text().strip()
        if new_key:
            set_openrouter_api_key(new_key)
            self._cleared = False
            self.accept()
            return

        if has_openrouter_api_key() or self.language_changed or self.context_settings_changed:
            self.accept()
            return

        self._status_label.setText(
            localized(PREFERENCES_STATUS_ENTER_KEY_LABELS, self._ui_language)
        )
        self._key_input.setFocus()

    def _clear_key(self) -> None:
        set_openrouter_api_key("")
        self._key_input.clear()
        self._cleared = True
        self._save_language()
        self._save_context_settings()
        self.accept()


# Legacy alias for older imports.
OpenRouterKeyDialog = PreferencesDialog


def open_preferences_dialog(
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
) -> bool:
    """
    Show the preferences dialog.

    Returns True when preferences were saved or the API key was cleared.
    """
    if pet is not None:
        pet.begin_chat_hold()
    try:
        dialog = PreferencesDialog(parent, pet=pet)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    finally:
        if pet is not None:
            pet.end_chat_hold()


def open_api_key_dialog(
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
) -> bool:
    """Backward-compatible alias for :func:`open_preferences_dialog`."""
    return open_preferences_dialog(parent, pet=pet)
