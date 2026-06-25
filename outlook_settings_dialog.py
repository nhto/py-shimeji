"""Dialog for Outlook connection status and notification toggles."""

from __future__ import annotations

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import (
    CHAT_WINDOW_GAP_PX,
    OUTLOOK_DIALOG_CALENDAR_HINT_LABELS,
    OUTLOOK_DIALOG_CALENDAR_LABELS,
    OUTLOOK_DIALOG_CANCEL_LABELS,
    OUTLOOK_DIALOG_INTRO_LABELS,
    OUTLOOK_DIALOG_MAIL_HINT_LABELS,
    OUTLOOK_DIALOG_MAIL_EVENTS_HINT_LABELS,
    OUTLOOK_DIALOG_MAIL_EVENTS_LABELS,
    OUTLOOK_DIALOG_MAIL_LABELS,
    OUTLOOK_DIALOG_NOTIFY_PET_FIRST_VISIBLE_LABELS,
    OUTLOOK_DIALOG_NOTIFY_PET_HINT_LABELS,
    OUTLOOK_DIALOG_NOTIFY_PET_LABELS,
    OUTLOOK_DIALOG_NOTIFY_PET_NUMBER_LABELS,
    OUTLOOK_DIALOG_NOTIFY_WHEN_PAUSED_HINT_LABELS,
    OUTLOOK_DIALOG_NOTIFY_WHEN_PAUSED_LABELS,
    OUTLOOK_DIALOG_SAVE_LABELS,
    OUTLOOK_DIALOG_SHARED_MAILBOXES_HINT_LABELS,
    OUTLOOK_DIALOG_SHARED_MAILBOXES_LABELS,
    OUTLOOK_DIALOG_SOURCE_COM_HINT_LABELS,
    OUTLOOK_DIALOG_SOURCE_COM_LABELS,
    OUTLOOK_DIALOG_SOURCE_GRAPH_HINT_LABELS,
    OUTLOOK_DIALOG_SOURCE_GRAPH_LABELS,
    OUTLOOK_DIALOG_SOURCE_LABELS,
    OUTLOOK_DIALOG_STATUS_BLOCKED_LABELS,
    OUTLOOK_DIALOG_STATUS_CONNECTED_LABELS,
    OUTLOOK_DIALOG_STATUS_DISCONNECTED_LABELS,
    OUTLOOK_DIALOG_STATUS_NEEDS_CONFIG_LABELS,
    OUTLOOK_DIALOG_GRAPH_IT_BLOCKED_LABELS,
    OUTLOOK_DIALOG_STATUS_UNAVAILABLE_LABELS,
    OUTLOOK_DIALOG_STATUS_UNSUPPORTED_LABELS,
    OUTLOOK_DIALOG_TEST_FAIL_LABELS,
    OUTLOOK_DIALOG_TEST_LABELS,
    OUTLOOK_DIALOG_TEST_OK_LABELS,
    OUTLOOK_DIALOG_TITLE_LABELS,
    OUTLOOK_NOTIFY_PET_FIRST_VISIBLE,
    OUTLOOK_SOURCE_COM,
    OUTLOOK_SOURCE_GRAPH,
    get_chat_language,
    get_outlook_calendar_enabled,
    get_outlook_include_shared_mailboxes,
    get_outlook_mail_enabled,
    get_outlook_mail_events_enabled,
    get_outlook_notify_pet_index,
    get_outlook_notify_when_paused,
    get_outlook_source,
    get_saved_pet_count,
    localized,
    outlook_com_supported,
    outlook_graph_configured,
    outlook_integration_available,
    set_outlook_settings,
)
from dialog_theme import DIALOG_HINT_STYLE, apply_light_dialog_theme
from outlook_backend import create_outlook_backend
from outlook_status import OutlookConnectionState, OutlookStatusManager
from pet_window import PetWindow


