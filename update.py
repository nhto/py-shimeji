"""GitHub Releases version check and in-place auto-update for frozen builds."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from version import GITHUB_REPO, __version__

_USER_FILES = frozenset({".env", ".app_settings.json", ".chat_settings.json"})
_GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_USER_AGENT = f"py-shimeji/{__version__}"
_VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+)*)")


@dataclass(frozen=True)
class UpdateInfo:
    """A newer release available on GitHub."""

    version: str
    tag: str
    download_url: str
    release_page_url: str
    notes: str


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def app_install_dir() -> Path:
    return Path(sys.executable).resolve().parent


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a semver prefix like ``v1.2.3`` into a comparable tuple."""
    match = _VERSION_RE.match(version.strip())
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(current: str, latest: str) -> bool:
    return parse_version(latest) > parse_version(current)


def _github_request(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Unexpected GitHub API response")
    return payload


def _pick_portable_zip_asset(assets: object) -> dict | None:
    if not isinstance(assets, list):
        return None
    candidates: list[dict] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name", ""))
        if not name.endswith(".zip"):
            continue
        if "setup" in name.lower():
            continue
        if name.startswith("py-shimeji"):
            candidates.append(asset)
    if not candidates:
        return None
    return candidates[0]


@dataclass(frozen=True)
class UpdateCheckResult:
    """Outcome of a GitHub Releases version check."""

    status: Literal["update", "current", "error"]
    update: UpdateInfo | None = None


def check_for_updates_result() -> UpdateCheckResult:
    """Check GitHub Releases and classify the outcome."""
    try:
        release = _github_request(_GITHUB_API)
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
        return UpdateCheckResult(status="error")

    tag = str(release.get("tag_name", "")).strip()
    if not tag:
        return UpdateCheckResult(status="error")

    version = tag.lstrip("v")
    if not is_newer_version(__version__, version):
        return UpdateCheckResult(status="current")

    asset = _pick_portable_zip_asset(release.get("assets"))
    if asset is None:
        return UpdateCheckResult(status="error")

    download_url = str(asset.get("browser_download_url", "")).strip()
    if not download_url:
        return UpdateCheckResult(status="error")

    notes = str(release.get("body", "")).strip()
    page_url = str(release.get("html_url", "")).strip()
    return UpdateCheckResult(
        status="update",
        update=UpdateInfo(
            version=version,
            tag=tag,
            download_url=download_url,
            release_page_url=page_url,
            notes=notes,
        ),
    )


def check_for_updates() -> UpdateInfo | None:
    """Return update info when a newer GitHub Release exists, else None."""
    result = check_for_updates_result()
    return result.update if result.status == "update" else None


def download_release_zip(update: UpdateInfo, destination: Path) -> Path:
    """Download the portable release zip to *destination*."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        update.download_url,
        headers={"User-Agent": _USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())
    return destination


def extract_release_zip(zip_path: Path, destination: Path) -> Path:
    """Extract the release zip and return the folder that contains the app exe."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)

    # Zip layout is either py-shimeji/... or a versioned top folder.
    for candidate in destination.iterdir():
        if candidate.is_dir() and (candidate / "py-shimeji.exe").is_file():
            return candidate
    if (destination / "py-shimeji.exe").is_file():
        return destination
    raise FileNotFoundError("Release zip does not contain py-shimeji.exe")


def updater_executable() -> Path | None:
    """Return the bundled updater exe when present next to the main app."""
    if not is_frozen():
        return None
    path = app_install_dir() / "py-shimeji-updater.exe"
    return path if path.is_file() else None


def apply_update_and_restart(update: UpdateInfo) -> bool:
    """
    Download the release, hand off to the updater, and return True when the
    main app should quit so files can be replaced.
    """
    if not is_frozen() or sys.platform != "win32":
        return False

    updater = updater_executable()
    if updater is None:
        return False

    work_dir = Path(tempfile.mkdtemp(prefix="py-shimeji-update-"))
    zip_path = work_dir / "update.zip"
    extracted_root = work_dir / "extracted"

    download_release_zip(update, zip_path)
    source_dir = extract_release_zip(zip_path, extracted_root)
    target_dir = app_install_dir()

    subprocess.Popen(
        [
            str(updater),
            "--source",
            str(source_dir),
            "--target",
            str(target_dir),
            "--restart",
            "py-shimeji.exe",
        ],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
    return True


def copy_release_tree(source: Path, target: Path, *, preserve_user_files: bool = True) -> None:
    """Copy a release folder over an install directory (updater helper)."""
    preserved: dict[str, bytes] = {}
    if preserve_user_files:
        for name in _USER_FILES:
            path = target / name
            if path.is_file():
                preserved[name] = path.read_bytes()

    for item in source.iterdir():
        dest = target / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    for name, data in preserved.items():
        (target / name).write_bytes(data)
