"""Open HKO warning pages from speech-bubble actions."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from weather_client import WeatherWarning, hko_lang_from_ui_language

_logger = logging.getLogger(__name__)

HKO_SITE_BASE = "https://www.hko.gov.hk"

# Live status board — fallback for unknown codes and special tips.
HKO_WARNINGS_TODAY_PATH = "/wxinfo/dailywx/wxwarntoday.htm"

# Category / subtype code → path under the language root (/en, /tc, /sc).
_HKO_WARNING_PATHS: dict[str, str] = {
    "WTS": "/wservice/warning/thunder.htm",
    "WRAIN": "/wservice/warning/rainstor.htm",
    "WRAINA": "/wservice/warning/rainstor.htm#amber",
    "WRAINR": "/wservice/warning/rainstor.htm#red",
    "WRAINB": "/wservice/warning/rainstor.htm#black",
    "WFNTSA": "/wservice/warning/flood.htm",
    "WL": "/wservice/warning/landslip.htm",
    "WMSGNL": "/wservice/warning/smse.htm",
    "WFROST": "/wservice/tsheet/pubwx.htm#frost",
    "WFIRE": "/publica/gen_pub/fdw.htm",
    "WFIREY": "/publica/gen_pub/fdw.htm",
    "WFIRER": "/publica/gen_pub/fdw.htm",
    "WCOLD": "/wservice/warning/coldhot.htm",
    "WHOT": "/wservice/warning/coldhot.htm",
    "WTMW": "/gts/equake/tsunami_mon.htm",
    "WTCSGNL": "/wservice/tsheet/tcwarn.htm",
    "WTCPRE8": "/wservice/tsheet/tcwarn.htm",
}


def open_url(url: str) -> None:
    """Open an http(s) URL in the default browser."""
    stripped = url.strip()
    if not stripped:
        return
    if not QDesktopServices.openUrl(QUrl(stripped)):
        _logger.warning("Could not open URL: %s", stripped)


def hko_site_lang(language: str) -> str:
    """Map app UI language to HKO website language path segment."""
    return hko_lang_from_ui_language(language)


def hko_warnings_today_url(*, language: str = "en") -> str:
    """URL for the live Hong Kong weather warnings board."""
    return f"{HKO_SITE_BASE}/{hko_site_lang(language)}{HKO_WARNINGS_TODAY_PATH}"


def hko_warning_url(warning: WeatherWarning, *, language: str = "en") -> str:
    """Build the most relevant HKO page URL for a warning."""
    site_lang = hko_site_lang(language)
    for key in (warning.subtype, warning.code):
        normalized = key.strip().upper()
        if not normalized:
            continue
        path = _HKO_WARNING_PATHS.get(normalized)
        if path is not None:
            return f"{HKO_SITE_BASE}/{site_lang}{path}"
    return hko_warnings_today_url(language=language)


def open_hko_warning(warning: WeatherWarning, *, language: str = "en") -> None:
    """Open the HKO page for a weather warning."""
    open_url(hko_warning_url(warning, language=language))


def open_hko_warnings_today(*, language: str = "en") -> None:
    """Open the HKO live warnings board (e.g. for special tips)."""
    open_url(hko_warnings_today_url(language=language))
