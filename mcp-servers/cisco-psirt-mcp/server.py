#!/usr/bin/env python3
"""cisco-psirt MCP server — Cisco PSIRT openVuln advisory intelligence.

Spec 078 (roadmap R2). Transport: stdio. Server id: `cisco-psirt`.

Read-only and device-free: this server talks to Cisco's API and nothing else. It
never opens a session to a device and never writes anywhere except its own advisory
cache (FR-018). Versions arrive from the caller, collected by `pyATS` or
`multivendor-cli` — which is why the two-step chain is documented in the skill.

## The one thing to understand before reading further

**An empty advisory list is not a clean bill of health.** Five outcomes exist so that
"Cisco published nothing" and "we never managed to ask" can never be confused:

    advisories_found      Cisco has published advisories for this version
    none_published        Cisco has published nothing — NOT "the device is safe"
    normalisation_failed  the version could not be parsed — the question went unasked
    unsupported_ostype    not a PSIRT OSType (this includes iosxr)
    api_error             auth, rate limit, or a rejected version format

All five are *successful tool calls carrying a typed outcome*, never protocol
errors, so the agent can read why and act rather than seeing an opaque failure.

## What this API does not provide

Measured, not assumed — stated here so nobody re-litigates it from Cisco's docs:

    Bug / EoX / Case / Serial-to-Info   HTTP 403 under the API Console grant (FR-016)
    CX Cloud (7 paths)                  HTTP 504, unreachable (FR-017)
    OSType iosxr                        HTTP 404 on every version — not an OSType
"""

from __future__ import annotations

import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import TokenProvider  # noqa: E402
from cache import AdvisoryCache  # noqa: E402
from normalise import (  # noqa: E402
    FORMAT_EXAMPLE,
    SUPPORTED_OSTYPES,
    VERIFIED_OSTYPES,
    collection_note,
    is_supported,
    is_verified,
    normalise,
    unsupported_reason,
)
from psirt import ApiError, PsirtClient  # noqa: E402
from ratelimit import PER_MINUTE, PER_SECOND, RateLimiter, dedupe  # noqa: E402

SERVER = "cisco-psirt"

mcp = FastMCP("cisco-psirt")

_tokens = TokenProvider()
_limiter = RateLimiter()
_cache = AdvisoryCache()
_client = PsirtClient(tokens=_tokens, limiter=_limiter)

# Platforms an operator may reasonably point at this server, which it cannot answer
# for. Naming them beats a generic refusal, and pointing at the right tool beats both.
_NON_CISCO_HINTS = {
    "junos": "Juniper", "eos": "Arista", "sros": "Nokia", "srlinux": "Nokia SR Linux",
    "nxos-cli": "use 'nxos'", "panos": "Palo Alto", "fortios": "Fortinet",
    "iosv": "use 'ios'", "cumulus": "NVIDIA Cumulus", "frr": "FRRouting",
    "vyos": "VyOS", "aruba": "HPE Aruba", "hpe": "HPE", "huawei": "Huawei",
}


def _base(**extra) -> dict:
    """Every result carries the server id, so it never conflicts with `nvd-cve`."""
    out: dict[str, Any] = {"server": SERVER}
    out.update(extra)
    return out


def _caveat_for(ostype: str, advisories: list) -> str | None:
    """The stronger warning an empty result deserves from an unverified family.

    An empty list from a family whose normaliser has never returned a live 200 may be
    a normalisation bug rather than a fact about Cisco's publications (FR-004b). All
    seven families are currently verified, so this returns None in practice — it stays
    because the moment Cisco adds an OSType, the new one will be unverified and this
    is the mechanism that says so.
    """
    if advisories:
        return None
    if not is_verified(ostype):
        return ("This family's version normaliser is unverified: no live query has "
                "confirmed the format. An empty result may reflect a normalisation "
                "error rather than an absence of advisories. Confirm manually.")
    return ("No Cisco advisory is published for this version. This is NOT a statement "
            "that the device is secure — it means Cisco has published nothing matching "
            "this exact version.")


def _run_lookup(kind: str, key_parts: tuple, fetch, refresh: bool) -> tuple[list, str, int | None]:
    """Cache-then-fetch, returning (advisories, cache_state, age).

    Order matters and is contractual (research R5): the cache is consulted before any
    call is considered, because 30 calls/minute is the binding constraint.
    """
    if not refresh:
        cached, age = _cache.get(kind, *key_parts)
        if cached is not None:
            return cached, "hit", age
    advisories, api_path = fetch()
    _cache.put(advisories, api_path, kind, *key_parts)
    return advisories, ("refreshed" if refresh else "miss"), None


