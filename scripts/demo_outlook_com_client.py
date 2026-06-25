"""Exercise outlook_com_client.py against the local Outlook profile.

Run from the project root:

    .venv\\Scripts\\python scripts\\demo_outlook_com_client.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from outlook_com_client import OutlookComClient


def main() -> int:
    client = OutlookComClient()
    try:
        if not client.is_available():
            print("Outlook COM is not available.")
            print("Install classic Outlook, sign in, and retry.")
            return 1

        email = client.get_current_user_email()
        print(f"Connected as: {email or '(unknown)'}")

        print()
        print("Unread messages:")
        unread = client.list_unread_messages(max_count=10)
        if not unread:
            print("  (none)")
        for message in unread:
            print(f"  - {message.sender_name} <{message.sender_email}>: {message.subject}")

        print()
        print("Meetings in the next 24 hours:")
        events = client.list_upcoming_events(within_hours=24)
        if not events:
            print("  (none)")
        for event in events:
            start = event.start.strftime("%Y-%m-%d %H:%M")
            location = f" @ {event.location}" if event.location else ""
            print(f"  - {start}: {event.subject}{location}")

        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
