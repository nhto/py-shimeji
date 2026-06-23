"""Visual dialog for choosing a pet's sprite folder."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import (
    CHAT_WINDOW_GAP_PX,
    SPRITE_PICKER_APPLY_LABELS,
    SPRITE_PICKER_BROWSE_LABELS,
    SPRITE_PICKER_CANCEL_LABELS,
    SPRITE_PICKER_FILES_HEADING_LABELS,
    SPRITE_PICKER_INTRO_LABELS,
    SPRITE_PICKER_INVALID_FOLDER_LABELS,
    SPRITE_PICKER_OPTIONAL_LABELS,
    SPRITE_PICKER_TITLE_LABELS,
    TRAY_SELECT_SPRITES_TITLE_LABELS,
    discover_sprite_packs,
    get_chat_language,
    iter_sprite_file_entries,
    localized,
    pet_has_sprites,
    sprite_pack_display_name,
    sprite_state_label,
)
from pet_window import PetWindow

_THUMB_SIZE = 72
_CARD_MIN_WIDTH = 108


class _SpriteCard(QFrame):
    """Clickable thumbnail card for one sprite pack."""

    clicked = pyqtSignal()

    def __init__(
        self,
        sprites_dir: Path,
        display_name: str,
        selected: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sprites_dir = sprites_dir
        self._selected = selected
        self.setObjectName("spriteCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(_CARD_MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self._thumb = QLabel()
        self._thumb.setObjectName("spriteThumb")
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setFixedSize(_THUMB_SIZE, _THUMB_SIZE)
        self._thumb.setPixmap(self._load_thumbnail(sprites_dir))
        layout.addWidget(self._thumb, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._name = QLabel(display_name)
        self._name.setObjectName("spriteName")
        self._name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._name.setWordWrap(True)
        layout.addWidget(self._name)

        self._apply_selection_style()

    @staticmethod
    def _load_thumbnail(sprites_dir: Path) -> QPixmap:
        for candidate in ("idle_1.png", "walk_1.png", "sit_1.png", "drag_1.png"):
            path = sprites_dir / candidate
            if path.is_file():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    return pixmap.scaled(
                        _THUMB_SIZE,
                        _THUMB_SIZE,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        placeholder = QPixmap(_THUMB_SIZE, _THUMB_SIZE)
        placeholder.fill(Qt.GlobalColor.transparent)
        return placeholder

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_selection_style()

    def _apply_selection_style(self) -> None:
        if self._selected:
            self.setProperty("selected", True)
        else:
            self.setProperty("selected", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _SpriteFilePanel(QFrame):
    """Checklist of required PNG filenames for the selected folder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("spriteFilePanel")
        self._language = get_chat_language()
        self._sprites_dir: Path | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        self._heading = QLabel()
        self._heading.setObjectName("spriteFilesHeading")
        outer.addWidget(self._heading)

        self._rows_host = QWidget()
        self._rows_host.setObjectName("spriteFilesBody")
        self._rows = QVBoxLayout(self._rows_host)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(4)
        outer.addWidget(self._rows_host)

        self._file_rows: list[
            tuple[str, str, bool, QLabel, QLabel, QLabel, QLabel]
        ] = []
        self._build_rows()
        self.set_language(self._language)

    def _build_rows(self) -> None:
        current_state: str | None = None
        for state, filename, optional in iter_sprite_file_entries():
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)

            state_label = QLabel()
            state_label.setObjectName("spriteFileState")
            state_label.setFixedWidth(52)
            if state != current_state:
                state_label.setText(sprite_state_label(state, self._language))
                current_state = state
            row.addWidget(state_label)

            name_label = QLabel(filename)
            name_label.setObjectName("spriteFileName")
            row.addWidget(name_label, stretch=1)

            optional_label = QLabel()
            optional_label.setObjectName("spriteFileOptional")
            optional_label.setFixedWidth(54)
            row.addWidget(optional_label)

            status_label = QLabel()
            status_label.setObjectName("spriteFileStatus")
            status_label.setFixedWidth(16)
            status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(status_label)

            self._rows.addLayout(row)
            self._file_rows.append(
                (state, filename, optional, state_label, name_label, optional_label, status_label)
            )

    def set_language(self, language: str) -> None:
        self._language = language
        self._heading.setText(
            localized(SPRITE_PICKER_FILES_HEADING_LABELS, language)
        )
        optional_text = localized(SPRITE_PICKER_OPTIONAL_LABELS, language)
        current_state: str | None = None
        for state, _filename, optional, state_label, _name_label, optional_label, _status in (
            self._file_rows
        ):
            if state != current_state:
                state_label.setText(sprite_state_label(state, language))
                current_state = state
            optional_label.setText(optional_text if optional else "")
        self._refresh_status()

    def set_folder(self, sprites_dir: Path | None) -> None:
        self._sprites_dir = sprites_dir.resolve() if sprites_dir is not None else None
        self._refresh_status()

    def _refresh_status(self) -> None:
        for _state, filename, optional, _state_label, name_label, _optional_label, status_label in (
            self._file_rows
        ):
            present = (
                self._sprites_dir is not None
                and (self._sprites_dir / filename).is_file()
            )
            if present:
                status_label.setText("✓")
                status_label.setStyleSheet("color: #4ade80;")
                name_label.setStyleSheet("color: #e2e8f0;")
            elif optional:
                status_label.setText("–")
                status_label.setStyleSheet("color: #64748b;")
                name_label.setStyleSheet("color: #94a3b8;")
            else:
                status_label.setText("✗")
                status_label.setStyleSheet("color: #f87171;")
                name_label.setStyleSheet("color: #fca5a5;")


