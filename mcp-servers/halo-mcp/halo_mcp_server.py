#!/usr/bin/env python3
"""Halo (HaloPSA / HaloITSM / HaloCRM) API MCP Server (Feature 069).

A focused FastMCP/stdio server for two jobs:
  1. Open **change requests** in Halo (the one gated write; confirm-before-submit).
  2. Review **assets and their related tickets** for operational context.

Halo is heavily per-org customized: a "change request" is just a ticket type
whose id and custom fields differ per instance. Discovery/confirmation of the
change ticket type and its field schema is orchestrated by the halo-* skills
(which cache the confirmed type in Memory MCP); this server exposes the
primitives (list ticket types, read a type's field schema, read a sample
ticket, create a change request).

18 tools — 17 read-only + 1 gated write:
  ticket types (2)  fields (2)  tickets (4 read + 1 write)  assets (3)
  context (4)       knowledge (2)

Auth: OAuth2 client-credentials (cloud). Transport: stdio (stdout is reserved
for MCP JSON-RPC; all logging goes to stderr).
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Bootstrap: env + logging BEFORE internal imports that read config
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("halo-mcp")

# ---------------------------------------------------------------------------
# Configuration (read at module load)
# ---------------------------------------------------------------------------

from utils.constants import (  # noqa: E402
    DEFAULT_MAX_PAGES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SCOPE,
    DEFAULT_TIMEOUT,
)

HALO_BASE_URL: str = os.getenv("HALO_BASE_URL", "").rstrip("/")
HALO_TENANT: str = os.getenv("HALO_TENANT", "")
HALO_CLIENT_ID: str = os.getenv("HALO_CLIENT_ID", "")
HALO_CLIENT_SECRET: str = os.getenv("HALO_CLIENT_SECRET", "")
HALO_SCOPE: str = os.getenv("HALO_SCOPE", DEFAULT_SCOPE)
HALO_AUTH_URL: str = os.getenv("HALO_AUTH_URL", "")  # override for self-hosted layouts
HALO_VERIFY_SSL: bool = os.getenv("HALO_VERIFY_SSL", "true").lower() == "true"
HALO_TIMEOUT: int = int(os.getenv("HALO_TIMEOUT", str(DEFAULT_TIMEOUT)))
HALO_PAGE_SIZE: int = int(os.getenv("HALO_PAGE_SIZE", str(DEFAULT_PAGE_SIZE)))
HALO_MAX_PAGES: int = int(os.getenv("HALO_MAX_PAGES", str(DEFAULT_MAX_PAGES)))
HALO_RATE_LIMIT: int = int(os.getenv("HALO_RATE_LIMIT", "0"))  # 0 = disabled (429 backoff only)

# ---------------------------------------------------------------------------
# Internal imports
# ---------------------------------------------------------------------------

from clients.halo_client import HaloClient  # noqa: E402
from utils.rate_limiter import SlidingWindowRateLimiter  # noqa: E402

from tools.ticket_types import (  # noqa: E402
    halo_get_ticket_type as _get_ticket_type,
    halo_list_ticket_types as _list_ticket_types,
)
from tools.fields import (  # noqa: E402
    halo_get_field as _get_field,
    halo_list_fields as _list_fields,
)
from tools.tickets import (  # noqa: E402
    halo_create_change_request as _create_change_request,
    halo_get_asset_tickets as _get_asset_tickets,
    halo_get_ticket as _get_ticket,
    halo_get_ticket_actions as _get_ticket_actions,
    halo_list_tickets as _list_tickets,
)
from tools.assets import (  # noqa: E402
    halo_get_asset as _get_asset,
    halo_get_asset_relationships as _get_asset_relationships,
    halo_list_assets as _list_assets,
)
from tools.context import (  # noqa: E402
    halo_list_clients as _list_clients,
    halo_list_contracts as _list_contracts,
    halo_list_sites as _list_sites,
    halo_list_users as _list_users,
)
from tools.knowledge import (  # noqa: E402
    halo_get_kb_article as _get_kb_article,
    halo_list_kb_articles as _list_kb_articles,
)

# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_client: Optional[HaloClient] = None


def get_client() -> HaloClient:
    """Return the shared HaloClient, creating it on first call.

    Raises:
        ValueError: If HALO_BASE_URL / HALO_CLIENT_ID / HALO_CLIENT_SECRET are unset.
    """
    global _client
    if _client is None:
        if not HALO_BASE_URL:
            raise ValueError(
                "HALO_BASE_URL is required but not set. Set it to your Halo host, "
                "e.g. https://<tenant>.halopsa.com"
            )
        if not HALO_CLIENT_ID or not HALO_CLIENT_SECRET:
            raise ValueError(
                "HALO_CLIENT_ID and HALO_CLIENT_SECRET are required but not set. "
                "Create an OAuth2 (client-credentials) API application in Halo "
                "(Configuration > Integrations > Halo API)."
            )
        rate_limiter = (
            SlidingWindowRateLimiter(HALO_RATE_LIMIT, 60.0) if HALO_RATE_LIMIT > 0 else None
        )
        _client = HaloClient(
            base_url=HALO_BASE_URL,
            client_id=HALO_CLIENT_ID,
            client_secret=HALO_CLIENT_SECRET,
            tenant=HALO_TENANT or None,
            scope=HALO_SCOPE,
            auth_url=HALO_AUTH_URL or None,
            verify_ssl=HALO_VERIFY_SSL,
            timeout=HALO_TIMEOUT,
            page_size=HALO_PAGE_SIZE,
            max_pages=HALO_MAX_PAGES,
            rate_limiter=rate_limiter,
        )
        logger.info(
            "HaloClient initialised: base_url=%s tenant=%s scope=%s verify_ssl=%s "
            "timeout=%ss page_size=%d max_pages=%d rate_limit=%s",
            HALO_BASE_URL,
            HALO_TENANT or "(none)",
            HALO_SCOPE,
            HALO_VERIFY_SSL,
            HALO_TIMEOUT,
            HALO_PAGE_SIZE,
            HALO_MAX_PAGES,
            HALO_RATE_LIMIT or "off",
        )
    return _client


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("halo-mcp")

# ── Ticket types (2) — "Request Types" in Halo ──────────────────────────────


@mcp.tool()
async def halo_list_ticket_types(
    can_create_only: Optional[bool] = None,
    customer: Optional[str] = None,
    showcounts: Optional[bool] = None,
    raw: bool = False,
) -> str:
    """List Halo ticket types ("Request Types").

    Use this to discover which ticket type an organization uses for CHANGES —
    Halo is per-org customized, so the change type's id/name vary. Set
    'can_create_only=true' to limit to types the API app may create. 'customer'
    (a client name or id) scopes to types available to that client. Returns each
    type's id, name, and (with showcounts) ticket counts.
    """
    return await _list_ticket_types(
        get_client(),
        can_create_only=can_create_only,
        customer=customer,
        showcounts=showcounts,
        raw=raw,
    )


@mcp.tool()
async def halo_get_ticket_type(ticket_type: str, raw: bool = False) -> str:
    """Get a ticket type's full field SCHEMA (authoritative field discovery).

    'ticket_type' is a type name or numeric id. Returns the type plus its field
    definitions (fields[]): each field's id/name, the underlying FieldInfo
    (type, input type, dropdown values), and required/visible flags for agent
    and end-user screens. This is the authoritative source for "what fields does
    this org's change ticket require" — pair it with a sample ticket
    (halo_get_ticket) for a concrete example.
    """
    return await _get_ticket_type(get_client(), ticket_type=ticket_type, raw=raw)


# ── Fields (2) — FieldInfo catalog ──────────────────────────────────────────


@mcp.tool()
async def halo_list_fields(custom_only: Optional[bool] = None, raw: bool = False) -> str:
    """List Halo field definitions (FieldInfo) with dropdown values.

    The master catalog of standard and custom fields. Set 'custom_only=true' for
    custom fields only. The same numeric id is used as the field's definition id,
    its value id on a ticket (customfields[].id), and its placement id on a
    ticket type — so this resolves field ids <-> names <-> option values.
    """
    return await _list_fields(get_client(), custom_only=custom_only, raw=raw)


@mcp.tool()
async def halo_get_field(field: str, raw: bool = False) -> str:
    """Get a single field definition (FieldInfo) by numeric id, with lookup values."""
    return await _get_field(get_client(), field=field, raw=raw)


# ── Tickets (4 read + 1 gated write) — "Faults" in Halo ─────────────────────


@mcp.tool()
async def halo_get_ticket(ticket: str, raw: bool = False) -> str:
    """Read a single ticket by numeric id — full detail + linked assets/customfields.

    Tickets are addressed by numeric id only (not name). Returns summary, details,
    status, priority, client/site/user, linked assets, and custom field values —
    useful as a concrete example of a populated change ticket.
    """
    return await _get_ticket(get_client(), ticket=ticket, raw=raw)


@mcp.tool()
async def halo_list_tickets(
    ticket_type: Optional[str] = None,
    customer: Optional[str] = None,
    asset_id: Optional[int] = None,
    status: Optional[str] = None,
    open_only: Optional[bool] = None,
    search: Optional[str] = None,
    raw: bool = False,
) -> str:
    """List/search tickets, filtered by ticket type, customer, asset, or status.

    'ticket_type' (name or id) and 'customer' (client name or id) are resolved to
    Halo ids. 'asset_id' returns tickets linked to that asset. 'search' does a
    free-text match; 'open_only=true' limits to open tickets. Paginated.
    """
    return await _list_tickets(
        get_client(),
        ticket_type=ticket_type,
        customer=customer,
        asset_id=asset_id,
        status=status,
        open_only=open_only,
        search=search,
        raw=raw,
    )


@mcp.tool()
async def halo_get_ticket_actions(ticket: str, raw: bool = False) -> str:
    """List a ticket's actions/notes history (by numeric ticket id)."""
    return await _get_ticket_actions(get_client(), ticket=ticket, raw=raw)


