"""MSAL token acquisition and cache for Microsoft Graph."""

from __future__ import annotations

import logging
from typing import Any

from config import (
    get_azure_client_id,
    get_azure_tenant_id,
    get_outlook_graph_token_cache,
    set_outlook_graph_token_cache,
)

GRAPH_SCOPES: list[str] = ["User.Read", "Mail.Read", "Calendars.Read"]
GRAPH_AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant}"

_logger = logging.getLogger(__name__)


def outlook_graph_configured() -> bool:
    """Return True when an Azure app client ID is configured."""
    return bool(get_azure_client_id())


def _build_msal_app() -> tuple[Any, Any]:
    import msal

    client_id = get_azure_client_id()
    if not client_id:
        raise RuntimeError("AZURE_CLIENT_ID is not configured")

    cache = msal.SerializableTokenCache()
    cached = get_outlook_graph_token_cache()
    if cached:
        cache.deserialize(cached)

    authority = GRAPH_AUTHORITY_TEMPLATE.format(tenant=get_azure_tenant_id())
    app = msal.PublicClientApplication(
        client_id,
        authority=authority,
        token_cache=cache,
    )
    return app, cache


def _persist_cache(cache: Any) -> None:
    if cache.has_state_changed:
        set_outlook_graph_token_cache(cache.serialize())


def acquire_graph_token(*, interactive: bool = False) -> dict[str, Any] | None:
    """Return a token response dict, or None when authentication fails."""
    if not outlook_graph_configured():
        return None

    try:
        app, cache = _build_msal_app()
    except Exception:
        _logger.exception("Failed to initialize MSAL")
        return None

    result: dict[str, Any] | None = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0])

    if not result and interactive:
        try:
            result = app.acquire_token_interactive(scopes=GRAPH_SCOPES)
        except Exception:
            _logger.exception("Interactive Graph sign-in failed")
            result = None

    _persist_cache(cache)
    if not result or "access_token" not in result:
        return None
    return result


def clear_graph_token_cache() -> None:
    """Remove saved Graph sign-in tokens."""
    set_outlook_graph_token_cache("")
