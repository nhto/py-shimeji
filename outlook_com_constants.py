"""Outlook COM folder and property constants (classic Outlook / MAPI)."""

from __future__ import annotations

# Default folder types (OlDefaultFolders)
OL_FOLDER_INBOX = 6
OL_FOLDER_CALENDAR = 9
OL_FOLDER_SENT = 5
OL_FOLDER_DRAFTS = 16
OL_FOLDER_DELETED = 3

# Item classes (OlObjectClass)
OL_MAIL_ITEM = 43
OL_APPOINTMENT_ITEM = 26

# MAPI property tags
PR_SMTP_ADDRESS = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
PR_SENDER_SMTP_ADDRESS = "http://schemas.microsoft.com/mapi/proptag/0x5D01001F"

# HRESULT: object is not running (GetActiveObject when Outlook is closed)
MK_E_UNAVAILABLE = -2147221021