@mcp.tool()
def check_version(ostype: str, version: str, refresh: bool = False) -> dict:
    """Check whether a Cisco OS version has published PSIRT advisories.

    Args:
        ostype: one of ios, iosxe, nxos, asa, fmc, ftd, aci. `iosxr` is NOT
            supported — it returns 404 on this API for every version.
        version: the running version. REQUIRED — never inferred or defaulted.
            Accepts a bare version or full `show version` output. The expected
            format differs per family: 17.3.1 (iosxe), 15.2(4)E (ios), 9.3(5)
            (nxos), 9.16.1 (asa), 7.0.1 (ftd/fmc), 15.2(3e) (aci, the SWITCH
            image version, not the APIC version).
        refresh: bypass the 6-hour cache. For incident use, where cache age is
            itself the question. Reported back as cache="refreshed" so over-use is
            visible — passing it always silently disables the cache.

    An empty `advisories` list with outcome `none_published` means Cisco has
    published nothing for this version. It does NOT mean the device is secure.
    """
    key = (ostype or "").strip().lower()

    # A non-Cisco platform is out of scope, not an error to be attempted (FR-010).
    if key in _NON_CISCO_HINTS:
        return _base(ostype=ostype, version_raw=version, version_normalised=None,
                     normaliser_verified=False, outcome="unsupported_ostype",
                     advisories=[], cache="miss",
                     caveat=f"{ostype!r} is not a Cisco OS. The PSIRT API covers Cisco "
                            f"products only ({_NON_CISCO_HINTS[key]}). For non-Cisco "
                            f"platforms use the nvd-cve integration instead.")

    if not is_supported(key):
        return _base(ostype=ostype, version_raw=version, version_normalised=None,
                     normaliser_verified=False, outcome="unsupported_ostype",
                     advisories=[], cache="miss", caveat=unsupported_reason(ostype),
                     supported_ostypes=list(SUPPORTED_OSTYPES))

    norm = normalise(key, version)
    if norm.failed:
        # FR-009a: a parse failure is a failure. Never an empty advisory list, which
        # would read as "not vulnerable" when nothing was ever checked.
        return _base(ostype=key, version_raw=norm.raw, version_normalised=None,
                     normaliser_verified=is_verified(key),
                     outcome="normalisation_failed", advisories=[], cache="miss",
                     caveat=f"Could not determine a version to query: {norm.reason} "
                            f"NOTHING WAS CHECKED — this is not a statement that the "
                            f"device is unaffected.",
                     expected_format=FORMAT_EXAMPLE.get(key))

    try:
        advisories, cache_state, age = _run_lookup(
            key, (norm.value,), lambda: _client.by_os_version(key, norm.value), refresh)
    except ApiError as exc:
        return _base(ostype=key, version_raw=norm.raw, version_normalised=norm.value,
                     normaliser_verified=is_verified(key), outcome="api_error",
                     advisories=[], cache="miss", error=str(exc),
                     caveat="The query did not complete, so no conclusion about this "
                            "device can be drawn from this result.",
                     expected_format=FORMAT_EXAMPLE.get(key),
                     collection_note=collection_note(key))

    result = _base(
        ostype=key, version_raw=norm.raw, version_normalised=norm.value,
        normaliser_verified=is_verified(key),
        outcome="advisories_found" if advisories else "none_published",
        advisories=advisories, advisory_count=len(advisories),
        cache=cache_state, caveat=_caveat_for(key, advisories))
    if age is not None:
        result["cache_age_seconds"] = age
    if collection_note(key):
        result["collection_note"] = collection_note(key)
    return result


@mcp.tool()
def check_versions(devices: list[dict], refresh: bool = False) -> dict:
    """Check a fleet, de-duplicating by version so the rate budget survives it.

    Args:
        devices: [{"name": "...", "ostype": "iosxe", "version": "17.3.1"}, ...]
        refresh: bypass the cache for every distinct version.

    De-duplication happens before anything else and is the reason this scales: 60
    devices running 12 distinct versions cost 12 calls, not 60 — one-third of the
    30/min budget instead of twice it (FR-013, research R5).

    One device failing never aborts the others (FR-011); each carries its own
    outcome.
    """
    if not devices:
        return _base(outcome="normalisation_failed", devices=[],
                     error="no devices supplied")

    keys = [((d.get("ostype") or "").strip().lower(),
             (d.get("version") or "")) for d in devices]
    groups = dedupe(keys)

    results: list[dict] = [None] * len(devices)  # type: ignore[list-item]
    for (ostype, version), positions in groups.items():
        # One lookup per distinct (ostype, version); fanned out to every device that
        # shares it. A failure is recorded per device rather than raised.
        try:
            answer = check_version(ostype, version, refresh=refresh)
        except Exception as exc:  # never let one device abort the sweep (FR-011)
            answer = _base(ostype=ostype, version_raw=version, outcome="api_error",
                           advisories=[], cache="miss",
                           error=f"{type(exc).__name__}: {exc}")
        for index in positions:
            entry = dict(answer)
            entry["device"] = devices[index].get("name")
            results[index] = entry

    by_outcome: dict[str, int] = {}
    for entry in results:
        by_outcome[entry["outcome"]] = by_outcome.get(entry["outcome"], 0) + 1

    return _base(
        devices=results,
        device_count=len(devices),
        distinct_versions=len(groups),
        api_calls_saved_by_dedup=len(devices) - len(groups),
        outcome_summary=by_outcome,
        note="A 'none_published' device is not a device confirmed secure. Check "
             "'normalisation_failed' and 'api_error' counts before concluding a fleet "
             "is clean — those devices were never checked.")


