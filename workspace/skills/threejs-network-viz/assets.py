"""
Real-3D-model ("real-stencil") asset resolution chain for User Story 5.

Resolution order per device role (spec.md FR-019, FR-020, FR-021):
  1. check_cached_asset()   - an already-resolved/user-supplied local asset
  2. search_sketchfab_cc0() + verify_cc0_license() + download_and_embed()
     - Sketchfab is the only automated network source, reached via the
       vendored `sketchfab-mcp-server` (mcp-servers/sketchfab-mcp-server/,
       registered as `sketchfab-mcp` in config/openclaw.json)
  3. procedural fallback, with a FallbackNote explaining why

FR-020 (never auto-fetch from gated marketplaces like Fab/TurboSquid/
CGTrader/GrabCAD) is satisfied by construction: no code path in this module
calls anything but the Sketchfab MCP and the local filesystem. A
manually-placed asset from ANY source (including a gated marketplace the
engineer downloaded from by hand) is picked up only via check_cached_asset's
local-file check, never fetched automatically.

The vendored sketchfab-mcp-server was patched during implementation of this
story: its sketchfab-model-details tool silently dropped the license field
from its formatted output (a real bug found via a live API call during
development — see mcp-servers/sketchfab-mcp-server/index.ts's "NetClaw
patch" comments). Without that fix, FR-019a's per-model CC0 verification
would have nothing to verify against.
"""

import asyncio
import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# The vendored sketchfab-mcp-server writes two plain console.log() lines to
# stdout around its stdio-transport handshake ("Sketchfab API key provided",
# "MCP Server running on stdio") instead of confining stdout to JSON-RPC
# only — a real bug in that server, found live during development. The
# official mcp SDK's stdio client tolerates this (skips the unparseable
# line and continues) but logs a full traceback per occurrence; silenced
# here since it's non-fatal noise, not an actionable error for our callers.
logging.getLogger("mcp.client.stdio").setLevel(logging.CRITICAL)

from topology_model import AssetKind, DeviceAsset, FallbackNote, FallbackReason, ModelSource, ProceduralShape

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVER_SCRIPT = _REPO_ROOT / "mcp-servers" / "sketchfab-mcp-server" / "build" / "index.js"

_ASSET_ROOT = Path(__file__).resolve().parents[2] / "output" / "threejs-network-viz" / "assets"
_CACHE_DIR = _ASSET_ROOT / "sketchfab-cache"
_USER_ASSET_DIR = _ASSET_ROOT / "user-supplied"

_CC0_LICENSE_SLUG = "cc0"

# Search terms per role — network-gear-specific CC0 content is close to
# nonexistent on Sketchfab in practice (confirmed by live searches during
# development: "router"/"server rack"/"electronic box" with a CC0 filter
# returned zero or irrelevant results), so these lean on generic
# electronics/box-shaped terms that are at least topically plausible, with
# procedural fallback expected to be the common outcome, not an edge case.
_ROLE_SEARCH_TERMS = {
    "router": "network router electronics box",
    "switch": "network switch electronics box",
    "firewall": "server rack electronics box",
    "load_balancer": "server rack electronics box",
    "client": "computer workstation",
}


def _server_env() -> dict:
    env = dict(os.environ)
    api_key = os.environ.get("SKETCHFAB_API_KEY", "")
    env["SKETCHFAB_API_KEY"] = api_key
    return env