@mcp.tool()
async def halo_get_asset_tickets(
    asset: str, open_only: Optional[bool] = None, raw: bool = False
) -> str:
    """List the tickets related to an asset (resolved by name or id).

    The core "review an asset's tickets for context" tool. 'asset' is an asset
    name / inventory number / id. Set 'open_only=true' for open tickets only.
    """
    return await _get_asset_tickets(get_client(), asset=asset, open_only=open_only, raw=raw)


@mcp.tool()
async def halo_create_change_request(
    summary: str,
    details: str,
    ticket_type: str,
    customer: Optional[str] = None,
    site: Optional[str] = None,
    user: Optional[int] = None,
    asset: Optional[str] = None,
    custom_fields: Optional[dict] = None,
    submit: bool = False,
    raw: bool = False,
) -> str:
    """Open a change request in Halo. GATED: previews unless submit=true.

    THE ONLY WRITE in this server. By default (submit=false) it performs NO write:
    it resolves ids, assembles the exact POST body, and returns it as a PREVIEW so
    a human can review the proposed change. Only re-call with submit=true AFTER the
    operator explicitly approves the previewed change.

    'ticket_type' is the org's change ticket type (name or id — discover it with
    halo_list_ticket_types and confirm with the user). 'customer'/'site' are names
    or ids; 'user' is a numeric id; 'asset' is a name/inventory-number/id and links
    the asset to the change. 'custom_fields' maps field id-or-name -> value for the
    ticket type's required/optional custom fields (learn them via
    halo_get_ticket_type). Halo's own CAB/approval workflow runs after creation.
    """
    return await _create_change_request(
        get_client(),
        summary=summary,
        details=details,
        ticket_type=ticket_type,
        customer=customer,
        site=site,
        user=user,
        asset=asset,
        custom_fields=custom_fields,
        submit=submit,
        raw=raw,
    )


