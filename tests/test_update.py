"""Tests for GitHub release version parsing and asset selection."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from update import (
    UpdateCheckResult,
    _pick_portable_zip_asset,
    check_for_updates_result,
    is_newer_version,
    parse_version,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.2.3", (1, 2, 3)),
        ("v0.10.0", (0, 10, 0)),
        ("2", (2,)),
    ],
)
def test_parse_version(value: str, expected: tuple[int, ...]) -> None:
    assert parse_version(value) == expected


@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("0.1.0", "0.2.0", True),
        ("0.1.0", "0.1.0", False),
        ("1.0.0", "0.9.9", False),
        ("0.9.0", "0.10.0", True),
    ],
)
def test_is_newer_version(current: str, latest: str, expected: bool) -> None:
    assert is_newer_version(current, latest) is expected


def test_pick_portable_zip_asset_prefers_app_zip() -> None:
    assets = [
        {"name": "py-shimeji-setup-1.0.0.exe", "browser_download_url": "https://example/setup"},
        {"name": "py-shimeji-1.0.0.zip", "browser_download_url": "https://example/zip"},
    ]
    picked = _pick_portable_zip_asset(assets)
    assert picked is not None
    assert picked["name"] == "py-shimeji-1.0.0.zip"


def test_check_for_updates_result_current(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "tag_name": "v0.1.0",
        "html_url": "https://github.com/nhto/py-shimeji/releases/tag/v0.1.0",
        "body": "Current",
        "assets": [{"name": "py-shimeji-0.1.0.zip", "browser_download_url": "https://example/zip"}],
    }

    def fake_request(url: str) -> dict:
        return payload

    monkeypatch.setattr("update._github_request", fake_request)
    result = check_for_updates_result()
    assert result.status == "current"
    assert result.update is None


def test_check_for_updates_result_update(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "tag_name": "v9.9.9",
        "html_url": "https://github.com/nhto/py-shimeji/releases/tag/v9.9.9",
        "body": "New release",
        "assets": [{"name": "py-shimeji-9.9.9.zip", "browser_download_url": "https://example/zip"}],
    }

    monkeypatch.setattr("update._github_request", lambda url: payload)
    result = check_for_updates_result()
    assert result.status == "update"
    assert result.update is not None
    assert result.update.version == "9.9.9"


def test_check_for_updates_result_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(url: str) -> dict:
        raise OSError("offline")

    monkeypatch.setattr("update._github_request", raise_error)
    result = check_for_updates_result()
    assert result.status == "error"
