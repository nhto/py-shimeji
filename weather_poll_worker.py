"""Background fetch of HKO weather data."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from weather_client import WeatherPollResult, fetch_weather_poll, is_transient_fetch_error, log_fetch_error

_logger = logging.getLogger(__name__)


class WeatherPollWorker(QThread):
    """Fetch current weather and/or warnings without blocking the UI thread."""

    poll_complete = pyqtSignal(object)
    poll_failed = pyqtSignal(str)

    def __init__(
        self,
        *,
        place: str,
        lang: str,
        include_current: bool,
        include_warnings: bool,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._place = place
        self._lang = lang
        self._include_current = include_current
        self._include_warnings = include_warnings

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            result = fetch_weather_poll(
                place=self._place,
                lang=self._lang,
                include_current=self._include_current,
                include_warnings=self._include_warnings,
            )
        except Exception as exc:  # noqa: BLE001 — surface to UI
            if is_transient_fetch_error(exc):
                log_fetch_error("poll", exc)
                self.poll_failed.emit(str(exc))
                return
            _logger.exception("Unexpected HKO weather fetch error")
            self.poll_failed.emit(str(exc))
            return
        if self.isInterruptionRequested():
            return
        self.poll_complete.emit(result)
