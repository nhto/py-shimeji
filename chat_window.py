"""Pop-up chat window for talking with Bubu via OpenRouter."""

from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication, QMouseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import (
    CHAT_ATTACH_IMAGE_LABELS,
    CHAT_GREETINGS,
    CHAT_IMAGE_ONLY_LABELS,
    CHAT_IMAGE_TOO_LARGE_LABELS,
    CHAT_IMAGE_UNSUPPORTED_LABELS,
    CHAT_INPUT_PLACEHOLDERS,
    CHAT_LANGUAGES,
    CHAT_MAX_HISTORY,
    CHAT_MAX_IMAGE_BYTES,
    CHAT_MODELS,
    CHAT_SEND_LABELS,
    CHAT_WINDOW_GAP_PX,
    CHAT_WINDOW_HEIGHT,
    CHAT_WINDOW_WIDTH,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    build_chat_system_prompt,
    chat_model_supports_images,
    get_chat_language,
    get_chat_model,
    set_chat_language,
    set_chat_model,
)
from pet_window import PetWindow


@dataclass
class ChatMessage:
    role: str
    text: str
    image_data_urls: list[str] | None = None


def _serialize_chat_message(message: ChatMessage) -> dict[str, object]:
    if message.image_data_urls:
        content: list[dict[str, object]] = []
        if message.text:
            content.append({"type": "text", "text": message.text})
        for image_url in message.image_data_urls:
            content.append({"type": "image_url", "image_url": {"url": image_url}})
        if not content:
            content = [{"type": "text", "text": ""}]
        return {"role": message.role, "content": content}
    return {"role": message.role, "content": message.text}


