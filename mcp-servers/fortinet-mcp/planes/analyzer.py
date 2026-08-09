"""Analyzer plane — FortiAnalyzer observed traffic. Spec 080, FR-018a..c.

The only plane that can answer "is this rule dead?". The manager knows a rule
exists; only the analyzer knows whether anything ever matched it.

THE ERROR THIS MODULE EXISTS TO PREVENT
---------------------------------------
"No logs matched" is NOT "this rule is unused". A retention window is not all of
history, log forwarding may be off, and the analyzer may simply not have been
receiving from that device. Reporting an empty window as "unused" would license
someone to delete a live firewall rule.

This is the same error class as spec 078's "no advisories != not vulnerable" and
spec 079's "no probes found != outage", and it gets the same treatment: a
separate, explicitly-named outcome (`no_logs_in_window`) that cannot be confused
with `ok` or with an error.

Shares the JSON-RPC transport with FortiManager (research R2) — same `/jsonrpc`
endpoint, same envelope, different methods.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from envelope import Outcome, Plane, emit, unreachable
from transport.jsonrpc import JsonRpcClient, JsonRpcError

#: Applied when a caller supplies no window. Stated in the response rather than
#: assumed silently (FR-018c) — an unbounded log query against a busy analyzer is
#: both slow and misleading.
DEFAULT_WINDOW_HOURS = 24


def _window(start: str | None, end: str | None) -> tuple[str, str, bool]:
    """Return (start, end, defaulted)."""
    if start and end:
        return start, end, False
    now = datetime.now(timezone.utc)
    return (
        (now - timedelta(hours=DEFAULT_WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        True,
    )


def _fail(client: JsonRpcClient, exc: JsonRpcError, tool: str) -> dict[str, Any]:
    if exc.outcome is Outcome.PLANE_UNREACHABLE:
        return unreachable(Plane.ANALYZER, client.source, str(exc), tool=tool)
    return emit(Plane.ANALYZER, source=client.source, outcome=exc.outcome,
                message=str(exc), tool=tool)


async def query_logs(
    client: JsonRpcClient, adom: str, filter_expr: str,
    window_start: str | None = None, window_end: str | None = None,
    limit: int = 100, offset: int = 0,
) -> dict[str, Any]:
    """Query traffic logs within a bounded window. FR-018a/b/c."""
    tool = "faz_query_logs"
    start, end, defaulted = _window(window_start, window_end)

    try:
        data = await client.call(
            "add", f"/logview/adom/{adom}/logsearch",
            filter=filter_expr, logtype="traffic",
            time_range={"start": start, "end": end},
            limit=limit, offset=offset,
        )
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    entries = (data or {}).get("data") or []
    total = (data or {}).get("total", len(entries))
    notes = []
    if defaulted:
        notes.append(
            f"No window was supplied, so the last {DEFAULT_WINDOW_HOURS} hours were "
            f"queried ({start} to {end}). Results describe that window only."
        )

    return emit(
        Plane.ANALYZER, source=client.source,
        scope={"adom": adom, "window_start": start, "window_end": end},
        data={
            "entries": entries, "total": total,
            "has_more": (offset + len(entries)) < total,
            "next_offset": offset + len(entries),
            "filter": filter_expr,
        },
        outcome=Outcome.OK if entries else Outcome.NO_LOGS_IN_WINDOW,
        message=None if entries else (
            f"No logs matched {filter_expr!r} between {start} and {end}. "
            "This is NOT evidence that the rule is unused — it means nothing "
            "matched in this window."
        ),
        notes=notes, tool=tool,
    )


async def fetch_more(
    client: JsonRpcClient, adom: str, filter_expr: str,
    window_start: str, window_end: str, offset: int, limit: int = 100,
) -> dict[str, Any]:
    """Next page of a log query. FR-018a.

    Re-runs the search at a new offset rather than reusing FortiAnalyzer's task
    id. FortiAnalyzer `tid`s are single-use and expire; treating one as a durable
    cursor produces silent truncation — a bug avoided by reading how
    `rstierli/fortianalyzer-mcp` handles it (research R1).
    """
    return await query_logs(
        client, adom, filter_expr,
        window_start=window_start, window_end=window_end,
        limit=limit, offset=offset,
    )


async def policy_activity(
    client: JsonRpcClient, adom: str, policyid: int,
    window_start: str | None = None, window_end: str | None = None,
) -> dict[str, Any]:
    """Did anything match this policy in the window? FR-018a/b.

    The tool most likely to be misread, so the guard lives here rather than in
    the skill: an empty result is reported as `no_logs_in_window` with an
    explicit statement that it is not evidence of disuse.
    """
    tool = "faz_policy_activity"
    start, end, defaulted = _window(window_start, window_end)

    try:
        data = await client.call(
            "add", f"/logview/adom/{adom}/logsearch",
            filter=f"policyid={policyid}", logtype="traffic",
            time_range={"start": start, "end": end}, limit=1,
        )
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    total = (data or {}).get("total", 0)
    matched = total > 0
    notes = []
    if defaulted:
        notes.append(f"Default {DEFAULT_WINDOW_HOURS}h window applied: {start} to {end}.")
    if not matched:
        notes.append(
            "Before concluding a rule is dead, confirm the device forwards logs "
            "to this analyzer and that retention covers the period of interest."
        )

    return emit(
        Plane.ANALYZER, source=client.source,
        scope={"adom": adom, "window_start": start, "window_end": end},
        data={"policyid": policyid, "sessions_matched": total, "matched": matched},
        outcome=Outcome.OK if matched else Outcome.NO_LOGS_IN_WINDOW,
        message=None if matched else (
            f"No sessions matched policy {policyid} between {start} and {end}. "
            "This is NOT evidence the rule is unused."
        ),
        notes=notes, tool=tool,
    )


async def list_devices(client: JsonRpcClient, adom: str) -> dict[str, Any]:
    """Devices logging to this analyzer. FR-018a.

    Worth calling before concluding anything from an empty log query: a device
    that never forwarded logs will always look idle.
    """
    tool = "faz_list_devices"
    try:
        data = await client.call("get", f"/dvmdb/adom/{adom}/device")
    except JsonRpcError as exc:
        return _fail(client, exc, tool)

    devices = [
        {"name": d.get("name"), "serial": d.get("sn"), "ip": d.get("ip")}
        for d in (data or [])
    ]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return emit(
        Plane.ANALYZER, source=client.source,
        scope={"adom": adom, "window_start": now, "window_end": now},
        data={"devices": devices, "count": len(devices)},
        outcome=Outcome.OK if devices else Outcome.EMPTY_RESULT, tool=tool,
    )