async def _call_tool_async(tool_name: str, arguments: dict) -> str:
    params = StdioServerParameters(
        command="node", args=[str(_SERVER_SCRIPT)], env=_server_env()
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return "\n".join(
                block.text for block in result.content if hasattr(block, "text")
            )


def _call_tool(tool_name: str, arguments: dict) -> str:
    """Sync wrapper — this module's callers (scene assembly) are synchronous,
    matching the rest of this skill's non-async architecture."""
    return asyncio.run(_call_tool_async(tool_name, arguments))


def check_cached_asset(role: str) -> Optional[DeviceAsset]:
    """
    Check for an already-resolved (cached Sketchfab download) or
    manually-supplied local asset for this role, before attempting any
    network fetch. This is also the ONLY path by which a gated-marketplace
    asset (Fab, TurboSquid, CGTrader, GrabCAD) can ever be used — the
    engineer places it by hand; this skill never fetches from those
    marketplaces itself (FR-020).
    """
    for directory, source in ((_CACHE_DIR, ModelSource.CACHE), (_USER_ASSET_DIR, ModelSource.USER_SUPPLIED)):
        candidate = directory / f"{role}.glb"
        if candidate.is_file():
            encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
            return DeviceAsset(
                kind=AssetKind.REAL_MODEL,
                model_source=source,
                # _CACHE_DIR is only ever populated by resolve_device_asset()
                # after a live verify_cc0_license() pass (see below), so
                # re-asserting "cc0" here is safe, not presumptuous.
                model_license_slug="cc0" if source == ModelSource.CACHE else None,
                embedded_glb_base64=encoded,
            )
    return None


def search_sketchfab_cc0(role: str) -> list[str]:
    """
    Search Sketchfab (via sketchfab-mcp's sketchfab-search tool) for
    candidate models for this role. The tool has no license parameter, so
    these are UNVERIFIED candidates — verify_cc0_license() MUST be called
    on each before use (FR-019a).
    """
    query = _ROLE_SEARCH_TERMS.get(role, role)
    # Deliberately NOT swallowing exceptions here — resolve_device_asset()
    # distinguishes "search failed/unreachable" (SOURCE_UNREACHABLE) from
    # "search succeeded but found nothing verifiable" (NO_CC0_CANDIDATE_FOUND).
    text = _call_tool("sketchfab-search", {"query": query, "downloadable": True, "limit": 8})
    return re.findall(r"^ID:\s*(\S+)$", text, flags=re.MULTILINE)


def verify_cc0_license(model_uid: str) -> bool:
    """
    Fetch model details (sketchfab-model-details) and accept ONLY an exact
    license.slug == "cc0" match (research.md §3, FR-019a) — never trust the
    search tool's "downloadable" filter alone, since Sketchfab's catalog is
    mixed-license.
    """
    try:
        text = _call_tool("sketchfab-model-details", {"modelId": model_uid})
    except Exception:
        return False
    match = re.search(r"^License:\s*(\{.*\})\s*$", text, flags=re.MULTILINE)
    if not match:
        return False
    try:
        license_obj = json.loads(match.group(1))
    except (json.JSONDecodeError, TypeError):
        return False
    return license_obj.get("slug") == _CC0_LICENSE_SLUG


def download_and_embed(model_uid: str) -> Optional[str]:
    """
    Download the model in glb format (sketchfab-download) and return it
    base64-encoded, ready for direct embedding into the generated HTML
    (FR-001, FR-019) — never a linked/separate file. Returns None if a
    genuine .glb isn't available for this model (Sketchfab doesn't
    auto-convert every downloadable model to glTF/GLB — confirmed live
    during development), which the caller treats as a fallback condition,
    not an error.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _CACHE_DIR / f"_download_{model_uid}.glb"
    try:
        text = _call_tool(
            "sketchfab-download",
            {"modelId": model_uid, "format": "glb", "outputPath": str(output_path)},
        )
    except Exception:
        return None

    # Only accept the exact-format-honored success message — the tool
    # silently substitutes a different format (source/gltf/usdz) when glb
    # isn't available for a given model, which we must NOT mistake for a
    # real glb.
    if "in glb format." not in text or "requested glb was not available" in text:
        output_path.unlink(missing_ok=True)
        return None

    save_match = re.search(r"Saved to:\s*(.+)$", text, flags=re.MULTILINE)
    if not save_match:
        return None
    saved_path = Path(save_match.group(1).strip())
    if not saved_path.is_file():
        return None

    return base64.b64encode(saved_path.read_bytes()).decode("ascii")


def resolve_device_asset(
    hostname: str, role: str, real_stencil_mode: bool
) -> tuple[DeviceAsset, Optional[FallbackNote]]:
    """Full resolution chain for one device's visual asset. Always returns a
    valid DeviceAsset (procedural fallback on any non-success path) plus an
    optional FallbackNote explaining why, per FR-021."""
    if not real_stencil_mode:
        return DeviceAsset(kind=AssetKind.PROCEDURAL), None

    cached = check_cached_asset(role)
    if cached is not None:
        return cached, None

    try:
        candidates = search_sketchfab_cc0(role)
    except Exception:
        return (
            DeviceAsset(kind=AssetKind.PROCEDURAL),
            FallbackNote(hostname=hostname, role=role, reason=FallbackReason.SOURCE_UNREACHABLE),
        )

    for model_uid in candidates:
        if not verify_cc0_license(model_uid):
            continue
        embedded = download_and_embed(model_uid)
        if embedded is None:
            continue
        # Cache the accepted download for future requests (T034's reuse tier).
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{role}.glb").write_bytes(base64.b64decode(embedded))
        return (
            DeviceAsset(
                kind=AssetKind.REAL_MODEL,
                model_source=ModelSource.SKETCHFAB,
                model_license_slug=_CC0_LICENSE_SLUG,
                embedded_glb_base64=embedded,
            ),
            None,
        )

    return (
        DeviceAsset(kind=AssetKind.PROCEDURAL, procedural_shape=None),
        FallbackNote(hostname=hostname, role=role, reason=FallbackReason.NO_CC0_CANDIDATE_FOUND),
    )
