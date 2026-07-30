"""Format HKO weather data for speech bubbles."""

from __future__ import annotations

from settings.core import SPEECH_BUBBLE_MAX_CHARS
from weather_client import CurrentWeather, SpecialWeatherTip, WeatherWarning


def _truncate(text: str, max_len: int) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_len:
        return collapsed
    if max_len <= 1:
        return collapsed[:max_len]
    return collapsed[: max_len - 1].rstrip() + "…"


def _short_place(place: str) -> str:
    aliases = {
        "Hong Kong Observatory": "HKO",
    }
    return aliases.get(place, place)


def format_hourly_weather(weather: CurrentWeather) -> str:
    parts: list[str] = []
    if weather.temperature_c is not None:
        parts.append(f"{weather.temperature_c}°C")
    if weather.humidity_pct is not None:
        parts.append(f"{weather.humidity_pct}%")
    place = _short_place(weather.place)
    header = f"🌤️ {' · '.join(parts)} · {place}" if parts else f"🌤️ {place}"
    if weather.forecast_desc:
        body_budget = max(40, SPEECH_BUBBLE_MAX_CHARS - len(header) - 1)
        body = _truncate(weather.forecast_desc, body_budget)
        return f"{header}\n{body}"
    return header


def format_warning_notification(warning: WeatherWarning) -> str:
    action = warning.action_code.upper()
    if action == "CANCEL":
        prefix = "✅"
        verb = "cancelled"
    elif action == "ISSUE":
        prefix = "⚠️"
        verb = "issued"
    else:
        prefix = "⚠️"
        verb = "updated"
    line = f"{prefix} {warning.name} {verb}"
    return _truncate(line, SPEECH_BUBBLE_MAX_CHARS)


def format_special_tip_notification(tip: SpecialWeatherTip) -> str:
    line = f"⚠️ {_truncate(tip.desc, SPEECH_BUBBLE_MAX_CHARS - 2)}"
    return _truncate(line, SPEECH_BUBBLE_MAX_CHARS)
