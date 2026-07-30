"""Poll HKO weather data and notify pets on the hour and for new warnings."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

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
from weather_client import (
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

        self._hour_check_timer = QTimer(self)
        self._hour_check_timer.timeout.connect(self._check_hourly_schedule)
        self._warning_timer = QTimer(self)
        self._warning_timer.timeout.connect(self._poll_warnings)

        self.weather_report.connect(self._on_weather_report)
        self.warning_alert.connect(self._on_warning_alert)

    def set_tray_notifier(self, notifier: TrayNotifier | None) -> None:
        self._tray_notifier = notifier

    def start(self) -> None:
        if self._running or not get_weather_enabled():
            return
        self._running = True
        self._warning_baseline_pending = True
        self._restart_timers()
        self._check_hourly_schedule()
        self._poll_warnings()

    def stop(self) -> None:
        self._running = False
        self._hour_check_timer.stop()
        self._warning_timer.stop()
        self._cancel_worker()

    def shutdown(self) -> None:
        self.stop()

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
        self._queue_poll(include_current=True, include_warnings=False)

    def _poll_warnings(self) -> None:
        if not self._running or not get_weather_enabled():
            return
        self._queue_poll(include_current=False, include_warnings=True)

    def _queue_poll(self, *, include_current: bool, include_warnings: bool) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._pending_include_current = self._pending_include_current or include_current
            self._pending_include_warnings = (
                self._pending_include_warnings or include_warnings
            )
            return
        self._start_worker(
            include_current=include_current,
            include_warnings=include_warnings,
        )

    def _start_worker(self, *, include_current: bool, include_warnings: bool) -> None:
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
            self._pending_include_current = False
            self._pending_include_warnings = False
            self._start_worker(
                include_current=include_current,
                include_warnings=include_warnings,
            )

    def _on_poll_failed(self, _message: str) -> None:
        return

    def _on_poll_complete(self, result: object) -> None:
        if not isinstance(result, WeatherPollResult):
            return
        if result.current is not None:
            hourly_key = datetime.now().strftime("%Y-%m-%dT%H")
            set_weather_last_hourly_key(hourly_key)
            text = format_hourly_weather(result.current)
            _logger.info("Hourly weather: %s", text.replace("\n", " · "))
            self.weather_report.emit(text)
        if result.warnings or result.tips:
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
        alerts: list[str] = []

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
                if warning.action_code.upper() == "CANCEL":
                    alerts.append(format_warning_notification(warning))
                else:
                    alerts.append(format_warning_notification(warning))
                known_warnings[key] = key
                warnings_changed = True

            for tip in tips:
                fingerprint = tip_fingerprint(tip)
                if fingerprint in known_swt_set:
                    continue
                alerts.append(format_special_tip_notification(tip))
                known_swt.append(fingerprint)
                known_swt_set.add(fingerprint)
                swt_changed = True

        if warnings_changed:
            set_weather_known_warnings(known_warnings)
        if swt_changed:
            set_weather_known_swt(known_swt[-_MAX_KNOWN_SWT:])

        for alert in alerts:
            _logger.info("Weather alert: %s", alert.replace("\n", " · "))
            self.warning_alert.emit(alert)

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

    def _notify(
        self,
        text: str,
        *,
        tray_title: str = "Weather",
    ) -> None:
        pet = self._pick_notify_pet()
        bubble_text = format_speech_bubble_text(text)
        if bubble_text is not None and self._should_show_bubble(pet) and pet is not None:
            pet.show_speech_bubble(bubble_text)
        elif self._tray_notifier is not None:
            self._tray_notifier(tray_title, text)

    def _on_weather_report(self, text: str) -> None:
        self._notify(text)

    def _on_warning_alert(self, text: str) -> None:
        self._notify(text)