# ── Assets (3) — "Devices" in Halo ──────────────────────────────────────────


@mcp.tool()
async def halo_get_asset(asset: str, raw: bool = False) -> str:
    """Read a single asset by name/inventory-number/id — detail + fields + ticket counts."""
    return await _get_asset(get_client(), asset=asset, raw=raw)


@mcp.tool()
async def halo_list_assets(
    customer: Optional[str] = None,
    assettype_id: Optional[int] = None,
    search: Optional[str] = None,
    raw: bool = False,
) -> str:
    """List/search assets, optionally scoped by customer, asset type, or free text."""
    return await _list_assets(
        get_client(), customer=customer, assettype_id=assettype_id, search=search, raw=raw
    )


@mcp.tool()
async def halo_get_asset_relationships(asset: str, raw: bool = False) -> str:
    """Get an asset's CMDB/CI hierarchy and relationship context (by name or id)."""
    return await _get_asset_relationships(get_client(), asset=asset, raw=raw)


# ── Context (4) — clients / sites / users / contracts ───────────────────────


@mcp.tool()
async def halo_list_clients(search: Optional[str] = None, raw: bool = False) -> str:
    """List/search Halo clients (customers). Use to resolve a client name to its id."""
    return await _list_clients(get_client(), search=search, raw=raw)


