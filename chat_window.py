"""Pop-up chat window for talking with Bubu via OpenRouter."""

from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QThread, QTimer, pyqtSignal
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
    CHAT_CLEAR_HISTORY_LABELS,
    CHAT_GREETINGS,
    CHAT_IMAGE_ONLY_LABELS,
    CHAT_IMAGE_TOO_LARGE_LABELS,
    CHAT_IMAGE_UNSUPPORTED_LABELS,
    CHAT_INPUT_PLACEHOLDERS,
    CHAT_LANGUAGES,
    CHAT_MAX_HISTORY,
    CHAT_MAX_IMAGE_BYTES,
    CHAT_MODELS,
    CHAT_NO_API_KEY_GREETINGS,
    CHAT_NO_API_KEY_SEND_LABELS,
    CHAT_SEND_LABELS,
    CHAT_STATUS_OFFLINE_LABELS,
    CHAT_STATUS_ONLINE_LABELS,
    CHAT_STATUS_TYPING_LABELS,
    CHAT_TYPING_INTERVAL_MS,
    CHAT_TYPING_PHRASE_LABELS,
    CHAT_WINDOW_GAP_PX,
    CHAT_WINDOW_HEIGHT,
    CHAT_WINDOW_TITLE_LABELS,
    CHAT_WINDOW_WIDTH,
    OPENROUTER_API_URL,
    build_chat_system_prompt,
    chat_model_supports_images,
    get_chat_language,
    get_chat_model,
    get_openrouter_api_key,
    get_pet_name,
    has_openrouter_api_key,
    localized_with_pet,
    set_chat_language,
    set_chat_model,
)
from dialog_theme import (
    CHAT_BUBU_BORDER,
    CHAT_BUBU_BUBBLE_BG,
    CHAT_BUBU_BUBBLE_FG,
    CHAT_BUBU_LABEL_COLOR,
    CHAT_BUBU_STREAMING_BORDER,
    CHAT_TYPING_BUBBLE_BG,
    CHAT_TYPING_BUBBLE_BORDER,
    CHAT_TYPING_LABEL_COLOR,
    CHAT_TYPING_TEXT_COLOR,
    CHAT_USER_BORDER,
    CHAT_USER_BUBBLE_BG,
    CHAT_USER_BUBBLE_FG,
    CHAT_USER_LABEL_COLOR,
    STATUS_OFFLINE_COLOR,
    STATUS_ONLINE_COLOR,
    STATUS_TYPING_COLOR,
    apply_light_chat_theme,
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
        if not has_openrouter_api_key():
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
                "Authorization": f"Bearer {get_openrouter_api_key()}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/nhto/py-shimeji",
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
        self._pet_name = get_pet_name()
        self._history: list[ChatMessage] = [
            ChatMessage("system", build_chat_system_prompt(self._language)),
        ]
        self._messages: list[ChatMessage] = []
        self._worker: ChatWorker | None = None
        self._model = get_chat_model()
        self._streaming_reply = ""
        self._pending_image_data_url: str | None = None
        self._pending_image_name: str | None = None
        self._busy = False
        self._typing_phase = 0
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(CHAT_TYPING_INTERVAL_MS)
        self._typing_timer.timeout.connect(self._on_typing_tick)
        self._setup_window()
        self._build_ui()
        self._update_api_key_state()
        if has_openrouter_api_key():
            self._append_assistant_message(self._greeting_text())
        else:
            self._append_assistant_message(self._no_api_key_greeting_text())

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
        cls._instance._update_api_key_state()
        cls._instance._input.setFocus()
        return cls._instance

    @classmethod
    def refresh_preferences_state(cls) -> None:
        """Update the open chat window after preferences change."""
        if cls._instance is not None:
            cls._instance._sync_language_from_settings()
            cls._instance._update_api_key_state()

    @classmethod
    def refresh_pet_name(cls) -> None:
        """Update the open chat window after the pet name changes."""
        if cls._instance is not None:
            cls._instance._sync_pet_name_from_settings()

    @classmethod
    def refresh_api_key_state(cls) -> None:
        """Backward-compatible alias for :meth:`refresh_preferences_state`."""
        cls.refresh_preferences_state()

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
        self.setWindowTitle(localized_with_pet(CHAT_WINDOW_TITLE_LABELS, self._language))
        self.setFixedSize(CHAT_WINDOW_WIDTH, CHAT_WINDOW_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        apply_light_chat_theme(self)

    def _pet_avatar_letter(self) -> str:
        return self._pet_name[:1].upper() or "?"

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

        avatar = QLabel(self._pet_avatar_letter())
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "background-color: #f97316; color: #ffffff; border-radius: 18px; font-weight: 700;"
        )
        self._avatar = avatar

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title = QLabel(self._pet_name)
        title.setObjectName("chatTitle")
        self._title_label = title
        subtitle_row = QHBoxLayout()
        subtitle_row.setSpacing(6)
        status = QLabel("●")
        status.setObjectName("statusDot")
        subtitle = QLabel("Online")
        subtitle.setObjectName("chatSubtitle")
        self._status_dot = status
        self._status_subtitle = subtitle
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

        self._loading_bar = QFrame()
        self._loading_bar.setObjectName("loadingBar")
        self._loading_bar.setFixedHeight(3)
        self._loading_bar.setVisible(False)
        card_layout.addWidget(self._loading_bar)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 12, 14, 14)
        body_layout.setSpacing(12)

        transcript_toolbar = QHBoxLayout()
        transcript_toolbar.setContentsMargins(0, 0, 0, 0)
        transcript_toolbar.addStretch()
        self._clear_history_button = QPushButton(
            self._localized(CHAT_CLEAR_HISTORY_LABELS)
        )
        self._clear_history_button.setObjectName("clearHistoryButton")
        self._clear_history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_history_button.clicked.connect(self._clear_chat_history)
        transcript_toolbar.addWidget(self._clear_history_button)
        body_layout.addLayout(transcript_toolbar)

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
        self._update_clear_history_button_state()

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

    def _append_assistant_message(self, text: str) -> None:
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
            bubbles.append(
                self._build_bubble(self._streaming_reply, is_user=False, streaming=True)
            )
        elif self._busy:
            bubbles.append(self._build_typing_bubble())

        self._transcript.setHtml("".join(bubbles))
        scrollbar = self._transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _build_bubble(
        self,
        text: str,
        *,
        is_user: bool,
        image_data_urls: list[str] | None = None,
        streaming: bool = False,
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
            label_color = CHAT_USER_LABEL_COLOR
            bubble_bg = CHAT_USER_BUBBLE_BG
            bubble_fg = CHAT_USER_BUBBLE_FG
            border = CHAT_USER_BORDER
        else:
            sender = self._pet_name
            align = "left"
            label_color = CHAT_BUBU_LABEL_COLOR
            bubble_bg = CHAT_BUBU_BUBBLE_BG
            bubble_fg = CHAT_BUBU_BUBBLE_FG
            border = CHAT_BUBU_BORDER
            if streaming:
                border = CHAT_BUBU_STREAMING_BORDER

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

    def _build_typing_bubble(self) -> str:
        """Animated thinking indicator shown before the first streamed token."""
        phase = self._typing_phase % 3
        dots: list[str] = []
        for index in range(3):
            active = index == phase
            opacity = "1" if active else "0.22"
            size = "11px" if active else "8px"
            dots.append(
                f'<span style="color:#f97316; opacity:{opacity}; font-size:{size};">'
                f"●</span>"
            )
        dots_html = "&nbsp;".join(dots)
        phrase = localized_with_pet(CHAT_TYPING_PHRASE_LABELS, self._language)

        return (
            f'<table width="100%" cellspacing="0" cellpadding="0" '
            f'style="margin-bottom:14px;">'
            f'<tr><td align="left" style="padding:0 4px;">'
            f'<span style="font-size:10px; font-weight:600; color:{CHAT_TYPING_LABEL_COLOR};">'
            f"{self._pet_name}</span><br/>"
            f'<table cellspacing="0" cellpadding="0" style="margin-top:4px;">'
            f'<tr><td align="left" style="background-color:{CHAT_TYPING_BUBBLE_BG}; '
            f"{CHAT_TYPING_BUBBLE_BORDER} padding:12px 16px;\">"
            f'<span style="color:{CHAT_TYPING_TEXT_COLOR}; font-size:12px;">{phrase}</span> '
            f"{dots_html}"
            f"</td></tr></table>"
            f"</td></tr></table>"
        )

    def _on_typing_tick(self) -> None:
        self._typing_phase = (self._typing_phase + 1) % 4
        pulse = (0.35, 0.55, 0.85, 0.55)[self._typing_phase]
        self._loading_bar.setStyleSheet(
            f"background-color: rgba(249, 115, 22, {pulse});"
            " border: none; max-height: 3px; min-height: 3px;"
        )
        self._send_button.setText("." * ((self._typing_phase % 3) + 1))
        self._render_transcript()

    def _set_header_online_status(self) -> None:
        """Restore the header status when not waiting on the model."""
        if not has_openrouter_api_key():
            self._status_subtitle.setText(
                self._localized(CHAT_STATUS_OFFLINE_LABELS)
            )
            self._status_dot.setStyleSheet(f"color: {STATUS_OFFLINE_COLOR}; font-size: 10px;")
            return
        self._status_subtitle.setText(self._localized(CHAT_STATUS_ONLINE_LABELS))
        self._status_dot.setStyleSheet(f"color: {STATUS_ONLINE_COLOR}; font-size: 10px;")

    def _set_header_typing_status(self) -> None:
        self._status_subtitle.setText(self._localized(CHAT_STATUS_TYPING_LABELS))
        self._status_dot.setStyleSheet(f"color: {STATUS_TYPING_COLOR}; font-size: 10px;")

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

    def _greeting_text(self) -> str:
        return localized_with_pet(CHAT_GREETINGS, self._language)

    def _no_api_key_greeting_text(self) -> str:
        return localized_with_pet(CHAT_NO_API_KEY_GREETINGS, self._language)

    def _sync_pet_name_from_settings(self) -> None:
        name = get_pet_name()
        if name == self._pet_name:
            return
        self._pet_name = name
        self.setWindowTitle(localized_with_pet(CHAT_WINDOW_TITLE_LABELS, self._language))
        self._title_label.setText(self._pet_name)
        self._avatar.setText(self._pet_avatar_letter())
        self._sync_system_prompt()
        self._update_input_labels()
        self._render_transcript()

    def _sync_language_from_settings(self) -> None:
        language = get_chat_language()
        if language == self._language:
            return
        self._language = language
        index = self._language_picker.findData(language)
        if index >= 0:
            self._language_picker.blockSignals(True)
            self._language_picker.setCurrentIndex(index)
            self._language_picker.blockSignals(False)
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

    def _update_api_key_state(self) -> None:
        """Reflect whether OpenRouter is configured in the header and composer."""
        configured = has_openrouter_api_key()
        if self._busy:
            self._set_header_typing_status()
        elif configured:
            self._set_header_online_status()
        else:
            self._status_subtitle.setText(
                self._localized(CHAT_STATUS_OFFLINE_LABELS)
            )
            self._status_dot.setStyleSheet(f"color: {STATUS_OFFLINE_COLOR}; font-size: 10px;")

        if configured:
            self._input.setPlaceholderText(
                localized_with_pet(CHAT_INPUT_PLACEHOLDERS, self._language)
            )
        else:
            self._input.setPlaceholderText(
                self._localized(CHAT_NO_API_KEY_SEND_LABELS)
            )

        enabled = configured and not self._busy
        self._input.setEnabled(enabled)
        self._send_button.setEnabled(enabled)
        self._attach_button.setEnabled(enabled)
        self._model_picker.setEnabled(enabled)
        self._language_picker.setEnabled(True)
        self._update_clear_history_button_state()

    def _update_input_labels(self) -> None:
        self._update_api_key_state()
        self._update_attach_button_state()
        self._clear_history_button.setText(self._localized(CHAT_CLEAR_HISTORY_LABELS))
        self._update_clear_history_button_state()

    def _has_clearable_history(self) -> bool:
        return any(message.role == "user" for message in self._messages)

    def _update_clear_history_button_state(self) -> None:
        self._clear_history_button.setEnabled(self._has_clearable_history() and not self._busy)

    def _clear_chat_history(self) -> None:
        if self._busy or not self._has_clearable_history():
            return

        self._messages.clear()
        self._history = [
            ChatMessage("system", build_chat_system_prompt(self._language)),
        ]
        self._streaming_reply = ""
        self._input.clear()
        self._clear_pending_image()

        if has_openrouter_api_key():
            self._append_assistant_message(self._greeting_text())
        else:
            self._append_assistant_message(self._no_api_key_greeting_text())

        self._update_clear_history_button_state()
        self._input.setFocus()

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
                self._append_assistant_message(self._localized(CHAT_IMAGE_TOO_LARGE_LABELS))
            else:
                self._append_assistant_message(self._localized(CHAT_IMAGE_UNSUPPORTED_LABELS))
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
        self._busy = busy
        configured = has_openrouter_api_key()
        self._input.setEnabled(configured and not busy)
        self._send_button.setEnabled(configured and not busy)
        self._attach_button.setEnabled(configured and not busy)
        self._model_picker.setEnabled(configured and not busy)
        self._language_picker.setEnabled(True)
        self._loading_bar.setVisible(busy)
        self._send_button.setProperty("loading", busy)
        self._send_button.style().unpolish(self._send_button)
        self._send_button.style().polish(self._send_button)

        if busy:
            self._typing_phase = 0
            self._set_header_typing_status()
            self._typing_timer.start()
            self._on_typing_tick()
        else:
            self._typing_timer.stop()
            self._loading_bar.setStyleSheet("")
            self._set_header_online_status()
            self._send_button.setText(
                CHAT_SEND_LABELS.get(self._language, CHAT_SEND_LABELS["en"])
            )
            self._render_transcript()

        self._update_clear_history_button_state()

    def _send_message(self) -> None:
        if not has_openrouter_api_key():
            self._append_assistant_message(self._localized(CHAT_NO_API_KEY_SEND_LABELS))
            return

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
        self._update_clear_history_button_state()
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
        self._append_assistant_message(reply)
        if self._pet is not None:
            self._pet.show_speech_bubble(reply)
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
            self._append_assistant_message(partial_reply)
        self._append_assistant_message(f"{self._error_reply_prefix()} {message}")
        self._set_busy(False)
        self._input.setFocus()

    def _clear_worker(self, _message: str = "") -> None:
        self._worker = None

    def closeEvent(self, event) -> None:  # noqa: N802
        self._typing_timer.stop()
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(2000)
        if self._pet is not None:
            self._pet.end_chat_hold()
            self._pet = None
        ChatWindow._instance = None
        super().closeEvent(event)
