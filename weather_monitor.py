"""Poll HKO weather data and notify pets on the hour and for new warnings."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config import (
    WEATHER_NOTIFY_PET_FIRST_VISIBLE,
    get_chat_language,
    get_weather_enabled,
    get_weather_known_swt,
    get_weather_known_warnings,
    get_weather_last_hourly_key,
    get_weather_location,
    get_weather_notify_pet_index,
    get_weather_notify_when_paused,
    get_weather_warning_poll_interval_sec,
    set_weather_known_swt,
    set_weather_known_warnings,
    set_weather_last_hourly_key,
)
from pet_window import PetWindow
from settings.core import format_speech_bubble_text
from chat_context import format_weather_chat_context
from weather_actions import open_hko_warning, open_hko_warnings_today
from weather_client import (
    CurrentWeather,
    SpecialWeatherTip,
    WeatherPollResult,
    WeatherWarning,
    hko_lang_from_ui_language,
    tip_fingerprint,
    warning_state_key,
)
from weather_poll_worker import WeatherPollWorker
from weather_text import (
    format_hourly_weather,
    format_special_tip_notification,
    format_warning_notification,
)

BubbleActions = list[tuple[str, Callable[[], None]]]

TrayNotifier = Callable[[str, str], None]
_logger = logging.getLogger(__name__)
_MAX_KNOWN_SWT = 50


class WeatherMonitor(QObject):
    """Timer-driven HKO polling with hourly reports and warning alerts."""

    weather_report = pyqtSignal(str)
    warning_alert = pyqtSignal(str)

    def __init__(
        self,
        pets: list[PetWindow],
        *,
        tray_notifier: TrayNotifier | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pets = pets
        self._tray_notifier = tray_notifier
        self._running = False
        self._warning_baseline_pending = True
        self._worker: WeatherPollWorker | None = None
        self._pending_include_current = False
        self._pending_include_warnings = False
        self._pending_notify_hourly = False
        self._worker_include_warnings = False
        self._worker_notify_hourly = False
        self._last_current: CurrentWeather | None = None
        self._active_warnings: list[WeatherWarning] = []
        self._active_tips: list[SpecialWeatherTip] = []

        self._hour_check_timer = QTimer(self)
        self._hour_check_timer.timeout.connect(self._check_hourly_schedule)
        self._warning_timer = QTimer(self)
        self._warning_timer.timeout.connect(self._poll_warnings)

        self.weather_report.connect(self._on_weather_report)

    def set_tray_notifier(self, notifier: TrayNotifier | None) -> None:
        self._tray_notifier = notifier

    def start(self) -> None:
        if self._running or not get_weather_enabled():
            return
        self._running = True
        self._warning_baseline_pending = True
        self._restart_timers()
        self._check_hourly_schedule()
        # Seed chat context with current conditions + warnings on start.
        self._queue_poll(include_current=True, include_warnings=True)

    def stop(self) -> None:
        self._running = False
        self._hour_check_timer.stop()
        self._warning_timer.stop()
        self._cancel_worker()

    def shutdown(self) -> None:
        self.stop()

    def chat_context(self) -> str | None:
        """Return a short live weather snapshot for the chat system prompt."""
        return format_weather_chat_context(
            enabled=get_weather_enabled(),
            current=self._last_current,
            warnings=self._active_warnings,
            tips=self._active_tips,
        )

    def restart(self) -> None:
        if not self._running:
            return
        self._restart_timers()

    def _restart_timers(self) -> None:
        self._hour_check_timer.start(60_000)
        warning_ms = max(1, get_weather_warning_poll_interval_sec()) * 1000
        self._warning_timer.start(warning_ms)

    def _check_hourly_schedule(self) -> None:
        if not self._running or not get_weather_enabled():
            return
        now = datetime.now()
        if now.minute != 0:
            return
        hourly_key = now.strftime("%Y-%m-%dT%H")
        if hourly_key == get_weather_last_hourly_key():
            return
        self._queue_poll(
            include_current=True,
            include_warnings=False,
            notify_hourly=True,
        )

    def _poll_warnings(self) -> None:
        if not self._running or not get_weather_enabled():
            return
        self._queue_poll(include_current=False, include_warnings=True)

    def _queue_poll(
        self,
        *,
        include_current: bool,
        include_warnings: bool,
        notify_hourly: bool = False,
    ) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._pending_include_current = self._pending_include_current or include_current
            self._pending_include_warnings = (
                self._pending_include_warnings or include_warnings
            )
            self._pending_notify_hourly = self._pending_notify_hourly or notify_hourly
            return
        self._start_worker(
            include_current=include_current,
            include_warnings=include_warnings,
            notify_hourly=notify_hourly,
        )

    def _start_worker(
        self,
        *,
        include_current: bool,
        include_warnings: bool,
        notify_hourly: bool = False,
    ) -> None:
        self._worker_include_warnings = include_warnings
        self._worker_notify_hourly = notify_hourly
        self._worker = WeatherPollWorker(
            place=get_weather_location(),
            lang=hko_lang_from_ui_language(get_chat_language()),
            include_current=include_current,
            include_warnings=include_warnings,
            parent=self,
        )
        self._worker.poll_complete.connect(self._on_poll_complete)
        self._worker.poll_failed.connect(self._on_poll_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _disconnect_worker(self, worker: WeatherPollWorker) -> None:
        for signal, slot in (
            (worker.poll_complete, self._on_poll_complete),
            (worker.poll_failed, self._on_poll_failed),
            (worker.finished, self._on_worker_finished),
        ):
            try:
                signal.disconnect(slot)
            except TypeError:
                pass

    def _cancel_worker(self) -> None:
        if self._worker is None:
            return

        worker = self._worker
        self._worker = None
        self._pending_include_current = False
        self._pending_include_warnings = False
        self._pending_notify_hourly = False
        self._disconnect_worker(worker)

        if worker.isRunning():
            worker.requestInterruption()
            if not worker.wait(10_000):
                worker.terminate()
                worker.wait(2_000)
        worker.deleteLater()

    def _on_worker_finished(self) -> None:
        worker = self.sender()
        if not isinstance(worker, WeatherPollWorker):
            worker = self._worker
        if worker is self._worker:
            self._worker = None
        if worker is not None:
            worker.deleteLater()
        if not self._running:
            return
        if self._pending_include_current or self._pending_include_warnings:
            include_current = self._pending_include_current
            include_warnings = self._pending_include_warnings
            notify_hourly = self._pending_notify_hourly
            self._pending_include_current = False
            self._pending_include_warnings = False
            self._pending_notify_hourly = False
            self._start_worker(
                include_current=include_current,
                include_warnings=include_warnings,
                notify_hourly=notify_hourly,
            )

    def _on_poll_failed(self, _message: str) -> None:
        return

    def _on_poll_complete(self, result: object) -> None:
        if not isinstance(result, WeatherPollResult):
            return
        if result.current is not None:
            self._last_current = result.current
            if self._worker_notify_hourly:
                hourly_key = datetime.now().strftime("%Y-%m-%dT%H")
                set_weather_last_hourly_key(hourly_key)
                text = format_hourly_weather(result.current)
                _logger.info("Hourly weather: %s", text.replace("\n", " · "))
                self.weather_report.emit(text)
        if self._worker_include_warnings:
            self._active_warnings = list(result.warnings)
            self._active_tips = list(result.tips)
            self._process_warnings(result.warnings, result.tips)

    def _process_warnings(
        self,
        warnings: list[WeatherWarning],
        tips: list[SpecialWeatherTip],
    ) -> None:
        known_warnings = dict(get_weather_known_warnings())
        known_swt = list(get_weather_known_swt())
        known_swt_set = set(known_swt)
        warnings_changed = False
        swt_changed = False
        alerts: list[tuple[str, BubbleActions | None]] = []
        language = get_chat_language()

        current_warning_keys = {
            warning_state_key(warning): warning for warning in warnings
        }

        if self._warning_baseline_pending:
            self._warning_baseline_pending = False
            if current_warning_keys != known_warnings:
                known_warnings = dict(current_warning_keys)
                warnings_changed = True
            new_swt = [tip_fingerprint(tip) for tip in tips]
            if new_swt != known_swt:
                known_swt = new_swt
                swt_changed = True
        else:
            for key, warning in current_warning_keys.items():
                if key in known_warnings:
                    continue
                alerts.append(
                    (
                        format_warning_notification(warning),
                        self._warning_bubble_actions(warning, language=language),
                    )
                )
                known_warnings[key] = key
                warnings_changed = True

            for tip in tips:
                fingerprint = tip_fingerprint(tip)
                if fingerprint in known_swt_set:
                    continue
                alerts.append(
                    (
                        format_special_tip_notification(tip),
                        self._special_tip_bubble_actions(language=language),
                    )
                )
                known_swt.append(fingerprint)
                known_swt_set.add(fingerprint)
                swt_changed = True

        if warnings_changed:
            set_weather_known_warnings(known_warnings)
        if swt_changed:
            set_weather_known_swt(known_swt[-_MAX_KNOWN_SWT:])

        for text, bubble_actions in alerts:
            _logger.info("Weather alert: %s", text.replace("\n", " · "))
            self.warning_alert.emit(text)
            self._notify(text, bubble_actions=bubble_actions)

    def _pick_notify_pet(self) -> PetWindow | None:
        index = get_weather_notify_pet_index()
        if index != WEATHER_NOTIFY_PET_FIRST_VISIBLE and 0 <= index < len(self._pets):
            return self._pets[index]
        for pet in self._pets:
            if pet.isVisible():
                return pet
        return self._pets[0] if self._pets else None

    def _should_show_bubble(self, pet: PetWindow | None) -> bool:
        if pet is None or not pet.isVisible():
            return False
        if pet.motion_paused and not get_weather_notify_when_paused():
            return False
        return True

    def _warning_bubble_actions(
        self,
        warning: WeatherWarning,
        *,
        language: str,
    ) -> BubbleActions:
        return [
            (
                "View on HKO",
                lambda item=warning, lang=language: open_hko_warning(
                    item,
                    language=lang,
                ),
            )
        ]

    def _special_tip_bubble_actions(self, *, language: str) -> BubbleActions:
        return [
            (
                "View on HKO",
                lambda lang=language: open_hko_warnings_today(language=lang),
            )
        ]

    def _notify(
        self,
        text: str,
        *,
        tray_title: str = "Weather",
        bubble_actions: BubbleActions | None = None,
    ) -> None:
        pet = self._pick_notify_pet()
        bubble_text = format_speech_bubble_text(text)
        if bubble_text is not None and self._should_show_bubble(pet) and pet is not None:
            pet.show_speech_bubble(bubble_text, actions=bubble_actions)
        elif self._tray_notifier is not None:
            self._tray_notifier(tray_title, text)

    def _on_weather_report(self, text: str) -> None:
        self._notify(text)