@mcp.tool()
def check_cve(cve: str, refresh: bool = False) -> dict:
    """Find Cisco advisories for a CVE id.

    `none_published` here means Cisco has issued no advisory for this CVE. It does
    not mean the CVE is harmless, and it does not mean NVD has nothing — the
    `nvd-cve` integration answers the NVD side. Either can legitimately be empty
    while the other is not (FR-015).
    """
    cve_id = (cve or "").strip().upper()
    if not cve_id.startswith("CVE-"):
        return _base(cve=cve, outcome="normalisation_failed", advisories=[],
                     cache="miss",
                     error=f"{cve!r} is not a CVE id. Expected the form CVE-2024-20353.")
    try:
        advisories, cache_state, age = _run_lookup(
            "cve", (cve_id,), lambda: _client.by_cve(cve_id), refresh)
    except ApiError as exc:
        return _base(cve=cve_id, outcome="api_error", advisories=[], cache="miss",
                     error=str(exc))
    result = _base(cve=cve_id,
                   outcome="advisories_found" if advisories else "none_published",
                   advisories=advisories, advisory_count=len(advisories),
                   cache=cache_state,
                   caveat=None if advisories else
                   "Cisco has published no advisory for this CVE. That is a statement "
                   "about Cisco's publications only — not about the CVE's severity, and "
                   "not about what NVD holds. Check the nvd-cve integration for that.")
    if age is not None:
        result["cache_age_seconds"] = age
    return result


@mcp.tool()
def check_advisory(advisory_id: str) -> dict:
    """Fetch one advisory by id, e.g. `cisco-sa-bootp-WuBhNBxA`."""
    ident = (advisory_id or "").strip()
    if not ident:
        return _base(outcome="normalisation_failed", advisories=[], cache="miss",
                     error="advisory_id is required")
    try:
        advisories, cache_state, age = _run_lookup(
            "advisory", (ident,), lambda: _client.by_advisory(ident), False)
    except ApiError as exc:
        return _base(advisory_id=ident, outcome="api_error", advisories=[],
                     cache="miss", error=str(exc))
    result = _base(advisory_id=ident,
                   outcome="advisories_found" if advisories else "none_published",
                   advisories=advisories, cache=cache_state)
    if age is not None:
        result["cache_age_seconds"] = age
    return result


@mcp.tool()
def list_recent(severity: str = "critical", start_date: str = "", end_date: str = "") -> dict:
    """List advisories of a severity first published in a date range.

    Args:
        severity: critical | high | medium | low
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD

    Verified: severity=critical over 2026-01-01 → 2026-07-31 returned 15 advisories.
    """
    sev = (severity or "").strip().lower()
    if sev not in ("critical", "high", "medium", "low"):
        return _base(outcome="normalisation_failed", advisories=[], cache="miss",
                     error=f"{severity!r} is not a severity. Use critical, high, "
                           f"medium or low.")
    if not start_date or not end_date:
        return _base(outcome="normalisation_failed", advisories=[], cache="miss",
                     error="start_date and end_date are both required (YYYY-MM-DD)")
    try:
        advisories, cache_state, age = _run_lookup(
            "severity", (sev, start_date, end_date),
            lambda: _client.by_severity_range(sev, start_date, end_date), False)
    except ApiError as exc:
        return _base(severity=sev, outcome="api_error", advisories=[], cache="miss",
                     error=str(exc))
    result = _base(severity=sev, start_date=start_date, end_date=end_date,
                   outcome="advisories_found" if advisories else "none_published",
                   advisories=advisories, advisory_count=len(advisories),
                   cache=cache_state)
    if age is not None:
        result["cache_age_seconds"] = age
    return result


@mcp.tool()
def psirt_status() -> dict:
    """Report auth state, rate budget, cache stats and which OSTypes are supported.

    Call this before a fleet sweep to see how much of the 30/min budget is left.
    Contains no credential values — only whether the variables are set.
    """
    auth = _tokens.status()
    return _base(
        authenticated=auth["authenticated"],
        configured=auth["configured"],
        missing_variables=auth["missing_variables"],
        token_expires_in_seconds=auth["token_expires_in_seconds"],
        rate_budget={"per_second": PER_SECOND, "per_minute": PER_MINUTE,
                     "calls_remaining_estimate": _limiter.calls_remaining()},
        cache=_cache.stats(),
        supported_ostypes=list(SUPPORTED_OSTYPES),
        verified_ostypes=sorted(VERIFIED_OSTYPES),
        version_format_examples=FORMAT_EXAMPLE,
        unavailable={
            "iosxr": "404 on every version — not an OSType on this API",
            "bug_eox_case_serial": "403 under the API Console grant (out of scope)",
            "cx_cloud": "504 on all seven paths tried (out of scope)",
        },
        read_only=True,
        note="This server never contacts a device. Collect versions with pyATS or "
             "multivendor-cli, then pass them here.")


if __name__ == "__main__":
    mcp.run(transport="stdio")
