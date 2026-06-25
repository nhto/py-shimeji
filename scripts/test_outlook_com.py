"""Phase 0 sanity check: classic Outlook desktop COM on Windows.

Run from the project root:

    .venv\\Scripts\\python scripts\\test_outlook_com.py
    .venv\\Scripts\\python scripts\\test_outlook_com.py --stores

Requires classic Outlook (not "New Outlook" only) signed in to your account.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OL_FOLDER_INBOX = 6
PR_SMTP_ADDRESS = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify classic Outlook COM access.")
    parser.add_argument(
        "--stores",
        action="store_true",
        help="List every mailbox store in the Outlook profile.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if sys.platform != "win32":
        print("FAIL: Outlook COM is Windows-only.")
        return 1

    try:
        import pythoncom
        import pywintypes
        import win32com.client
    except ImportError:
        print("FAIL: pywin32 is not installed. Run: pip install pywin32")
        return 1

    pythoncom.CoInitialize()
    try:
        try:
            outlook = win32com.client.GetActiveObject("Outlook.Application")
        except pywintypes.com_error as exc:
            if exc.hresult != -2147221021:  # MK_E_UNAVAILABLE — Outlook not running
                raise
            outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        user = namespace.CurrentUser

        name = getattr(user, "Name", None) or "(unknown)"
        address = getattr(user, "Address", None) or "(unknown)"
        try:
            smtp = user.PropertyAccessor.GetProperty(PR_SMTP_ADDRESS)
        except Exception:
            smtp = None

        inbox = namespace.GetDefaultFolder(OL_FOLDER_INBOX)
        unread_count = inbox.Items.Restrict("[UnRead] = True").Count
    except Exception as exc:
        print(f"FAIL: Could not connect to Outlook via COM ({type(exc).__name__}: {exc})")
        print()
        print("Checklist:")
        print("  - Classic Outlook desktop is installed (not Outlook Web only)")
        print("  - Outlook is running and you are signed in")
        print("  - Turn off 'New Outlook' in Outlook settings if COM fails")
        print("  - Allow the one-time programmatic access prompt if Windows shows it")
        print("  - IT has not blocked programmatic access to Outlook")
        return 1
    finally:
        pythoncom.CoUninitialize()

    print("OK: Outlook COM is available.")
    print(f"User: {name}")
    print(f"Address: {address}")
    if smtp:
        print(f"SMTP: {smtp}")
    print(f"Unread inbox (default): {unread_count}")

    if args.stores:
        try:
            from outlook_com_client import OutlookComClient

            client = OutlookComClient()
            try:
                stores = client.list_mail_stores()
            finally:
                client.close()
        except Exception as exc:
            print(f"WARN: Could not list mailbox stores ({type(exc).__name__}: {exc})")
            return 0

        if not stores:
            print("Mailbox stores: (none)")
        else:
            print("Mailbox stores:")
            for store in stores:
                print(f"  - {store.display_name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
