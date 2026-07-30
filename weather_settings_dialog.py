"""Dialog for Hong Kong Observatory weather notification settings."""

from __future__ import annotations

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config import (
    CHAT_WINDOW_GAP_PX,
    HKO_WEATHER_PLACES,
    WEATHER_DIALOG_CANCEL_LABELS,
    WEATHER_DIALOG_ENABLED_HINT_LABELS,
    WEATHER_DIALOG_ENABLED_LABELS,
    WEATHER_DIALOG_INTRO_LABELS,
    WEATHER_DIALOG_LOCATION_HINT_LABELS,
    WEATHER_DIALOG_LOCATION_LABELS,
    WEATHER_DIALOG_NOTIFY_PET_FIRST_VISIBLE_LABELS,
    WEATHER_DIALOG_NOTIFY_PET_HINT_LABELS,
    WEATHER_DIALOG_NOTIFY_PET_LABELS,
    WEATHER_DIALOG_NOTIFY_PET_NUMBER_LABELS,
    WEATHER_DIALOG_NOTIFY_WHEN_PAUSED_HINT_LABELS,
    WEATHER_DIALOG_NOTIFY_WHEN_PAUSED_LABELS,
    WEATHER_DIALOG_SAVE_LABELS,
    WEATHER_DIALOG_TITLE_LABELS,
    WEATHER_DIALOG_WARNING_INTERVAL_HINT_LABELS,
    WEATHER_DIALOG_WARNING_INTERVAL_LABELS,
    WEATHER_NOTIFY_PET_FIRST_VISIBLE,
    WEATHER_WARNING_POLL_INTERVAL_SEC_MAX,
    WEATHER_WARNING_POLL_INTERVAL_SEC_MIN,
    get_chat_language,
    get_saved_pet_count,
    get_weather_enabled,
    get_weather_location,
    get_weather_notify_pet_index,
    get_weather_notify_when_paused,
    get_weather_warning_poll_interval_sec,
    localized,
    set_weather_settings,
)
from dialog_theme import DIALOG_HINT_STYLE, apply_light_dialog_theme
from pet_window import PetWindow