@mcp.tool()
async def halo_list_sites(
    customer: Optional[str] = None, search: Optional[str] = None, raw: bool = False
) -> str:
    """List/search sites, optionally scoped to a customer (name or id)."""
    return await _list_sites(get_client(), customer=customer, search=search, raw=raw)


@mcp.tool()
async def halo_list_users(
    customer: Optional[str] = None,
    site_id: Optional[int] = None,
    search: Optional[str] = None,
    raw: bool = False,
) -> str:
    """List/search users/contacts, optionally scoped to a customer or site."""
    return await _list_users(
        get_client(), customer=customer, site_id=site_id, search=search, raw=raw
    )


@mcp.tool()
async def halo_list_contracts(customer: Optional[str] = None, raw: bool = False) -> str:
    """List client contracts/agreements, optionally scoped to a customer."""
    return await _list_contracts(get_client(), customer=customer, raw=raw)


# ── Knowledge (2) — KB articles ─────────────────────────────────────────────


@mcp.tool()
async def halo_list_kb_articles(search: Optional[str] = None, raw: bool = False) -> str:
    """Search the Halo knowledge base for articles (resolution/runbook context)."""
    return await _list_kb_articles(get_client(), search=search, raw=raw)


@mcp.tool()
async def halo_get_kb_article(article: str, raw: bool = False) -> str:
    """Get a single KB article by numeric id, including its body."""
    return await _get_kb_article(get_client(), article=article, raw=raw)


# ---------------------------------------------------------------------------
# Testability exports
# ---------------------------------------------------------------------------

#: The 18 core tool functions (module-level, for test introspection).
TOOL_FUNCS = [
    _list_ticket_types,
    _get_ticket_type,
    _list_fields,
    _get_field,
    _get_ticket,
    _list_tickets,
    _get_ticket_actions,
    _get_asset_tickets,
    _create_change_request,
    _get_asset,
    _list_assets,
    _get_asset_relationships,
    _list_clients,
    _list_sites,
    _list_users,
    _list_contracts,
    _list_kb_articles,
    _get_kb_article,
]

#: The 18 registered MCP tool names (authoritative for test assertions).
REGISTERED_TOOL_NAMES = [
    "halo_list_ticket_types",
    "halo_get_ticket_type",
    "halo_list_fields",
    "halo_get_field",
    "halo_get_ticket",
    "halo_list_tickets",
    "halo_get_ticket_actions",
    "halo_get_asset_tickets",
    "halo_create_change_request",
    "halo_get_asset",
    "halo_list_assets",
    "halo_get_asset_relationships",
    "halo_list_clients",
    "halo_list_sites",
    "halo_list_users",
    "halo_list_contracts",
    "halo_list_kb_articles",
    "halo_get_kb_article",
]

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(
        "Starting halo-mcp server (transport=stdio, base_url=%s, tools=%d)",
        HALO_BASE_URL or "(unset)",
        len(REGISTERED_TOOL_NAMES),
    )
    mcp.run()
