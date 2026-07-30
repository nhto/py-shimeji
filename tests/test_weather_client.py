"""Unit tests for HKO weather parsing and formatting."""

from __future__ import annotations

from weather_client import (
    CurrentWeather,
    SpecialWeatherTip,
    WeatherWarning,
    hko_lang_from_ui_language,
    parse_current_weather,
    parse_special_tips,
    parse_warnings,
    tip_fingerprint,
    warning_state_key,
)
from weather_text import (
    format_hourly_weather,
    format_special_tip_notification,
    format_warning_notification,
)


def test_hko_lang_from_ui_language() -> None:
    assert hko_lang_from_ui_language("en") == "en"
    assert hko_lang_from_ui_language("zh-Hans") == "sc"
    assert hko_lang_from_ui_language("zh-Hant") == "tc"


def test_parse_current_weather_reads_place_and_forecast() -> None:
    rhrread = {
        "temperature": {
            "data": [
                {"place": "Hong Kong Observatory", "value": 28, "unit": "C"},
            ]
        },
        "humidity": {
            "data": [
                {"place": "Hong Kong Observatory", "value": 82, "unit": "percent"},
            ]
        },
        "updateTime": "2026-07-30T09:00:00+08:00",
    }
    flw = {"forecastDesc": "Mainly cloudy with showers."}
    weather = parse_current_weather(rhrread, flw, place="Hong Kong Observatory")
    assert weather is not None
    assert weather.temperature_c == 28
    assert weather.humidity_pct == 82
    assert "cloudy" in weather.forecast_desc


def test_parse_warnings_and_tips() -> None:
    warnsum = {
        "WRAIN": {
            "name": "Rainstorm Warning Signal",
            "code": "WRAIN",
            "actionCode": "ISSUE",
            "issueTime": "2026-07-30T08:00:00+08:00",
            "updateTime": "2026-07-30T08:00:00+08:00",
        }
    }
    swt_payload = {
        "swt": [
            {
                "desc": "Thunderstorms may affect Hong Kong.",
                "updateTime": "2026-07-30T09:00:00+08:00",
            }
        ]
    }
    warnings = parse_warnings(warnsum)
    tips = parse_special_tips(swt_payload)
    assert len(warnings) == 1
    assert warnings[0].name.startswith("Rainstorm")
    assert len(tips) == 1
    assert "Thunderstorms" in tips[0].desc


def test_format_hourly_weather_includes_readings() -> None:
    weather = CurrentWeather(
        place="Hong Kong Observatory",
        temperature_c=29,
        humidity_pct=80,
        forecast_desc="Sunny periods.",
        update_time="2026-07-30T09:00:00+08:00",
    )
    text = format_hourly_weather(weather)
    assert "29°C" in text
    assert "80%" in text
    assert "HKO" in text
    assert "Sunny" in text


def test_format_warning_and_tip_notifications() -> None:
    warning = WeatherWarning(
        code="WRAIN",
        name="Rainstorm Warning Signal",
        action_code="ISSUE",
        issue_time="",
        update_time="2026-07-30T08:00:00+08:00",
    )
    tip = SpecialWeatherTip(
        desc="Heavy rain expected.",
        update_time="2026-07-30T09:00:00+08:00",
    )
    assert "issued" in format_warning_notification(warning)
    assert "Heavy rain" in format_special_tip_notification(tip)
    assert warning_state_key(warning).startswith("WRAIN|")
    assert tip_fingerprint(tip).startswith("2026-07-30T09:00:00+08:00|")