class WeatherSettingsDialog(QDialog):
    """Configure HKO weather reports and warning alerts."""

    def __init__(
        self,
        parent: QWidget | None = None,
        pet: PetWindow | None = None,
        *,
        weather_monitor: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet = pet
        self._weather_monitor = weather_monitor
        self._positioned = False
        self._ui_language = get_chat_language()
        self._setup_window()
        self._build_ui()
        self._load_values()
        self._apply_language(self._ui_language)

    def _setup_window(self) -> None:
        self.setModal(True)
        self.setMinimumWidth(440)
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

        self._intro_label = QLabel("", self)
        self._intro_label.setWordWrap(True)
        layout.addWidget(self._intro_label)

        self._enabled_check = QCheckBox("", self)
        layout.addWidget(self._enabled_check)
        self._enabled_hint = QLabel("", self)
        self._enabled_hint.setWordWrap(True)
        self._enabled_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._enabled_hint)

        self._location_label = QLabel("", self)
        layout.addWidget(self._location_label)
        self._location_combo = QComboBox(self)
        self._location_combo.addItems(list(HKO_WEATHER_PLACES))
        layout.addWidget(self._location_combo)
        self._location_hint = QLabel("", self)
        self._location_hint.setWordWrap(True)
        self._location_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._location_hint)

        self._warning_interval_label = QLabel("", self)
        layout.addWidget(self._warning_interval_label)
        self._warning_interval_spin = QSpinBox(self)
        self._warning_interval_spin.setRange(
            WEATHER_WARNING_POLL_INTERVAL_SEC_MIN,
            WEATHER_WARNING_POLL_INTERVAL_SEC_MAX,
        )
        self._warning_interval_spin.setSingleStep(60)
        self._warning_interval_spin.setSuffix(" s")
        layout.addWidget(self._warning_interval_spin)
        self._warning_interval_hint = QLabel("", self)
        self._warning_interval_hint.setWordWrap(True)
        self._warning_interval_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._warning_interval_hint)

        self._notify_pet_label = QLabel("", self)
        layout.addWidget(self._notify_pet_label)
        self._notify_pet_combo = QComboBox(self)
        layout.addWidget(self._notify_pet_combo)
        self._notify_pet_hint = QLabel("", self)
        self._notify_pet_hint.setWordWrap(True)
        self._notify_pet_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._notify_pet_hint)

        self._notify_when_paused_check = QCheckBox("", self)
        layout.addWidget(self._notify_when_paused_check)
        self._notify_when_paused_hint = QLabel("", self)
        self._notify_when_paused_hint.setWordWrap(True)
        self._notify_when_paused_hint.setStyleSheet(DIALOG_HINT_STYLE)
        layout.addWidget(self._notify_when_paused_hint)

        buttons = QDialogButtonBox(parent=self)
        self._save_button = buttons.addButton("", QDialogButtonBox.ButtonRole.AcceptRole)
        self._cancel_button = buttons.addButton("", QDialogButtonBox.ButtonRole.RejectRole)
        self._save_button.clicked.connect(self._save)
        self._cancel_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self) -> None:
        self._enabled_check.setChecked(get_weather_enabled())
        location = get_weather_location()
        location_index = self._location_combo.findText(location)
        if location_index >= 0:
            self._location_combo.setCurrentIndex(location_index)
        self._warning_interval_spin.setValue(get_weather_warning_poll_interval_sec())
        self._notify_when_paused_check.setChecked(get_weather_notify_when_paused())
        self._rebuild_notify_pet_combo(get_weather_notify_pet_index())

    def _rebuild_notify_pet_combo(self, selected_index: int) -> None:
        self._notify_pet_combo.clear()
        self._notify_pet_combo.addItem(
            localized(WEATHER_DIALOG_NOTIFY_PET_FIRST_VISIBLE_LABELS, self._ui_language),
            WEATHER_NOTIFY_PET_FIRST_VISIBLE,
        )
        for index in range(1, max(1, get_saved_pet_count()) + 1):
            self._notify_pet_combo.addItem(
                localized(WEATHER_DIALOG_NOTIFY_PET_NUMBER_LABELS, self._ui_language).format(
                    index=index
                ),
                index - 1,
            )
        combo_index = self._notify_pet_combo.findData(selected_index)
        if combo_index >= 0:
            self._notify_pet_combo.setCurrentIndex(combo_index)

    def _apply_language(self, language: str) -> None:
        self.setWindowTitle(localized(WEATHER_DIALOG_TITLE_LABELS, language))
        self._intro_label.setText(localized(WEATHER_DIALOG_INTRO_LABELS, language))
        self._enabled_check.setText(localized(WEATHER_DIALOG_ENABLED_LABELS, language))
        self._enabled_hint.setText(localized(WEATHER_DIALOG_ENABLED_HINT_LABELS, language))
        self._location_label.setText(localized(WEATHER_DIALOG_LOCATION_LABELS, language))
        self._location_hint.setText(localized(WEATHER_DIALOG_LOCATION_HINT_LABELS, language))
        self._warning_interval_label.setText(
            localized(WEATHER_DIALOG_WARNING_INTERVAL_LABELS, language)
        )
        self._warning_interval_hint.setText(
            localized(WEATHER_DIALOG_WARNING_INTERVAL_HINT_LABELS, language)
        )
        self._notify_pet_label.setText(localized(WEATHER_DIALOG_NOTIFY_PET_LABELS, language))
        self._notify_pet_hint.setText(localized(WEATHER_DIALOG_NOTIFY_PET_HINT_LABELS, language))
        self._notify_when_paused_check.setText(
            localized(WEATHER_DIALOG_NOTIFY_WHEN_PAUSED_LABELS, language)
        )
        self._notify_when_paused_hint.setText(
            localized(WEATHER_DIALOG_NOTIFY_WHEN_PAUSED_HINT_LABELS, language)
        )
        self._save_button.setText(localized(WEATHER_DIALOG_SAVE_LABELS, language))
        self._cancel_button.setText(localized(WEATHER_DIALOG_CANCEL_LABELS, language))
        self._rebuild_notify_pet_combo(self._notify_pet_combo.currentData())

    def _save(self) -> None:
        notify_index = self._notify_pet_combo.currentData()
        if notify_index is None:
            notify_index = WEATHER_NOTIFY_PET_FIRST_VISIBLE
        set_weather_settings(
            enabled=self._enabled_check.isChecked(),
            location=self._location_combo.currentText(),
            warning_poll_interval_sec=self._warning_interval_spin.value(),
            notify_pet_index=int(notify_index),
            notify_when_paused=self._notify_when_paused_check.isChecked(),
        )
        restart = getattr(self._weather_monitor, "restart", None)
        if callable(restart):
            restart()
        start = getattr(self._weather_monitor, "start", None)
        stop = getattr(self._weather_monitor, "stop", None)
        if self._enabled_check.isChecked() and callable(start):
            start()
        elif not self._enabled_check.isChecked() and callable(stop):
            stop()
        self.accept()


def open_weather_settings_dialog(
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
    *,
    weather_monitor: object | None = None,
) -> bool:
    dialog = WeatherSettingsDialog(
        parent,
        pet,
        weather_monitor=weather_monitor,
    )
    return dialog.exec() == QDialog.DialogCode.Accepted
