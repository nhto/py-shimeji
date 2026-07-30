"""Hong Kong Observatory weather notification settings."""

from __future__ import annotations

from settings.core import MAX_PETS
from settings.persistence import clamp_int, load_app_settings, save_app_settings

WEATHER_WARNING_POLL_INTERVAL_SEC_DEFAULT: int = 600
WEATHER_WARNING_POLL_INTERVAL_SEC_MIN: int = 60
WEATHER_WARNING_POLL_INTERVAL_SEC_MAX: int = 3600
WEATHER_NOTIFY_PET_FIRST_VISIBLE: int = -1
WEATHER_DEFAULT_LOCATION: str = "Hong Kong Observatory"

HKO_WEATHER_PLACES: tuple[str, ...] = (
    "Hong Kong Observatory",
    "King's Park",
    "Wong Chuk Hang",
    "Ta Kwu Ling",
    "Lau Fau Shan",
    "Tai Po",
    "Sha Tin",
    "Tuen Mun",
    "Tseung Kwan O",
    "Sai Kung",
    "Cheung Chau",
    "Chek Lap Kok",
    "Tsing Yi",
    "Shek Kong",
    "Tsuen Wan Ho Koon",
    "Tsuen Wan Shing Mun Valley",
    "Hong Kong Park",
    "Shau Kei Wan",
    "Kowloon City",
    "Happy Valley",
    "Wong Tai Sin",
    "Stanley",
    "Kwun Tong",
    "Sham Shui Po",
    "Kai Tak Runway Park",
    "Yuen Long Park",
    "Tai Mei Tuk",
)


def _weather_settings_raw() -> dict:
    weather = load_app_settings().get("weather", {})
    return weather if isinstance(weather, dict) else {}


def _normalize_notify_pet_index(value: object) -> int:
    if value == WEATHER_NOTIFY_PET_FIRST_VISIBLE:
        return WEATHER_NOTIFY_PET_FIRST_VISIBLE
    try:
        index = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return WEATHER_NOTIFY_PET_FIRST_VISIBLE
    if index < 0:
        return WEATHER_NOTIFY_PET_FIRST_VISIBLE
    return min(index, MAX_PETS - 1)


def _normalize_location(value: object) -> str:
    if isinstance(value, str) and value.strip():
        place = value.strip()
        if place in HKO_WEATHER_PLACES:
            return place
    return WEATHER_DEFAULT_LOCATION


def _normalize_known_warnings(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        if isinstance(key, str) and key.strip() and isinstance(item, str) and item.strip():
            result[key.strip()] = item.strip()
    return result


def _normalize_known_swt(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def get_weather_settings() -> dict:
    raw = _weather_settings_raw()
    return {
        "enabled": bool(raw.get("enabled", True)),
        "location": _normalize_location(raw.get("location")),
        "warning_poll_interval_sec": clamp_int(
            raw.get("warning_poll_interval_sec"),
            WEATHER_WARNING_POLL_INTERVAL_SEC_MIN,
            WEATHER_WARNING_POLL_INTERVAL_SEC_MAX,
            WEATHER_WARNING_POLL_INTERVAL_SEC_DEFAULT,
        ),
        "notify_pet_index": _normalize_notify_pet_index(raw.get("notify_pet_index")),
        "notify_when_paused": bool(raw.get("notify_when_paused", True)),
        "last_hourly_key": raw.get("last_hourly_key")
        if isinstance(raw.get("last_hourly_key"), str)
        else "",
        "known_warnings": _normalize_known_warnings(raw.get("known_warnings")),
        "known_swt": _normalize_known_swt(raw.get("known_swt")),
    }


def get_weather_enabled() -> bool:
    return bool(get_weather_settings()["enabled"])


def get_weather_location() -> str:
    return str(get_weather_settings()["location"])


def get_weather_warning_poll_interval_sec() -> int:
    return int(get_weather_settings()["warning_poll_interval_sec"])


def get_weather_notify_pet_index() -> int:
    return int(get_weather_settings()["notify_pet_index"])


def get_weather_notify_when_paused() -> bool:
    return bool(get_weather_settings()["notify_when_paused"])


def get_weather_last_hourly_key() -> str:
    return str(get_weather_settings()["last_hourly_key"])


def get_weather_known_warnings() -> dict[str, str]:
    return dict(get_weather_settings()["known_warnings"])


def get_weather_known_swt() -> list[str]:
    return list(get_weather_settings()["known_swt"])


def _save_weather_partial(updates: dict) -> None:
    data = load_app_settings()
    weather = data.setdefault("weather", {})
    if not isinstance(weather, dict):
        weather = {}
        data["weather"] = weather
    weather.update(updates)
    save_app_settings(data)


def set_weather_enabled(enabled: bool) -> None:
    _save_weather_partial({"enabled": bool(enabled)})


def set_weather_settings(
    *,
    enabled: bool | None = None,
    location: str | None = None,
    warning_poll_interval_sec: int | None = None,
    notify_pet_index: int | None = None,
    notify_when_paused: bool | None = None,
) -> None:
    updates: dict[str, object] = {}
    if enabled is not None:
        updates["enabled"] = bool(enabled)
    if location is not None:
        updates["location"] = _normalize_location(location)
    if warning_poll_interval_sec is not None:
        updates["warning_poll_interval_sec"] = clamp_int(
            warning_poll_interval_sec,
            WEATHER_WARNING_POLL_INTERVAL_SEC_MIN,
            WEATHER_WARNING_POLL_INTERVAL_SEC_MAX,
            WEATHER_WARNING_POLL_INTERVAL_SEC_DEFAULT,
        )
    if notify_pet_index is not None:
        updates["notify_pet_index"] = _normalize_notify_pet_index(notify_pet_index)
    if notify_when_paused is not None:
        updates["notify_when_paused"] = bool(notify_when_paused)
    if updates:
        _save_weather_partial(updates)


def set_weather_last_hourly_key(key: str) -> None:
    _save_weather_partial({"last_hourly_key": key.strip()})


def set_weather_known_warnings(known_warnings: dict[str, str]) -> None:
    _save_weather_partial({"known_warnings": _normalize_known_warnings(known_warnings)})


def set_weather_known_swt(known_swt: list[str]) -> None:
    _save_weather_partial({"known_swt": _normalize_known_swt(known_swt)})
