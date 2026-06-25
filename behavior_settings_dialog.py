"""Dialog for pet movement, chase, count, and ambient speech settings."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import (
    BEHAVIOR_CANCEL_LABELS,
    BEHAVIOR_CHASE_HINT_LABELS,
    BEHAVIOR_CHASE_LABELS,
    BEHAVIOR_DIALOG_INTRO_LABELS,
    BEHAVIOR_DIALOG_TITLE_LABELS,
    BEHAVIOR_AMBIENT_HINT_LABELS,
    BEHAVIOR_AMBIENT_LABELS,
    BEHAVIOR_PET_COUNT_HINT_LABELS,
    BEHAVIOR_PET_COUNT_LABELS,
    BEHAVIOR_SAVE_LABELS,
    BEHAVIOR_SPEED_HINT_LABELS,
    BEHAVIOR_SPEED_LABELS,
    BEHAVIOR_SPEED_PERCENT_MAX,
    BEHAVIOR_SPEED_PERCENT_MIN,
    CHAT_WINDOW_GAP_PX,
    MAX_PET_COUNT,
    MIN_PET_COUNT,
    get_ambient_speech_enabled,
    get_chat_language,
    get_cursor_chase_chance,
    get_saved_pet_count,
    get_speed_percent,
    localized,
    set_behavior_settings,
)
from dialog_theme import DIALOG_HINT_STYLE, apply_light_dialog_theme
from pet_window import PetWindow


class BehaviorSettingsDialog(QDialog):
    """Adjust movement speed, cursor chase, pet count, and ambient speech."""

    def __init__(
        self,
        parent: QWidget | None = None,
        pet: PetWindow | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet = pet
        self._positioned = False
        self._ui_language = get_chat_language()
        self._setup_window()
        self._build_ui()
        self._load_values()
        self._apply_language(self._ui_language)

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
        layout.addWidget(self._intro)

        self._speed_label = QLabel()
        layout.addWidget(self._speed_label)
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(
            BEHAVIOR_SPEED_PERCENT_MIN,
            BEHAVIOR_SPEED_PERCENT_MAX,
        )
        self._speed_slider.valueChanged.connect(self._update_speed_label)
        layout.addWidget(self._speed_slider)
        self._speed_hint = QLabel()
        self._speed_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._speed_hint)

        self._chase_label = QLabel()
        layout.addWidget(self._chase_label)
        self._chase_slider = QSlider(Qt.Orientation.Horizontal)
        self._chase_slider.setRange(0, 100)
        self._chase_slider.valueChanged.connect(self._update_chase_label)
        layout.addWidget(self._chase_slider)
        self._chase_hint = QLabel()
        self._chase_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._chase_hint)

        pet_row = QHBoxLayout()
        self._pet_count_label = QLabel()
        pet_row.addWidget(self._pet_count_label)
        self._pet_count_spin = QSpinBox()
        self._pet_count_spin.setRange(MIN_PET_COUNT, MAX_PET_COUNT)
        pet_row.addWidget(self._pet_count_spin)
        pet_row.addStretch()
        layout.addLayout(pet_row)
        self._pet_count_hint = QLabel()
        self._pet_count_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._pet_count_hint)

        self._ambient_checkbox = QCheckBox()
        layout.addWidget(self._ambient_checkbox)
        self._ambient_hint = QLabel()
        self._ambient_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._ambient_hint)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._save_settings)
        self._button_box.rejected.connect(self.reject)
        self._save_button = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        self._cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self._button_box)

    def _load_values(self) -> None:
        self._speed_slider.setValue(get_speed_percent())
        self._chase_slider.setValue(round(get_cursor_chase_chance() * 100))
        self._pet_count_spin.setValue(get_saved_pet_count())
        self._ambient_checkbox.setChecked(get_ambient_speech_enabled())

    def _update_speed_label(self, value: int) -> None:
        self._speed_label.setText(
            localized(BEHAVIOR_SPEED_LABELS, self._ui_language).format(value=value)
        )

    def _update_chase_label(self, value: int) -> None:
        self._chase_label.setText(
            localized(BEHAVIOR_CHASE_LABELS, self._ui_language).format(value=value)
        )

    def _apply_language(self, language: str) -> None:
        self._ui_language = language
        self.setWindowTitle(localized(BEHAVIOR_DIALOG_TITLE_LABELS, language))
        self._intro.setText(localized(BEHAVIOR_DIALOG_INTRO_LABELS, language))
        self._speed_hint.setText(localized(BEHAVIOR_SPEED_HINT_LABELS, language))
        self._chase_hint.setText(localized(BEHAVIOR_CHASE_HINT_LABELS, language))
        self._pet_count_label.setText(localized(BEHAVIOR_PET_COUNT_LABELS, language))
        self._pet_count_hint.setText(
            localized(BEHAVIOR_PET_COUNT_HINT_LABELS, language).format(
                min=MIN_PET_COUNT,
                max=MAX_PET_COUNT,
            )
        )
        self._ambient_checkbox.setText(localized(BEHAVIOR_AMBIENT_LABELS, language))
        self._ambient_hint.setText(localized(BEHAVIOR_AMBIENT_HINT_LABELS, language))
        if self._save_button is not None:
            self._save_button.setText(localized(BEHAVIOR_SAVE_LABELS, language))
        if self._cancel_button is not None:
            self._cancel_button.setText(localized(BEHAVIOR_CANCEL_LABELS, language))
        self._update_speed_label(self._speed_slider.value())
        self._update_chase_label(self._chase_slider.value())

    def _save_settings(self) -> None:
        set_behavior_settings(
            speed_percent=self._speed_slider.value(),
            cursor_chase_chance=self._chase_slider.value() / 100.0,
            pet_count=self._pet_count_spin.value(),
            ambient_speech_enabled=self._ambient_checkbox.isChecked(),
        )
        self.accept()

    @property
    def pet_count(self) -> int:
        return self._pet_count_spin.value()


def open_behavior_settings_dialog(
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
) -> BehaviorSettingsDialog | None:
    """
    Show the behavior settings dialog.

    Returns the dialog when saved, or None when cancelled.
    """
    if pet is not None:
        pet.begin_menu_hold()
    try:
        dialog = BehaviorSettingsDialog(parent, pet=pet)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog
    finally:
        if pet is not None:
            pet.end_menu_hold()