class OutlookSettingsDialog(QDialog):
    """Show Outlook connection status and mail/calendar toggles."""

    def __init__(
        self,
        parent: QWidget | None = None,
        pet: PetWindow | None = None,
        *,
        outlook_status: OutlookStatusManager | None = None,
        outlook_monitor: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet = pet
        self._outlook_status = outlook_status
        self._outlook_monitor = outlook_monitor
        self._positioned = False
        self._ui_language = get_chat_language()
        self._setup_window()
        self._build_ui()
        self._load_values()
        self._apply_language(self._ui_language)
        self._refresh_status()

    def _setup_window(self) -> None:
        self.setModal(True)
        self.setMinimumWidth(460)
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

        self._source_label = QLabel()
        layout.addWidget(self._source_label)
        self._source_picker = QComboBox()
        self._source_picker.addItem("", OUTLOOK_SOURCE_GRAPH)
        self._source_picker.addItem("", OUTLOOK_SOURCE_COM)
        if not outlook_graph_configured():
            model = self._source_picker.model()
            if model is not None:
                item = model.item(0)
                if item is not None:
                    item.setEnabled(False)
        if not outlook_com_supported():
            model = self._source_picker.model()
            if model is not None:
                item = model.item(1)
                if item is not None:
                    item.setEnabled(False)
        self._source_picker.currentIndexChanged.connect(self._on_source_changed)
        layout.addWidget(self._source_picker)
        self._source_hint = QLabel()
        self._source_hint.setStyleSheet(DIALOG_HINT_STYLE)
        self._source_hint.setWordWrap(True)
        layout.addWidget(self._source_hint)

        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._test_button = QPushButton()
        self._test_button.clicked.connect(self._test_connection)
        layout.addWidget(self._test_button)

        self._mail_checkbox = QCheckBox()
        layout.addWidget(self._mail_checkbox)
        self._mail_hint = QLabel()
        self._mail_hint.setStyleSheet(DIALOG_HINT_STYLE)
        self._mail_hint.setWordWrap(True)
        layout.addWidget(self._mail_hint)

        self._mail_events_checkbox = QCheckBox()
        layout.addWidget(self._mail_events_checkbox)
        self._mail_events_hint = QLabel()
        self._mail_events_hint.setStyleSheet(DIALOG_HINT_STYLE)
        self._mail_events_hint.setWordWrap(True)
        layout.addWidget(self._mail_events_hint)

        self._calendar_checkbox = QCheckBox()
        layout.addWidget(self._calendar_checkbox)
        self._calendar_hint = QLabel()
        self._calendar_hint.setStyleSheet(DIALOG_HINT_STYLE)
        self._calendar_hint.setWordWrap(True)
        layout.addWidget(self._calendar_hint)

        self._notify_pet_label = QLabel()
        layout.addWidget(self._notify_pet_label)
        self._notify_pet_picker = QComboBox()
        layout.addWidget(self._notify_pet_picker)
        self._notify_pet_hint = QLabel()
        self._notify_pet_hint.setStyleSheet(DIALOG_HINT_STYLE)
        self._notify_pet_hint.setWordWrap(True)
        layout.addWidget(self._notify_pet_hint)

        self._notify_when_paused_checkbox = QCheckBox()
        layout.addWidget(self._notify_when_paused_checkbox)
        self._notify_when_paused_hint = QLabel()
        self._notify_when_paused_hint.setStyleSheet(DIALOG_HINT_STYLE)
        self._notify_when_paused_hint.setWordWrap(True)
        layout.addWidget(self._notify_when_paused_hint)

        self._shared_mailboxes_checkbox = QCheckBox()
        layout.addWidget(self._shared_mailboxes_checkbox)
        self._shared_mailboxes_hint = QLabel()
        self._shared_mailboxes_hint.setStyleSheet(DIALOG_HINT_STYLE)
        self._shared_mailboxes_hint.setWordWrap(True)
        layout.addWidget(self._shared_mailboxes_hint)

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
        source = get_outlook_source()
        index = self._source_picker.findData(source)
        if index >= 0 and self._source_picker.itemData(index) == source:
            if not (source == OUTLOOK_SOURCE_GRAPH and not outlook_graph_configured()):
                self._source_picker.setCurrentIndex(index)
        if self._selected_source() == OUTLOOK_SOURCE_GRAPH and not outlook_graph_configured():
            com_index = self._source_picker.findData(OUTLOOK_SOURCE_COM)
            if com_index >= 0:
                self._source_picker.setCurrentIndex(com_index)
        self._mail_checkbox.setChecked(get_outlook_mail_enabled())
        self._mail_events_checkbox.setChecked(get_outlook_mail_events_enabled())
        self._calendar_checkbox.setChecked(get_outlook_calendar_enabled())
        self._notify_when_paused_checkbox.setChecked(get_outlook_notify_when_paused())
        self._shared_mailboxes_checkbox.setChecked(get_outlook_include_shared_mailboxes())
        self._reload_notify_pet_picker()
        self._update_source_hint()
        self._update_mail_events_visibility()
        self._update_com_only_visibility()

    def _reload_notify_pet_picker(self) -> None:
        language = self._ui_language
        selected = get_outlook_notify_pet_index()
        self._notify_pet_picker.clear()
        self._notify_pet_picker.addItem(
            localized(OUTLOOK_DIALOG_NOTIFY_PET_FIRST_VISIBLE_LABELS, language),
            OUTLOOK_NOTIFY_PET_FIRST_VISIBLE,
        )
        for index in range(get_saved_pet_count()):
            self._notify_pet_picker.addItem(
                localized(OUTLOOK_DIALOG_NOTIFY_PET_NUMBER_LABELS, language).format(
                    number=index + 1
                ),
                index,
            )
        picker_index = self._notify_pet_picker.findData(selected)
        if picker_index >= 0:
            self._notify_pet_picker.setCurrentIndex(picker_index)

    def _selected_source(self) -> str:
        value = self._source_picker.currentData()
        if value in {OUTLOOK_SOURCE_GRAPH, OUTLOOK_SOURCE_COM}:
            return str(value)
        return OUTLOOK_SOURCE_GRAPH

    def _on_source_changed(self) -> None:
        self._update_source_hint()
        self._update_mail_events_visibility()
        self._update_com_only_visibility()
        self._refresh_status()

    def _update_com_only_visibility(self) -> None:
        show = self._selected_source() == OUTLOOK_SOURCE_COM
        self._shared_mailboxes_checkbox.setVisible(show)
        self._shared_mailboxes_hint.setVisible(show)

    def _update_mail_events_visibility(self) -> None:
        show = self._selected_source() == OUTLOOK_SOURCE_COM
        self._mail_events_checkbox.setVisible(show)
        self._mail_events_hint.setVisible(show)

    def _update_source_hint(self) -> None:
        language = self._ui_language
        if self._selected_source() == OUTLOOK_SOURCE_GRAPH:
            self._source_hint.setText(
                localized(OUTLOOK_DIALOG_SOURCE_GRAPH_HINT_LABELS, language)
            )
        else:
            self._source_hint.setText(
                localized(OUTLOOK_DIALOG_SOURCE_COM_HINT_LABELS, language)
            )

    def _apply_language(self, language: str) -> None:
        self._ui_language = language
        self.setWindowTitle(localized(OUTLOOK_DIALOG_TITLE_LABELS, language))
        self._intro.setText(localized(OUTLOOK_DIALOG_INTRO_LABELS, language))
        self._source_label.setText(localized(OUTLOOK_DIALOG_SOURCE_LABELS, language))
        self._source_picker.setItemText(
            0, localized(OUTLOOK_DIALOG_SOURCE_GRAPH_LABELS, language)
        )
        self._source_picker.setItemText(
            1, localized(OUTLOOK_DIALOG_SOURCE_COM_LABELS, language)
        )
        self._test_button.setText(localized(OUTLOOK_DIALOG_TEST_LABELS, language))
        self._mail_checkbox.setText(localized(OUTLOOK_DIALOG_MAIL_LABELS, language))
        self._mail_hint.setText(localized(OUTLOOK_DIALOG_MAIL_HINT_LABELS, language))
        self._mail_events_checkbox.setText(
            localized(OUTLOOK_DIALOG_MAIL_EVENTS_LABELS, language)
        )
        self._mail_events_hint.setText(
            localized(OUTLOOK_DIALOG_MAIL_EVENTS_HINT_LABELS, language)
        )
        self._calendar_checkbox.setText(localized(OUTLOOK_DIALOG_CALENDAR_LABELS, language))
        self._calendar_hint.setText(localized(OUTLOOK_DIALOG_CALENDAR_HINT_LABELS, language))
        self._notify_pet_label.setText(
            localized(OUTLOOK_DIALOG_NOTIFY_PET_LABELS, language)
        )
        self._notify_pet_hint.setText(
            localized(OUTLOOK_DIALOG_NOTIFY_PET_HINT_LABELS, language)
        )
        self._notify_when_paused_checkbox.setText(
            localized(OUTLOOK_DIALOG_NOTIFY_WHEN_PAUSED_LABELS, language)
        )
        self._notify_when_paused_hint.setText(
            localized(OUTLOOK_DIALOG_NOTIFY_WHEN_PAUSED_HINT_LABELS, language)
        )
        self._shared_mailboxes_checkbox.setText(
            localized(OUTLOOK_DIALOG_SHARED_MAILBOXES_LABELS, language)
        )
        self._shared_mailboxes_hint.setText(
            localized(OUTLOOK_DIALOG_SHARED_MAILBOXES_HINT_LABELS, language)
        )
        if self._save_button is not None:
            self._save_button.setText(localized(OUTLOOK_DIALOG_SAVE_LABELS, language))
        if self._cancel_button is not None:
            self._cancel_button.setText(localized(OUTLOOK_DIALOG_CANCEL_LABELS, language))
        self._reload_notify_pet_picker()
        self._update_source_hint()
        self._update_com_only_visibility()

    def _refresh_status(self) -> None:
        language = self._ui_language
        if not outlook_integration_available():
            self._status.setText(localized(OUTLOOK_DIALOG_STATUS_UNSUPPORTED_LABELS, language))
            self._test_button.setEnabled(False)
            return

        selected = self._selected_source()
        if selected == OUTLOOK_SOURCE_GRAPH and not outlook_graph_configured():
            self._status.setText(
                localized(OUTLOOK_DIALOG_GRAPH_IT_BLOCKED_LABELS, language)
            )
            self._test_button.setEnabled(False)
            return

        self._test_button.setEnabled(True)
        manager = self._outlook_status
        if manager is None or manager.source != selected:
            self._status.setText(
                localized(OUTLOOK_DIALOG_STATUS_DISCONNECTED_LABELS, language)
            )
            return

        state = manager.state
        if state == OutlookConnectionState.CONNECTED:
            email = manager.email or "(unknown)"
            self._status.setText(
                localized(OUTLOOK_DIALOG_STATUS_CONNECTED_LABELS, language).format(
                    email=email
                )
            )
        elif state == OutlookConnectionState.UNAVAILABLE:
            self._status.setText(
                localized(OUTLOOK_DIALOG_STATUS_UNAVAILABLE_LABELS, language)
            )
        elif state == OutlookConnectionState.NEEDS_CONFIG:
            self._status.setText(
                localized(OUTLOOK_DIALOG_STATUS_NEEDS_CONFIG_LABELS, language)
            )
        elif state == OutlookConnectionState.BLOCKED:
            self._status.setText(localized(OUTLOOK_DIALOG_STATUS_BLOCKED_LABELS, language))
        else:
            self._status.setText(
                localized(OUTLOOK_DIALOG_STATUS_DISCONNECTED_LABELS, language)
            )

    def _test_connection(self) -> None:
        language = self._ui_language
        selected = self._selected_source()
        if selected == OUTLOOK_SOURCE_GRAPH and not outlook_graph_configured():
            self._status.setText(
                localized(OUTLOOK_DIALOG_STATUS_NEEDS_CONFIG_LABELS, language)
            )
            return

        client = create_outlook_backend(selected)
        try:
            if selected == OUTLOOK_SOURCE_GRAPH:
                ok = client.connect(interactive=True)
            else:
                ok = client.is_available()
            if ok:
                email = client.get_current_user_email() or "(unknown)"
                self._status.setText(
                    localized(OUTLOOK_DIALOG_TEST_OK_LABELS, language).format(email=email)
                )
            else:
                self._status.setText(localized(OUTLOOK_DIALOG_TEST_FAIL_LABELS, language))
        finally:
            client.close()

    def _save_settings(self) -> None:
        source = self._selected_source()
        notify_pet_data = self._notify_pet_picker.currentData()
        notify_pet_index = (
            int(notify_pet_data)
            if notify_pet_data is not None
            else OUTLOOK_NOTIFY_PET_FIRST_VISIBLE
        )
        set_outlook_settings(
            source=source,
            mail_enabled=self._mail_checkbox.isChecked(),
            mail_events_enabled=(
                self._mail_events_checkbox.isChecked()
                if source == OUTLOOK_SOURCE_COM
                else None
            ),
            calendar_enabled=self._calendar_checkbox.isChecked(),
            notify_pet_index=notify_pet_index,
            notify_when_paused=self._notify_when_paused_checkbox.isChecked(),
            include_shared_mailboxes=(
                self._shared_mailboxes_checkbox.isChecked()
                if source == OUTLOOK_SOURCE_COM
                else None
            ),
        )
        if self._outlook_status is not None:
            self._outlook_status.reload_backend()
        if self._outlook_monitor is not None:
            restart = getattr(self._outlook_monitor, "restart_mail_delivery", None)
            if callable(restart):
                restart()
        self.accept()


def open_outlook_settings_dialog(
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
    *,
    outlook_status: OutlookStatusManager | None = None,
    outlook_monitor: object | None = None,
) -> OutlookSettingsDialog | None:
    """Show the Outlook settings dialog. Returns the dialog when saved."""
    if pet is not None:
        pet.begin_menu_hold()
    try:
        dialog = OutlookSettingsDialog(
            parent,
            pet,
            outlook_status=outlook_status,
            outlook_monitor=outlook_monitor,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog
    finally:
        if pet is not None:
            pet.end_menu_hold()
