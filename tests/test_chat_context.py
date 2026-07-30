"""Unit tests for live chat context formatting."""

from __future__ import annotations

from datetime import datetime, timedelta

from chat_context import (
    build_live_chat_context,
    clear_chat_context_providers,
    format_outlook_chat_context,
    format_weather_chat_context,
    register_chat_context_provider,
)
from config import build_chat_system_prompt
from outlook_models import CalendarEvent
from weather_client import CurrentWeather, SpecialWeatherTip, WeatherWarning


def setup_function() -> None:
    clear_chat_context_providers()


def teardown_function() -> None:
    clear_chat_context_providers()


def test_format_weather_chat_context_includes_temp_and_warnings() -> None:
    text = format_weather_chat_context(
        enabled=True,
        current=CurrentWeather(
            place="Hong Kong Observatory",
            temperature_c=28,
            humidity_pct=80,
            forecast_desc="Showers.",
            update_time="2026-07-30T15:00:00+08:00",
        ),
        warnings=[
            WeatherWarning(
                code="WTS",
                name="Thunderstorm Warning",
                action_code="ISSUE",
                issue_time="",
                update_time="",
            ),
            WeatherWarning(
                code="WRAIN",
                name="Rainstorm Warning Signal",
                action_code="CANCEL",
                issue_time="",
                update_time="",
            ),
        ],
        tips=[
            SpecialWeatherTip(desc="Heavy rain expected later.", update_time=""),
        ],
    )
    assert text is not None
    assert "28°C" in text
    assert "Thunderstorm Warning" in text
    assert "Rainstorm" not in text
    assert "Heavy rain" in text


def test_format_weather_disabled_returns_none() -> None:
    assert (
        format_weather_chat_context(
            enabled=False,
            current=None,
            warnings=[],
            tips=[],
        )
        is None
    )


def test_format_outlook_chat_context_unread_and_next_meeting() -> None:
    now = datetime(2026, 7, 30, 15, 0, 0)
    text = format_outlook_chat_context(
        enabled=True,
        connected=True,
        unread_count=3,
        upcoming_events=[
            CalendarEvent(
                entry_id="1",
                subject="Standup",
                start=now + timedelta(minutes=20),
                end=now + timedelta(minutes=50),
            )
        ],
        now=now,
    )
    assert text is not None
    assert "Unread mail: 3" in text
    assert "Standup" in text
    assert "in 20 min" in text


def test_format_outlook_not_connected() -> None:
    text = format_outlook_chat_context(
        enabled=True,
        connected=False,
        unread_count=None,
        upcoming_events=[],
    )
    assert text is not None
    assert "Not connected" in text


def test_build_live_chat_context_combines_providers() -> None:
    register_chat_context_provider(lambda: "Weather:\n- Now: 30°C")
    register_chat_context_provider(lambda: "Outlook:\n- Unread mail: 1")
    block = build_live_chat_context()
    assert "Live desktop context" in block
    assert "30°C" in block
    assert "Unread mail: 1" in block


def test_build_chat_system_prompt_appends_live_context() -> None:
    register_chat_context_provider(lambda: "Weather:\n- Now at HKO: 29°C")
    prompt = build_chat_system_prompt("en")
    assert "Live desktop context" in prompt
    assert "29°C" in prompt
