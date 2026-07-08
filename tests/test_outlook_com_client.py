"""Unit tests for classic Outlook COM attachment behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from outlook_com_constants import MK_E_UNAVAILABLE


def test_attach_outlook_application_uses_running_instance() -> None:
    import outlook_com_client as module

    mock_outlook = MagicMock()
    with patch("win32com.client.GetActiveObject", return_value=mock_outlook) as get_active:
        result = module._attach_outlook_application()

    assert result is mock_outlook
    get_active.assert_called_once_with("Outlook.Application")


def test_attach_outlook_application_does_not_launch_when_not_running() -> None:
    import outlook_com_client as module
    import pywintypes

    com_error = pywintypes.com_error(MK_E_UNAVAILABLE, "Not available", None, -1)

    with (
        patch("win32com.client.GetActiveObject", side_effect=com_error),
        patch("subprocess.Popen") as popen,
        patch("win32com.client.Dispatch") as dispatch,
        pytest.raises(RuntimeError, match="Outlook is not running"),
    ):
        module._attach_outlook_application()

    popen.assert_not_called()
    dispatch.assert_not_called()