class SpritePickerDialog(QDialog):
    """Grid picker for built-in and custom sprite folders."""

    def __init__(
        self,
        pet_index: int,
        current_dir: Path,
        parent: QWidget | None = None,
        pet: PetWindow | None = None,
    ) -> None:
        super().__init__(parent)
        self._pet_index = pet_index
        self._pet = pet
        self._positioned = False
        self._language = get_chat_language()
        self._selected_dir = current_dir.resolve()
        self._cards: list[_SpriteCard] = []
        self._result_dir: Path | None = None

        self._setup_window()
        self._build_ui()
        self._reload_packs()
        self._apply_language()

    @property
    def selected_dir(self) -> Path | None:
        return self._result_dir

    def _setup_window(self) -> None:
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setMaximumWidth(520)
        self.setStyleSheet(
            """
            QWidget#spritePickerRoot {
                background-color: #1a1625;
                border: 1px solid #3d3654;
                border-radius: 16px;
            }
            QLabel#spriteHeading {
                color: #f8fafc;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#spriteIntro {
                color: #94a3b8;
                font-size: 11px;
            }
            QFrame#spriteFilePanel {
                background-color: #14111c;
                border: 1px solid #2e2940;
                border-radius: 10px;
            }
            QLabel#spriteFilesHeading {
                color: #cbd5e1;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#spriteFileState {
                color: #94a3b8;
                font-size: 11px;
            }
            QLabel#spriteFileName {
                color: #e2e8f0;
                font-size: 11px;
                font-family: Consolas, "Courier New", monospace;
            }
            QLabel#spriteFileOptional {
                color: #64748b;
                font-size: 10px;
            }
            QLabel#spriteFileStatus {
                font-size: 11px;
                font-weight: 700;
            }
            QScrollArea#spriteScroll {
                background-color: transparent;
                border: none;
            }
            QWidget#spriteScrollBody {
                background-color: transparent;
            }
            QFrame#spriteCard {
                background-color: #221e30;
                border: 2px solid #3d3654;
                border-radius: 12px;
            }
            QFrame#spriteCard:hover {
                border-color: #6366f1;
                background-color: #2a2540;
            }
            QFrame#spriteCard[selected="true"] {
                border-color: #818cf8;
                background-color: #2d2850;
            }
            QLabel#spriteThumb {
                background-color: #14111c;
                border: 1px solid #2e2940;
                border-radius: 10px;
            }
            QLabel#spriteName {
                color: #e2e8f0;
                font-size: 11px;
            }
            QPushButton#browseButton {
                background-color: transparent;
                color: #cbd5e1;
                border: 1px solid #4b4563;
                border-radius: 10px;
                padding: 8px 14px;
            }
            QPushButton#browseButton:hover {
                background-color: #3d3654;
                color: #f8fafc;
            }
            QPushButton#applyButton {
                background-color: #f97316;
                color: #1c1510;
                border: none;
                border-radius: 10px;
                padding: 8px 18px;
                font-weight: 600;
            }
            QPushButton#applyButton:hover {
                background-color: #fb923c;
            }
            QPushButton#cancelButton {
                background-color: transparent;
                color: #cbd5e1;
                border: 1px solid #4b4563;
                border-radius: 10px;
                padding: 8px 14px;
            }
            QPushButton#cancelButton:hover {
                background-color: #3d3654;
                color: #f8fafc;
            }
            """
        )

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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        root = QWidget()
        root.setObjectName("spritePickerRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        self._heading = QLabel()
        self._heading.setObjectName("spriteHeading")
        layout.addWidget(self._heading)

        self._intro = QLabel()
        self._intro.setObjectName("spriteIntro")
        self._intro.setWordWrap(True)
        layout.addWidget(self._intro)

        self._file_panel = _SpriteFilePanel(parent=root)
        layout.addWidget(self._file_panel)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("spriteScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setMaximumHeight(280)

        self._grid_host = QWidget()
        self._grid_host.setObjectName("spriteScrollBody")
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(2, 2, 2, 2)
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(10)
        self._scroll.setWidget(self._grid_host)
        layout.addWidget(self._scroll)

        button_row = QHBoxLayout()
        self._browse_button = QPushButton()
        self._browse_button.setObjectName("browseButton")
        self._browse_button.clicked.connect(self._browse_custom_folder)
        button_row.addWidget(self._browse_button)
        button_row.addStretch()

        self._cancel_button = QPushButton()
        self._cancel_button.setObjectName("cancelButton")
        self._cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self._cancel_button)

        self._apply_button = QPushButton()
        self._apply_button.setObjectName("applyButton")
        self._apply_button.clicked.connect(self._apply_selection)
        button_row.addWidget(self._apply_button)
        layout.addLayout(button_row)

        outer.addWidget(root)

    def _apply_language(self) -> None:
        self.setWindowTitle(
            localized(SPRITE_PICKER_TITLE_LABELS, self._language).format(
                index=self._pet_index
            )
        )
        self._heading.setText(
            localized(SPRITE_PICKER_TITLE_LABELS, self._language).format(
                index=self._pet_index
            )
        )
        self._intro.setText(localized(SPRITE_PICKER_INTRO_LABELS, self._language))
        self._file_panel.set_language(self._language)
        self._file_panel.set_folder(self._selected_dir)
        self._browse_button.setText(localized(SPRITE_PICKER_BROWSE_LABELS, self._language))
        self._apply_button.setText(localized(SPRITE_PICKER_APPLY_LABELS, self._language))
        self._cancel_button.setText(localized(SPRITE_PICKER_CANCEL_LABELS, self._language))

    def _reload_packs(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

        packs = discover_sprite_packs(self._selected_dir)
        columns = 3
        for index, sprites_dir in enumerate(packs):
            name = sprite_pack_display_name(sprites_dir, self._language)
            card = _SpriteCard(
                sprites_dir,
                name,
                selected=sprites_dir.resolve() == self._selected_dir,
                parent=self._grid_host,
            )
            card.clicked.connect(lambda checked=False, path=sprites_dir: self._select_dir(path))
            row, col = divmod(index, columns)
            self._grid.addWidget(card, row, col)
            self._cards.append(card)

        self._file_panel.set_folder(self._selected_dir)

    def _select_dir(self, sprites_dir: Path) -> None:
        self._selected_dir = sprites_dir.resolve()
        for card in self._cards:
            card.set_selected(card.sprites_dir.resolve() == self._selected_dir)
        self._file_panel.set_folder(self._selected_dir)

    def _browse_custom_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            localized(TRAY_SELECT_SPRITES_TITLE_LABELS, self._language).format(
                index=self._pet_index
            ),
            str(self._selected_dir),
        )
        if not folder:
            return

        path = Path(folder)
        if not pet_has_sprites(path):
            QMessageBox.warning(
                self,
                localized(SPRITE_PICKER_TITLE_LABELS, self._language).format(
                    index=self._pet_index
                ),
                localized(SPRITE_PICKER_INVALID_FOLDER_LABELS, self._language),
            )
            return

        self._selected_dir = path.resolve()
        self._reload_packs()

    def _apply_selection(self) -> None:
        if not pet_has_sprites(self._selected_dir):
            QMessageBox.warning(
                self,
                localized(SPRITE_PICKER_TITLE_LABELS, self._language).format(
                    index=self._pet_index
                ),
                localized(SPRITE_PICKER_INVALID_FOLDER_LABELS, self._language),
            )
            return

        self._result_dir = self._selected_dir
        self.accept()


def open_sprite_picker_dialog(
    pet_index: int,
    current_dir: Path,
    parent: QWidget | None = None,
    pet: PetWindow | None = None,
) -> Path | None:
    """
    Show the sprite picker and return the chosen folder, or None if cancelled.
    """
    if pet is not None:
        pet.begin_chat_hold()
    try:
        dialog = SpritePickerDialog(pet_index, current_dir, parent=parent, pet=pet)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_dir
    finally:
        if pet is not None:
            pet.end_chat_hold()
