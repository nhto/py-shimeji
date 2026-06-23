"""Shared light-theme styles for application dialogs and pop-up panels."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

# Inline label styles (used where object-name selectors are not practical).
DIALOG_HINT_STYLE = "color: #64748b; font-size: 11px;"
DIALOG_HEADING_STYLE = "font-weight: 600; color: #0f172a;"

SPRITE_STATUS_OK_STYLE = "color: #16a34a;"
SPRITE_STATUS_OPTIONAL_STYLE = "color: #64748b;"
SPRITE_STATUS_MISSING_STYLE = "color: #dc2626;"
SPRITE_NAME_OK_STYLE = "color: #1e293b;"
SPRITE_NAME_OPTIONAL_STYLE = "color: #64748b;"
SPRITE_NAME_MISSING_STYLE = "color: #b91c1c;"

CHAT_USER_LABEL_COLOR = "#4f46e5"
CHAT_USER_BUBBLE_BG = "#4f46e5"
CHAT_USER_BUBBLE_FG = "#ffffff"
CHAT_USER_BORDER = "border:1px solid #6366f1;"

CHAT_BUBU_LABEL_COLOR = "#ea580c"
CHAT_BUBU_BUBBLE_BG = "#f1f5f9"
CHAT_BUBU_BUBBLE_FG = "#1e293b"
CHAT_BUBU_BORDER = "border:1px solid #e2e8f0;"
CHAT_BUBU_STREAMING_BORDER = "border:1px solid #f97316;"

CHAT_TYPING_LABEL_COLOR = "#ea580c"
CHAT_TYPING_BUBBLE_BG = "#f1f5f9"
CHAT_TYPING_BUBBLE_BORDER = "border:1px solid #e2e8f0;"
CHAT_TYPING_TEXT_COLOR = "#475569"

STATUS_ONLINE_COLOR = "#16a34a"
STATUS_OFFLINE_COLOR = "#dc2626"
STATUS_TYPING_COLOR = "#d97706"

LIGHT_DIALOG_STYLESHEET = """
    QDialog {
        background-color: #ffffff;
        color: #0f172a;
    }
    QLabel {
        color: #0f172a;
    }
    QFrame[frameShape="4"] {
        color: #e2e8f0;
    }
    QLineEdit {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 8px 10px;
        selection-background-color: #6366f1;
        selection-color: #ffffff;
    }
    QLineEdit:focus {
        border-color: #6366f1;
    }
    QComboBox {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 24px;
    }
    QComboBox:hover {
        border-color: #94a3b8;
    }
    QComboBox:focus {
        border-color: #6366f1;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        selection-background-color: #eef2ff;
        selection-color: #312e81;
    }
    QSlider::groove:horizontal {
        background: #e2e8f0;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #6366f1;
        width: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }
    QSlider::sub-page:horizontal {
        background: #a5b4fc;
        border-radius: 3px;
    }
    QSpinBox {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 4px 8px;
        min-height: 24px;
    }
    QSpinBox:focus {
        border-color: #6366f1;
    }
    QCheckBox {
        color: #0f172a;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        background: #ffffff;
    }
    QCheckBox::indicator:checked {
        background: #6366f1;
        border-color: #6366f1;
    }
    QPushButton {
        background-color: #f8fafc;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 6px 14px;
    }
    QPushButton:hover {
        background-color: #f1f5f9;
        color: #0f172a;
        border-color: #94a3b8;
    }
    QDialogButtonBox QPushButton {
        min-width: 72px;
    }
"""

LIGHT_SPRITE_PICKER_STYLESHEET = """
    QWidget#spritePickerRoot {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
    }
    QLabel#spriteHeading {
        color: #0f172a;
        font-size: 15px;
        font-weight: 700;
    }
    QLabel#spriteIntro {
        color: #64748b;
        font-size: 11px;
    }
    QFrame#spriteFilePanel {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
    }
    QLabel#spriteFilesHeading {
        color: #334155;
        font-size: 11px;
        font-weight: 600;
    }
    QLabel#spriteFileState {
        color: #64748b;
        font-size: 11px;
    }
    QLabel#spriteFileName {
        color: #1e293b;
        font-size: 11px;
        font-family: Consolas, "Courier New", monospace;
    }
    QLabel#spriteFileOptional {
        color: #94a3b8;
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
        background-color: #ffffff;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
    }
    QFrame#spriteCard:hover {
        border-color: #6366f1;
        background-color: #f8fafc;
    }
    QFrame#spriteCard[selected="true"] {
        border-color: #4f46e5;
        background-color: #eef2ff;
    }
    QLabel#spriteThumb {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
    }
    QLabel#spriteName {
        color: #1e293b;
        font-size: 11px;
    }
    QPushButton#browseButton {
        background-color: #ffffff;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 8px 14px;
    }
    QPushButton#browseButton:hover {
        background-color: #f1f5f9;
        color: #0f172a;
        border-color: #94a3b8;
    }
    QPushButton#applyButton {
        background-color: #f97316;
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 600;
    }
    QPushButton#applyButton:hover {
        background-color: #ea580c;
    }
    QPushButton#cancelButton {
        background-color: #ffffff;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 8px 14px;
    }
    QPushButton#cancelButton:hover {
        background-color: #f1f5f9;
        color: #0f172a;
        border-color: #94a3b8;
    }
