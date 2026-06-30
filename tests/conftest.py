"""Shared pytest fixtures."""

from __future__ import annotations

import sys

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Single QApplication instance for Qt-dependent unit tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app
