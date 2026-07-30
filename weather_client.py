"""Fetch and parse Hong Kong Observatory open weather data."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

_logger = logging.getLogger(__name__)

HKO_WEATHER_API_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
HKO_REQUEST_TIMEOUT_SEC = 15
HKO_USER_AGENT = "py-shimeji"


@dataclass(frozen=True)
class CurrentWeather:
    """Snapshot of current conditions for one place."""

    place: str
    temperature_c: int | None
    humidity_pct: int | None
    forecast_desc: str
    update_time: str


@dataclass(frozen=True)
class WeatherWarning:
    """Active or recently changed weather warning from HKO."""

    code: str
    name: str
    action_code: str
    issue_time: str
    update_time: str


@dataclass(frozen=True)
class SpecialWeatherTip:
    """Special weather tip bulletin."""

    desc: str
    update_time: str


@dataclass(frozen=True)
class WeatherPollResult:
    """Combined fetch result for one monitor cycle."""

    current: CurrentWeather | None
    warnings: list[WeatherWarning]
    tips: list[SpecialWeatherTip]


def hko_lang_from_ui_language(language: str) -> str:
    """Map app UI language to HKO API lang parameter."""
    normalized = language.strip().lower()
    if normalized in {"zh-hans", "zh_cn", "sc"}:
        return "sc"
    if normalized in {"zh-hant", "zh_tw", "zh-hk", "tc"}:
        return "tc"
    return "en"


def _fetch_json(data_type: str, lang: str) -> dict:
    query = f"dataType={data_type}&lang={lang}"
    url = f"{HKO_WEATHER_API_URL}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": HKO_USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=HKO_REQUEST_TIMEOUT_SEC) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError(f"HKO {data_type} response is not a JSON object")
    return payload


def _reading_for_place(entries: object, place: str) -> int | None:
    if not isinstance(entries, list):
        return None
    for item in entries:
        if not isinstance(item, dict):
            continue
        item_place = item.get("place")
        if isinstance(item_place, str) and item_place.strip() == place:
            try:
                return int(item.get("value"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return None
    return None


def parse_current_weather(
    rhrread: dict,
    flw: dict,
    *,
    place: str,
) -> CurrentWeather | None:
    temperature = _reading_for_place(rhrread.get("temperature", {}).get("data"), place)
    humidity = _reading_for_place(rhrread.get("humidity", {}).get("data"), place)
    forecast_desc = ""
    raw_desc = flw.get("forecastDesc")
    if isinstance(raw_desc, str):
        forecast_desc = raw_desc.strip()
    update_time = ""
    raw_update = rhrread.get("updateTime")
    if isinstance(raw_update, str):
        update_time = raw_update.strip()
    if temperature is None and humidity is None and not forecast_desc:
        return None
    return CurrentWeather(
        place=place,
        temperature_c=temperature,
        humidity_pct=humidity,
        forecast_desc=forecast_desc,
        update_time=update_time,
    )


def parse_warnings(warnsum: dict) -> list[WeatherWarning]:
    warnings: list[WeatherWarning] = []
    for code, item in warnsum.items():
        if not isinstance(code, str) or not isinstance(item, dict):
            continue
        name = item.get("name")
        action_code = item.get("actionCode")
        issue_time = item.get("issueTime")
        update_time = item.get("updateTime")
        warnings.append(
            WeatherWarning(
                code=code.strip(),
                name=name.strip() if isinstance(name, str) else code.strip(),
                action_code=action_code.strip().upper()
                if isinstance(action_code, str)
                else "",
                issue_time=issue_time.strip() if isinstance(issue_time, str) else "",
                update_time=update_time.strip() if isinstance(update_time, str) else "",
            )
        )
    warnings.sort(key=lambda warning: warning.code)
    return warnings


def parse_special_tips(swt_payload: dict) -> list[SpecialWeatherTip]:
    tips: list[SpecialWeatherTip] = []
    raw_tips = swt_payload.get("swt")
    if not isinstance(raw_tips, list):
        return tips
    for item in raw_tips:
        if not isinstance(item, dict):
            continue
        desc = item.get("desc")
        update_time = item.get("updateTime")
        if not isinstance(desc, str) or not desc.strip():
            continue
        tips.append(
            SpecialWeatherTip(
                desc=desc.strip(),
                update_time=update_time.strip() if isinstance(update_time, str) else "",
            )
        )
    return tips


def warning_state_key(warning: WeatherWarning) -> str:
    return f"{warning.code}|{warning.update_time}|{warning.action_code}"


def tip_fingerprint(tip: SpecialWeatherTip) -> str:
    return f"{tip.update_time}|{tip.desc}"


def fetch_current_weather(*, place: str, lang: str) -> CurrentWeather | None:
    rhrread = _fetch_json("rhrread", lang)
    flw = _fetch_json("flw", lang)
    return parse_current_weather(rhrread, flw, place=place)


def fetch_warnings_and_tips(*, lang: str) -> tuple[list[WeatherWarning], list[SpecialWeatherTip]]:
    warnsum = _fetch_json("warnsum", lang)
    swt_payload = _fetch_json("swt", lang)
    return parse_warnings(warnsum), parse_special_tips(swt_payload)


def fetch_weather_poll(
    *,
    place: str,
    lang: str,
    include_current: bool,
    include_warnings: bool,
) -> WeatherPollResult:
    current: CurrentWeather | None = None
    warnings: list[WeatherWarning] = []
    tips: list[SpecialWeatherTip] = []

    if include_current:
        current = fetch_current_weather(place=place, lang=lang)
    if include_warnings:
        warnings, tips = fetch_warnings_and_tips(lang=lang)

    return WeatherPollResult(current=current, warnings=warnings, tips=tips)


def is_transient_fetch_error(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.URLError):
        return True
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, ValueError):
        return True
    return False


def log_fetch_error(context: str, exc: BaseException) -> None:
    _logger.warning("HKO weather fetch failed (%s): %s", context, exc)
