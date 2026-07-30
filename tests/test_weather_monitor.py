"""Unit tests for weather monitor scheduling and alert deduplication."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from weather_client import (
    CurrentWeather,
    SpecialWeatherTip,
    WeatherPollResult,
    WeatherWarning,
    tip_fingerprint,
    warning_state_key,
)
from weather_monitor import WeatherMonitor


def _sample_warning() -> WeatherWarning:
    return WeatherWarning(
        code="WTS",
        name="Thunderstorm Warning",
        action_code="ISSUE",
        issue_time="2026-07-30T08:00:00+08:00",
        update_time="2026-07-30T08:00:00+08:00",
    )


def _sample_tip() -> SpecialWeatherTip:
    return SpecialWeatherTip(
        desc="Thunderstorms are expected.",
        update_time="2026-07-30T09:00:00+08:00",
    )


@patch("weather_monitor.set_weather_known_swt")
@patch("weather_monitor.get_weather_known_swt", return_value=[])
@patch("weather_monitor.set_weather_known_warnings")
@patch("weather_monitor.get_weather_known_warnings", return_value={})
def test_process_warnings_baseline_does_not_emit(
    _get_warnings,
    set_warnings,
    _get_swt,
    set_swt,
    qapp,
) -> None:
    monitor = WeatherMonitor(pets=[], parent=None)
    alerts: list[str] = []
    monitor.warning_alert.connect(alerts.append)

    warning = _sample_warning()
    tip = _sample_tip()
    monitor._process_warnings([warning], [tip])

    assert alerts == []
    set_warnings.assert_called_once()
    set_swt.assert_called_once()
    assert warning_state_key(warning) in set_warnings.call_args.args[0]
    assert tip_fingerprint(tip) in set_swt.call_args.args[0]


@patch("weather_monitor.set_weather_known_swt")
@patch("weather_monitor.get_weather_known_swt", return_value=[])
@patch("weather_monitor.set_weather_known_warnings", return_value=None)
@patch(
    "weather_monitor.get_weather_known_warnings",
    return_value={},
)
@patch("weather_monitor.get_chat_language", return_value="en")
def test_process_warnings_notifies_with_view_on_hko_action(
    _get_lang,
    _get_warnings,
    _set_warnings,
    _get_swt,
    _set_swt,
    qapp,
) -> None:
    pet = MagicMock()
    pet.isVisible.return_value = True
    pet.motion_paused = False
    monitor = WeatherMonitor(pets=[pet], parent=None)
    monitor._warning_baseline_pending = False
    monitor._should_show_bubble = MagicMock(return_value=True)  # type: ignore[method-assign]

    monitor._process_warnings([_sample_warning()], [])

    pet.show_speech_bubble.assert_called_once()
    _args, kwargs = pet.show_speech_bubble.call_args
    actions = kwargs.get("actions")
    assert actions is not None
    assert len(actions) == 1
    assert actions[0][0] == "View on HKO"
    assert callable(actions[0][1])


@patch("weather_monitor.set_weather_known_swt")
@patch("weather_monitor.get_weather_known_swt", return_value=[])
@patch("weather_monitor.set_weather_known_warnings", return_value=None)
@patch(
    "weather_monitor.get_weather_known_warnings",
    return_value={},
)
def test_process_warnings_emits_new_tip_after_baseline(
    _get_warnings,
    _set_warnings,
    _get_swt,
    _set_swt,
    qapp,
) -> None:
    monitor = WeatherMonitor(pets=[], parent=None)
    monitor._warning_baseline_pending = False
    alerts: list[str] = []
    monitor.warning_alert.connect(alerts.append)

    monitor._process_warnings([], [_sample_tip()])

    assert len(alerts) == 1
    assert "Thunderstorms" in alerts[0]


@patch("weather_monitor.set_weather_last_hourly_key")
@patch("weather_monitor.get_weather_last_hourly_key", return_value="")
def test_on_poll_complete_emits_hourly_report(
    _last_key,
    set_last_key,
    qapp,
) -> None:
    monitor = WeatherMonitor(pets=[], parent=None)
    monitor._worker_notify_hourly = True
    reports: list[str] = []
    monitor.weather_report.connect(reports.append)

    result = WeatherPollResult(
        current=CurrentWeather(
            place="Hong Kong Observatory",
            temperature_c=27,
            humidity_pct=75,
            forecast_desc="Fine.",
            update_time="2026-07-30T09:00:00+08:00",
        ),
        warnings=[],
        tips=[],
    )
    monitor._on_poll_complete(result)

    assert len(reports) == 1
    assert "27°C" in reports[0]
    set_last_key.assert_called_once()
    assert monitor._last_current is not None
    assert monitor._last_current.temperature_c == 27


@patch("weather_monitor.set_weather_last_hourly_key")
@patch("weather_monitor.get_weather_last_hourly_key", return_value="")
def test_on_poll_complete_seeds_current_without_hourly_notify(
    _last_key,
    set_last_key,
    qapp,
) -> None:
    monitor = WeatherMonitor(pets=[], parent=None)
    monitor._worker_notify_hourly = False
    reports: list[str] = []
    monitor.weather_report.connect(reports.append)

    result = WeatherPollResult(
        current=CurrentWeather(
            place="Hong Kong Observatory",
            temperature_c=27,
            humidity_pct=75,
            forecast_desc="Fine.",
            update_time="2026-07-30T09:00:00+08:00",
        ),
        warnings=[],
        tips=[],
    )
    monitor._on_poll_complete(result)

    assert reports == []
    set_last_key.assert_not_called()
    assert monitor._last_current is not None


@patch("weather_monitor.get_weather_enabled", return_value=True)
@patch("weather_monitor.get_weather_last_hourly_key", return_value="2026-07-30T09")
def test_check_hourly_schedule_skips_same_hour(
    _last_key,
    _enabled,
    qapp,
) -> None:
    monitor = WeatherMonitor(pets=[], parent=None)
    monitor._running = True
    monitor._queue_poll = MagicMock()  # type: ignore[method-assign]

    with patch("weather_monitor.datetime") as mock_datetime:
        mock_datetime.now.return_value = MagicMock(minute=0)
        mock_datetime.now.return_value.strftime.return_value = "2026-07-30T09"
        monitor._check_hourly_schedule()

    monitor._queue_poll.assert_not_called()
