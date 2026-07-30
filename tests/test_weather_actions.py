"""Unit tests for HKO speech-bubble action URLs."""

from __future__ import annotations

from weather_actions import (
    hko_site_lang,
    hko_warning_url,
    hko_warnings_today_url,
)
from weather_client import WeatherWarning


def _warning(**overrides: str) -> WeatherWarning:
    base = {
        "code": "WTS",
        "name": "Thunderstorm Warning",
        "action_code": "ISSUE",
        "issue_time": "2026-07-30T08:00:00+08:00",
        "update_time": "2026-07-30T08:00:00+08:00",
        "subtype": "",
    }
    base.update(overrides)
    return WeatherWarning(**base)


def test_hko_site_lang_follows_ui_language() -> None:
    assert hko_site_lang("en") == "en"
    assert hko_site_lang("zh-Hans") == "sc"
    assert hko_site_lang("zh-Hant") == "tc"


def test_hko_warning_url_uses_subtype_when_present() -> None:
    warning = _warning(code="WRAIN", subtype="WRAINR", name="Rainstorm Warning Signal")
    url = hko_warning_url(warning, language="en")
    assert url.endswith("/en/wservice/warning/rainstor.htm#red")


def test_hko_warning_url_falls_back_to_category() -> None:
    warning = _warning()
    url = hko_warning_url(warning, language="zh-Hant")
    assert url.endswith("/tc/wservice/warning/thunder.htm")


def test_hko_warning_url_unknown_uses_warnings_today() -> None:
    warning = _warning(code="UNKNOWN", subtype="")
    assert hko_warning_url(warning, language="en") == hko_warnings_today_url(
        language="en"
    )


def test_hko_warnings_today_url() -> None:
    assert hko_warnings_today_url(language="zh-Hans").endswith(
        "/sc/wxinfo/dailywx/wxwarntoday.htm"
    )
