"""Live desktop context injected into the chat system prompt."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from outlook_models import CalendarEvent
from weather_client import CurrentWeather, SpecialWeatherTip, WeatherWarning


@dataclass(frozen=True)
class BatteryStatus:
    """Current power/battery snapshot for chat context."""

    on_ac: bool | None
    percent: int | None
    charging: bool | None = None

ContextProvider = Callable[[], str | None]


def _short_place(place: str) -> str:
    if place == "Hong Kong Observatory":
        return "HKO"
    return place

_MAX_CONTEXT_CHARS = 900
_MAX_MEETINGS = 2
_MAX_WARNINGS = 4
_MAX_TIPS = 1
_MEETING_LOOKAHEAD = timedelta(hours=24)

_providers: list[ContextProvider] = []


def register_chat_context_provider(provider: ContextProvider) -> None:
    """Register a callable that returns a context section, or None when empty."""
    if provider not in _providers:
        _providers.append(provider)


def clear_chat_context_providers() -> None:
    """Remove all registered providers (mainly for tests)."""
    _providers.clear()


def build_live_chat_context() -> str:
    """Combine registered provider sections into one prompt block."""
    sections: list[str] = []
    for provider in list(_providers):
        try:
            section = provider()
        except Exception:
            continue
        if isinstance(section, str) and section.strip():
            sections.append(section.strip())
    if not sections:
        return ""
    body = "\n".join(sections)
    if len(body) > _MAX_CONTEXT_CHARS:
        body = body[: _MAX_CONTEXT_CHARS - 1].rstrip() + "…"
    return (
        "Live desktop context (use when relevant; do not invent facts beyond this):\n"
        f"{body}"
    )


def format_weather_chat_context(
    *,
    enabled: bool,
    current: CurrentWeather | None,
    warnings: list[WeatherWarning],
    tips: list[SpecialWeatherTip],
) -> str | None:
    """Format a short HKO weather snapshot for the system prompt."""
    if not enabled:
        return None

    lines: list[str] = ["Weather (Hong Kong Observatory):"]
    if current is not None:
        parts: list[str] = []
        if current.temperature_c is not None:
            parts.append(f"{current.temperature_c}°C")
        if current.humidity_pct is not None:
            parts.append(f"{current.humidity_pct}% humidity")
        place = _short_place(current.place)
        header = " · ".join(parts) if parts else "conditions"
        lines.append(f"- Now at {place}: {header}")
        forecast = " ".join(current.forecast_desc.split())
        if forecast:
            if len(forecast) > 120:
                forecast = forecast[:119].rstrip() + "…"
            lines.append(f"- Forecast: {forecast}")
    else:
        lines.append("- Current conditions not fetched yet")

    active = [
        warning
        for warning in warnings
        if warning.action_code.upper() != "CANCEL"
    ][:_MAX_WARNINGS]
    if active:
        names = ", ".join(warning.name for warning in active)
        lines.append(f"- Active warnings: {names}")
    else:
        lines.append("- Active warnings: none")

    for tip in tips[:_MAX_TIPS]:
        desc = " ".join(tip.desc.split())
        if len(desc) > 100:
            desc = desc[:99].rstrip() + "…"
        lines.append(f"- Special tip: {desc}")

    return "\n".join(lines)


def _format_meeting_when(event: CalendarEvent, *, now: datetime) -> str:
    if event.is_all_day:
        return f"all day {event.start.strftime('%Y-%m-%d')}"
    minutes = int((event.start - now).total_seconds() // 60)
    clock = event.start.strftime("%H:%M")
    if minutes <= 0:
        return f"now ({clock})"
    if minutes < 60:
        return f"in {minutes} min ({clock})"
    hours = minutes // 60
    rem = minutes % 60
    if hours < 24:
        if rem:
            return f"in {hours}h {rem}m ({clock})"
        return f"in {hours}h ({clock})"
    return event.start.strftime("%Y-%m-%d %H:%M")


def format_outlook_chat_context(
    *,
    enabled: bool,
    connected: bool,
    unread_count: int | None,
    upcoming_events: list[CalendarEvent],
    now: datetime | None = None,
) -> str | None:
    """Format a short Outlook mail/calendar snapshot for the system prompt."""
    if not enabled:
        return None

    lines: list[str] = ["Outlook:"]
    if not connected:
        lines.append("- Not connected")
        return "\n".join(lines)

    if unread_count is not None:
        lines.append(f"- Unread mail: {unread_count}")

    current = now or datetime.now()
    horizon = current + _MEETING_LOOKAHEAD
    upcoming = [
        event
        for event in upcoming_events
        if event.end >= current and event.start <= horizon
    ]
    upcoming.sort(key=lambda event: event.start)
    upcoming = upcoming[:_MAX_MEETINGS]

    if upcoming:
        for event in upcoming:
            title = event.subject.strip() or "(no subject)"
            if len(title) > 60:
                title = title[:59].rstrip() + "…"
            when = _format_meeting_when(event, now=current)
            lines.append(f"- Next meeting: {title} — {when}")
    else:
        lines.append("- Next meeting: none in the next 24 hours")

    return "\n".join(lines)


def _format_timezone_label(current: datetime) -> str:
    tzinfo = current.tzinfo
    name = current.tzname() or "local"
    if tzinfo is None:
        return name
    offset = tzinfo.utcoffset(current)
    if offset is None:
        return name
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    offset_label = (
        f"UTC{sign}{hours}"
        if minutes == 0
        else f"UTC{sign}{hours}:{minutes:02d}"
    )
    if name and name not in {"UTC", offset_label}:
        return f"{name} ({offset_label})"
    return offset_label


def format_desktop_chat_context(
    *,
    now: datetime | None = None,
    battery: BatteryStatus | None = None,
    motion_paused: bool = False,
    click_through: bool = False,
    active_window_title: str | None = None,
    clipboard_text: str | None = None,
) -> str | None:
    """Format local desktop state for the chat system prompt."""
    current = now or datetime.now().astimezone()
    tz_label = _format_timezone_label(current)

    lines: list[str] = [
        "Desktop:",
        (
            f"- Local time: {current.strftime('%a %Y-%m-%d %H:%M')} "
            f"({tz_label})"
        ),
    ]

    if battery is not None:
        parts: list[str] = []
        if battery.on_ac is True:
            parts.append("plugged in")
        elif battery.on_ac is False:
            parts.append("on battery")
        if battery.percent is not None:
            parts.append(f"{battery.percent}%")
        if battery.charging is True:
            parts.append("charging")
        elif battery.charging is False and battery.on_ac is False:
            parts.append("discharging")
        if parts:
            lines.append(f"- Power: {', '.join(parts)}")

    app_bits: list[str] = []
    if motion_paused:
        app_bits.append("pets paused")
    else:
        app_bits.append("pets active")
    if click_through:
        app_bits.append("click-through on")
    else:
        app_bits.append("click-through off")
    lines.append(f"- App: {'; '.join(app_bits)}")

    if active_window_title:
        lines.append(f"- Active window: {active_window_title}")

    if clipboard_text:
        preview = clipboard_text.replace('"', "'")
        lines.append(f'- Clipboard: "{preview}"')

    return "\n".join(lines)