"""

LIGHT_CHAT_STYLESHEET = """
    QWidget#chatCard {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
    }
    QWidget#chatHeader {
        background-color: #f8fafc;
        border-top-left-radius: 20px;
        border-top-right-radius: 20px;
        border-bottom: 1px solid #e2e8f0;
    }
    QLabel#chatTitle {
        color: #0f172a;
        font-size: 15px;
        font-weight: 700;
    }
    QLabel#chatSubtitle {
        color: #64748b;
        font-size: 11px;
    }
    QLabel#statusDot {
        color: #16a34a;
        font-size: 10px;
    }
    QPushButton#closeButton {
        background-color: #ffffff;
        color: #64748b;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 2px 8px;
        font-size: 12px;
    }
    QPushButton#closeButton:hover {
        background-color: #f1f5f9;
        color: #0f172a;
        border-color: #94a3b8;
    }
    QTextEdit#transcript {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 8px 6px;
        color: #0f172a;
    }
    QFrame#composer {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
    }
    QLineEdit#messageInput {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 10px 12px;
        color: #0f172a;
        selection-background-color: #6366f1;
        selection-color: #ffffff;
    }
    QLineEdit#messageInput:focus {
        border-color: #6366f1;
    }
    QPushButton#sendButton {
        background-color: #f97316;
        color: #ffffff;
        border: none;
        border-radius: 12px;
        padding: 10px 18px;
        font-weight: 700;
    }
    QPushButton#sendButton:hover {
        background-color: #ea580c;
    }
    QPushButton#sendButton:disabled {
        background-color: #e2e8f0;
        color: #94a3b8;
    }
    QPushButton#sendButton[loading="true"] {
        background-color: #ffedd5;
        color: #c2410c;
    }
    QFrame#loadingBar {
        background-color: #e2e8f0;
        border: none;
        max-height: 3px;
        min-height: 3px;
    }
    QPushButton#attachButton {
        background-color: #ffffff;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 10px 12px;
        font-size: 14px;
    }
    QPushButton#attachButton:hover {
        border-color: #6366f1;
        color: #312e81;
    }
    QPushButton#attachButton:disabled {
        background-color: #f1f5f9;
        color: #94a3b8;
        border-color: #e2e8f0;
    }
    QPushButton#attachButton[attached="true"] {
        border-color: #f97316;
        color: #c2410c;
        background-color: #fff7ed;
    }
    QLabel#attachmentChip {
        color: #c2410c;
        font-size: 11px;
    }
    QPushButton#removeAttachmentButton {
        background-color: #ffffff;
        color: #64748b;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 0 6px;
        font-size: 11px;
    }
    QPushButton#removeAttachmentButton:hover {
        background-color: #f1f5f9;
        color: #0f172a;
        border-color: #94a3b8;
    }
    QComboBox#modelPicker,
    QComboBox#languagePicker {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 2px 8px;
        font-size: 11px;
        min-height: 22px;
    }
    QComboBox#modelPicker:hover,
    QComboBox#languagePicker:hover {
        border-color: #6366f1;
        color: #312e81;
    }
    QComboBox#modelPicker::drop-down,
    QComboBox#languagePicker::drop-down {
        border: none;
        width: 18px;
    }
    QComboBox#modelPicker QAbstractItemView,
    QComboBox#languagePicker QAbstractItemView {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        selection-background-color: #eef2ff;
        selection-color: #312e81;
    }
"""


def apply_light_dialog_theme(widget: QWidget) -> None:
    """Apply the shared light stylesheet to a modal dialog."""
    widget.setStyleSheet(LIGHT_DIALOG_STYLESHEET)


def apply_light_sprite_picker_theme(widget: QWidget) -> None:
    """Apply the light sprite-picker stylesheet on top of the base dialog theme."""
    widget.setStyleSheet(LIGHT_DIALOG_STYLESHEET + LIGHT_SPRITE_PICKER_STYLESHEET)


def apply_light_chat_theme(widget: QWidget) -> None:
    """Apply the light chat panel stylesheet."""
    widget.setStyleSheet(LIGHT_CHAT_STYLESHEET)