def _encode_image_data_url(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        raise ValueError("unsupported_image")

    data = path.read_bytes()
    if len(data) > CHAT_MAX_IMAGE_BYTES:
        raise ValueError("image_too_large")

    encoded = base64.standard_b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class ChatWorker(QThread):
    """Fetch a chat completion without blocking the UI thread."""

    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        messages: list[ChatMessage],
        model: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._messages = messages
        self._model = model

    def run(self) -> None:
        if not OPENROUTER_API_KEY:
            self.failed.emit("OpenRouter API key is not configured.")
            return

        payload = {
            "model": self._model,
            "stream": True,
            "messages": [_serialize_chat_message(message) for message in self._messages],
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            OPENROUTER_API_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/py-shimeji",
                "X-Title": "py-shimeji",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                reply_parts: list[str] = []
                for raw_line in response:
                    if self.isInterruptionRequested():
                        return

                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue

                    payload_line = line[5:].strip()
                    if payload_line == "[DONE]":
                        break

                    data = json.loads(payload_line)
                    delta = data["choices"][0]["delta"].get("content", "")

                    if isinstance(delta, list):
                        chunk = "".join(
                            item.get("text", "")
                            for item in delta
                            if isinstance(item, dict)
                        )
                    elif isinstance(delta, str):
                        chunk = delta
                    else:
                        chunk = ""

                    if chunk:
                        reply_parts.append(chunk)
                        self.chunk_received.emit(chunk)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self.failed.emit(f"API error ({exc.code}): {detail}")
            return
        except urllib.error.URLError as exc:
            self.failed.emit(f"Network error: {exc.reason}")
            return
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            self.failed.emit(f"Unexpected response: {exc}")
            return

        reply = "".join(reply_parts).strip()
        if not reply:
            self.failed.emit("The model returned an empty response.")
            return

        self.finished.emit(reply)


class ChatWindow(QWidget):
    """Speech-bubble chat panel anchored above the desktop pet."""

    _instance: ChatWindow | None = None

    def __init__(self, parent: QWidget | None = None, pet: PetWindow | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._pet = pet
        self._drag_offset = QPoint(0, 0)
        self._language = get_chat_language()
        self._history: list[ChatMessage] = [
            ChatMessage("system", build_chat_system_prompt(self._language)),
        ]
        self._messages: list[ChatMessage] = []
        self._worker: ChatWorker | None = None
        self._model = get_chat_model()
        self._streaming_reply = ""
        self._pending_image_data_url: str | None = None
        self._pending_image_name: str | None = None
        self._setup_window()
        self._build_ui()
        self._append_bubu_message(CHAT_GREETINGS[self._language])

    @classmethod
    def open_chat(
        cls,
        parent: QWidget | None = None,
        pet: PetWindow | None = None,
    ) -> ChatWindow:
        """Show a single shared chat window above the pet."""
        if cls._instance is None:
            cls._instance = ChatWindow(parent, pet=pet)
        elif pet is not None:
            cls._instance._set_pet(pet)
        if pet is not None:
            pet.begin_chat_hold()
        cls._instance._position_above_pet(pet)
        cls._instance.show()
        cls._instance.raise_()
        cls._instance.activateWindow()
        cls._instance._input.setFocus()
        return cls._instance

    def _set_pet(self, pet: PetWindow) -> None:
        if self._pet is pet:
            return
        if self._pet is not None:
            self._pet.end_chat_hold()
        self._pet = pet

    def _position_above_pet(self, pet: PetWindow | None) -> None:
        """Place the chat panel centered above the shimeji."""
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

    def _setup_window(self) -> None:
        self.setWindowTitle("Chat with Bubu")
        self.setFixedSize(CHAT_WINDOW_WIDTH, CHAT_WINDOW_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(
            """
            QWidget#chatCard {
                background-color: #1a1625;
                border: 1px solid #3d3654;
                border-radius: 20px;
            }
            QWidget#chatHeader {
                background-color: #221e30;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom: 1px solid #3d3654;
            }
            QLabel#chatTitle {
                color: #f8fafc;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#chatSubtitle {
                color: #cbd5e1;
                font-size: 11px;
            }
            QLabel#statusDot {
                color: #4ade80;
                font-size: 10px;
            }
            QPushButton#closeButton {
                background-color: transparent;
                color: #cbd5e1;
                border: 1px solid #4b4563;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 12px;
            }
            QPushButton#closeButton:hover {
                background-color: #3d3654;
                color: #f8fafc;
            }
            QTextEdit#transcript {
                background-color: #14111c;
                border: 1px solid #2e2940;
                border-radius: 12px;
                padding: 8px 6px;
            }
            QFrame#composer {
                background-color: #221e30;
                border: 1px solid #3d3654;
                border-radius: 16px;
            }
            QLineEdit#messageInput {
                background-color: #14111c;
                border: 1px solid #4b4563;
                border-radius: 12px;
                padding: 10px 12px;
                color: #f8fafc;
                selection-background-color: #6366f1;
            }
            QLineEdit#messageInput:focus {
                border-color: #818cf8;
            }
            QPushButton#sendButton {
                background-color: #f97316;
                color: #1c1510;
                border: none;
                border-radius: 12px;
                padding: 10px 18px;
                font-weight: 700;
            }
            QPushButton#sendButton:hover {
                background-color: #fb923c;
            }
            QPushButton#sendButton:disabled {
                background-color: #3d3654;
                color: #94a3b8;
            }
            QPushButton#attachButton {
                background-color: #2a2638;
                color: #e2e8f0;
                border: 1px solid #4b4563;
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QPushButton#attachButton:hover {
                border-color: #818cf8;
                color: #f8fafc;
            }
            QPushButton#attachButton:disabled {
                background-color: #221e30;
                color: #64748b;
                border-color: #3d3654;
            }
            QPushButton#attachButton[attached="true"] {
                border-color: #f97316;
                color: #fdba74;
            }
            QLabel#attachmentChip {
                color: #fdba74;
                font-size: 11px;
            }
            QPushButton#removeAttachmentButton {
                background-color: transparent;
                color: #cbd5e1;
                border: 1px solid #4b4563;
                border-radius: 8px;
                padding: 0 6px;
                font-size: 11px;
            }
            QPushButton#removeAttachmentButton:hover {
                background-color: #3d3654;
                color: #f8fafc;
            }
            QComboBox#modelPicker,
            QComboBox#languagePicker {
                background-color: #14111c;
                color: #e2e8f0;
                border: 1px solid #4b4563;
                border-radius: 8px;
                padding: 2px 8px;
                font-size: 11px;
                min-height: 22px;
            }
            QComboBox#modelPicker:hover,
            QComboBox#languagePicker:hover {
                border-color: #818cf8;
                color: #f8fafc;
            }
            QComboBox#modelPicker::drop-down,
            QComboBox#languagePicker::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox#modelPicker QAbstractItemView,
            QComboBox#languagePicker QAbstractItemView {
                background-color: #221e30;
                color: #f8fafc;
                border: 1px solid #4b4563;
                selection-background-color: #6366f1;
                selection-color: #f8fafc;
            }
            """
        )

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        card = QWidget()
        card.setObjectName("chatCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("chatHeader")
        header.setFixedHeight(96)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 12, 12)
        header_layout.setSpacing(10)

        avatar = QLabel("B")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "background-color: #f97316; color: #1c1510; border-radius: 18px; font-weight: 700;"
        )

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title = QLabel("Bubu")
        title.setObjectName("chatTitle")
        subtitle_row = QHBoxLayout()
        subtitle_row.setSpacing(6)
        status = QLabel("●")
        status.setObjectName("statusDot")
        subtitle = QLabel("Online")
        subtitle.setObjectName("chatSubtitle")
        subtitle_row.addWidget(status)
        subtitle_row.addWidget(subtitle)
        subtitle_row.addStretch()
        title_block.addWidget(title)
        title_block.addLayout(subtitle_row)

        pickers_row = QHBoxLayout()
        pickers_row.setSpacing(6)

        self._language_picker = QComboBox()
        self._language_picker.setObjectName("languagePicker")
        self._language_picker.setCursor(Qt.CursorShape.PointingHandCursor)
        for lang_id, label in CHAT_LANGUAGES:
            self._language_picker.addItem(label, lang_id)
        lang_index = self._language_picker.findData(self._language)
        if lang_index >= 0:
            self._language_picker.setCurrentIndex(lang_index)
        self._language_picker.currentIndexChanged.connect(self._on_language_changed)
        pickers_row.addWidget(self._language_picker, stretch=1)

        self._model_picker = QComboBox()
        self._model_picker.setObjectName("modelPicker")
        self._model_picker.setCursor(Qt.CursorShape.PointingHandCursor)
        for model_id, label in CHAT_MODELS:
            self._model_picker.addItem(label, model_id)
        index = self._model_picker.findData(self._model)
        if index >= 0:
            self._model_picker.setCurrentIndex(index)
        self._model_picker.currentIndexChanged.connect(self._on_model_changed)
        pickers_row.addWidget(self._model_picker, stretch=1)

        title_block.addLayout(pickers_row)

        close_button = QPushButton("×")
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(28, 28)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close)

        header_layout.addWidget(avatar)
        header_layout.addLayout(title_block, stretch=1)
        header_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignTop)
        card_layout.addWidget(header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 12, 14, 14)
        body_layout.setSpacing(12)

        self._transcript = QTextEdit()
        self._transcript.setObjectName("transcript")
        self._transcript.setReadOnly(True)
        self._transcript.setFrameShape(QFrame.Shape.NoFrame)
        self._transcript.setFont(QFont("Segoe UI", 11))
        self._transcript.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._transcript.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body_layout.addWidget(self._transcript, stretch=1)

        self._attachment_row = QWidget()
        attachment_layout = QHBoxLayout(self._attachment_row)
        attachment_layout.setContentsMargins(4, 0, 4, 0)
        attachment_layout.setSpacing(6)
        self._attachment_label = QLabel()
        self._attachment_label.setObjectName("attachmentChip")
        remove_attachment_button = QPushButton("×")
        remove_attachment_button.setObjectName("removeAttachmentButton")
        remove_attachment_button.setFixedSize(22, 22)
        remove_attachment_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_attachment_button.clicked.connect(self._clear_pending_image)
        attachment_layout.addWidget(self._attachment_label)
        attachment_layout.addWidget(remove_attachment_button)
        attachment_layout.addStretch()
        self._attachment_row.setVisible(False)
        body_layout.addWidget(self._attachment_row)

        composer = QFrame()
        composer.setObjectName("composer")
        composer_layout = QHBoxLayout(composer)
        composer_layout.setContentsMargins(8, 8, 8, 8)
        composer_layout.setSpacing(8)

        self._attach_button = QPushButton("🖼")
        self._attach_button.setObjectName("attachButton")
        self._attach_button.setFixedWidth(42)
        self._attach_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_button.clicked.connect(self._pick_image)
        composer_layout.addWidget(self._attach_button)

        self._input = QLineEdit()
        self._input.setObjectName("messageInput")
        self._input.returnPressed.connect(self._send_message)
        composer_layout.addWidget(self._input, stretch=1)

        self._send_button = QPushButton("Send")
        self._send_button.setObjectName("sendButton")
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.clicked.connect(self._send_message)
        composer_layout.addWidget(self._send_button)

        self._update_input_labels()
        self._update_image_upload_visibility()

        body_layout.addWidget(composer)
        card_layout.addWidget(body, stretch=1)

        outer.addWidget(card)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _append_bubu_message(self, text: str) -> None:
        self._messages.append(ChatMessage("assistant", text))
        self._render_transcript()

    def _append_user_message(
        self,
        text: str,
        image_data_urls: list[str] | None = None,
    ) -> None:
        self._messages.append(ChatMessage("user", text, image_data_urls))
        self._render_transcript()

    def _render_transcript(self) -> None:
        bubbles: list[str] = []
        for message in self._messages:
            bubbles.append(
                self._build_bubble(
                    message.text,
                    is_user=message.role == "user",
                    image_data_urls=message.image_data_urls,
                )
            )
        if self._streaming_reply:
            bubbles.append(self._build_bubble(self._streaming_reply, is_user=False))

        self._transcript.setHtml("".join(bubbles))
        scrollbar = self._transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _build_bubble(
        self,
        text: str,
        *,
        is_user: bool,
        image_data_urls: list[str] | None = None,
    ) -> str:
        """Render a message bubble using table layout (Qt rich text lacks flex/inline-block)."""
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        image_html = ""
        if image_data_urls:
            image_bits = []
            for image_url in image_data_urls:
                safe_url = (
                    image_url.replace("&", "&amp;")
                    .replace('"', "&quot;")
                )
                image_bits.append(
                    f'<img src="{safe_url}" width="180" '
                    f'style="margin-top:6px; border-radius:8px;" />'
                )
            image_html = "<br/>".join(image_bits)
            if image_html:
                image_html += "<br/>"

        body_html = f"{image_html}{escaped}" if image_html or escaped else "&nbsp;"
        if is_user:
            sender = "You"
            align = "right"
            label_color = "#a5b4fc"
            bubble_bg = "#4f46e5"
            bubble_fg = "#ffffff"
            border = "border:1px solid #6366f1;"
        else:
            sender = "Bubu"
            align = "left"
            label_color = "#fdba74"
            bubble_bg = "#2a2638"
            bubble_fg = "#f1f5f9"
            border = "border:1px solid #4b4563;"

        return (
            f'<table width="100%" cellspacing="0" cellpadding="0" '
            f'style="margin-bottom:14px;">'
            f'<tr><td align="{align}" style="padding:0 4px;">'
            f'<span style="font-size:10px; font-weight:600; color:{label_color};">'
            f'{sender}</span><br/>'
            f'<table cellspacing="0" cellpadding="0" style="margin-top:4px;">'
            f'<tr><td align="{align}" style="background-color:{bubble_bg}; {border} '
            f'padding:10px 14px; color:{bubble_fg}; font-size:13px; '
            f'line-height:1.55;">{body_html}</td></tr></table>'
            f'</td></tr></table>'
        )

    def _on_model_changed(self, index: int) -> None:
        if index < 0:
            return
        model_id = self._model_picker.itemData(index)
        if not isinstance(model_id, str) or model_id == self._model:
            return
        self._model = model_id
        set_chat_model(model_id)
        self._update_image_upload_visibility()

    def _on_language_changed(self, index: int) -> None:
        if index < 0:
            return
        language_id = self._language_picker.itemData(index)
        if not isinstance(language_id, str) or language_id == self._language:
            return
        self._language = language_id
        set_chat_language(language_id)
        self._sync_system_prompt()
        self._update_input_labels()

    def _sync_system_prompt(self) -> None:
        prompt = build_chat_system_prompt(self._language)
        if not self._history:
            self._history.append(ChatMessage("system", prompt))
            return
        self._history[0] = ChatMessage("system", prompt)

    def _localized(self, labels: dict[str, str]) -> str:
        return labels.get(self._language, labels["en"])

    def _update_input_labels(self) -> None:
        self._input.setPlaceholderText(
            CHAT_INPUT_PLACEHOLDERS.get(self._language, CHAT_INPUT_PLACEHOLDERS["en"])
        )
        if self._worker is None:
            self._send_button.setText(
                CHAT_SEND_LABELS.get(self._language, CHAT_SEND_LABELS["en"])
            )
        self._update_attach_button_state()

    def _update_image_upload_visibility(self) -> None:
        supports_images = chat_model_supports_images(self._model)
        self._attach_button.setVisible(supports_images)
        self._attachment_row.setVisible(
            supports_images and self._pending_image_data_url is not None
        )
        if not supports_images:
            self._clear_pending_image()

    def _update_attach_button_state(self) -> None:
        attached = self._pending_image_data_url is not None
        self._attach_button.setProperty("attached", attached)
        self._attach_button.style().unpolish(self._attach_button)
        self._attach_button.style().polish(self._attach_button)
        self._attach_button.setToolTip(self._localized(CHAT_ATTACH_IMAGE_LABELS))
        if attached and self._pending_image_name:
            self._attachment_label.setText(self._pending_image_name)

    def _pick_image(self) -> None:
        if self._worker is not None or not chat_model_supports_images(self._model):
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            self._localized(CHAT_ATTACH_IMAGE_LABELS),
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp);;All files (*)",
        )
        if not path:
            return

        try:
            data_url = _encode_image_data_url(Path(path))
        except ValueError as exc:
            if str(exc) == "image_too_large":
                self._append_bubu_message(self._localized(CHAT_IMAGE_TOO_LARGE_LABELS))
            else:
                self._append_bubu_message(self._localized(CHAT_IMAGE_UNSUPPORTED_LABELS))
            return

        self._pending_image_data_url = data_url
        self._pending_image_name = Path(path).name
        self._attachment_row.setVisible(True)
        self._update_attach_button_state()

    def _clear_pending_image(self) -> None:
        self._pending_image_data_url = None
        self._pending_image_name = None
        self._attachment_row.setVisible(False)
        self._update_attach_button_state()

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        self._attach_button.setEnabled(not busy)
        self._model_picker.setEnabled(not busy)
        self._language_picker.setEnabled(not busy)
        if busy:
            self._send_button.setText("...")
        else:
            self._send_button.setText(
                CHAT_SEND_LABELS.get(self._language, CHAT_SEND_LABELS["en"])
            )

    def _send_message(self) -> None:
        text = self._input.text().strip()
        has_image = self._pending_image_data_url is not None
        if (not text and not has_image) or self._worker is not None:
            return

        image_data_urls = [self._pending_image_data_url] if has_image else None
        display_text = text or self._localized(CHAT_IMAGE_ONLY_LABELS)

        self._input.clear()
        self._clear_pending_image()
        self._append_user_message(display_text, image_data_urls)
        self._sync_system_prompt()
        self._history.append(ChatMessage("user", text, image_data_urls))
        self._trim_history()
        self._set_busy(True)
        self._streaming_reply = ""
        self._render_transcript()

        self._worker = ChatWorker(list(self._history), self._model, parent=self)
        self._worker.chunk_received.connect(self._on_reply_chunk)
        self._worker.finished.connect(self._on_reply)
        self._worker.failed.connect(self._on_error)
        self._worker.finished.connect(self._clear_worker)
        self._worker.failed.connect(self._clear_worker)
        self._worker.start()

    def _trim_history(self) -> None:
        """Keep the system prompt plus the most recent turns."""
        system = self._history[:1]
        turns = self._history[1:]
        if len(turns) > CHAT_MAX_HISTORY:
            turns = turns[-CHAT_MAX_HISTORY:]
        self._history = system + turns

    def _on_reply_chunk(self, chunk: str) -> None:
        self._streaming_reply += chunk
        self._render_transcript()

    def _on_reply(self, reply: str) -> None:
        self._history.append(ChatMessage("assistant", reply))
        self._streaming_reply = ""
        self._append_bubu_message(reply)
        self._set_busy(False)
        self._input.setFocus()

    def _error_reply_prefix(self) -> str:
        prefixes = {
            "en": "Sorry, I couldn't reply right now.",
            "zh-Hans": "抱歉，我现在无法回复。",
            "zh-Hant": "抱歉，我現在無法回覆。",
        }
        return prefixes.get(self._language, prefixes["en"])

    def _on_error(self, message: str) -> None:
        if self._streaming_reply:
            partial_reply = self._streaming_reply
            self._streaming_reply = ""
            self._append_bubu_message(partial_reply)
        self._append_bubu_message(f"{self._error_reply_prefix()} {message}")
        self._set_busy(False)
        self._input.setFocus()

    def _clear_worker(self, _message: str = "") -> None:
        self._worker = None

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(2000)
        if self._pet is not None:
            self._pet.end_chat_hold()
            self._pet = None
        ChatWindow._instance = None
        super().closeEvent(event)
