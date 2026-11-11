#!/usr/bin/env python3
"""result-analysis-mcp -- read-only, declarative analysis of retained large results (spec 187).

Issue #322: a complete 170 KB+ diagnostic result reaches the agent truncated by the host, and
the agent (correctly) refuses to count it. NetClaw cannot change the host limit, so producers
retain the COMPLETE result and hand out a handle; this server answers bounded questions about
the handle and states, in every response, exactly what the answer covered.

No code execution, no SQL, no regex, no device access, no command re-run. Filters are
(field, op, literal) triples. Read-only: it never writes to a device and never modifies a
retained result.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP  # noqa: E402

import result_query as query  # noqa: E402
import result_retention as retention  # noqa: E402

mcp = FastMCP("result-analysis-mcp")


def _err(op: str, msg: str, handle: str | None = None) -> dict:
    return {"operation": op, "handle": handle, "error": msg, "complete": False,
            "note": "No answer was produced; do not infer a count or total."}


def _open(op: str, handle: str):
    try:
        meta, payload = retention.load(handle)
    except retention.HandleError as exc:
        return None, None, _err(op, str(exc), handle)
    retention._audit("query", handle=handle, operation=op)
    return meta, payload, None


@mcp.tool()
def result_status() -> dict:
    """Show limits and what this surface will and will not do."""
    return {
        "operation": "result_status",
        "limits": {"inline_budget_chars": retention.inline_budget(),
                   "max_result_bytes": retention.max_result_bytes(),
                   "store_max_bytes": retention.max_store_bytes(),
                   "ttl_seconds": retention.ttl_seconds(),
                   "max_scan_records": query.max_scan(),
                   "max_page_records": query.MAX_PAGE,
                   "max_response_chars": query.MAX_RESPONSE_CHARS},
        "store": str(retention.store_dir()),
        "never": ["execute code, SQL, shell or regex", "contact devices or re-run commands",
                  "modify a retained result"],
        "ops": sorted(query.OPS),
    }


@mcp.tool()
def result_list() -> dict:
    """List live retained results (handle, source command/device, size, time). No contents."""
    return {"operation": "result_list", "results": retention.list_handles()}


@mcp.tool()
def result_describe(handle: str) -> dict:
    """Describe a retained result: source facts, shape, record collections, field names, and
    any retention truncation or producer filtering notes. Start here."""
    meta, payload, err = _open("result_describe", handle)
    if err:
        return err
    out: dict = {"operation": "result_describe", "handle": handle, "meta": {
        k: meta.get(k) for k in ("tool", "device", "command", "retrieved_at", "expires_at",
                                 "kind", "source_bytes", "source_sha256", "retained_bytes",
                                 "retention_truncated", "retention_truncation",
                                 "producer_notes", "stream")}}
    if isinstance(payload, str):
        out["lines_total"] = len(payload.splitlines())
    else:
        cands = query.find_collections(payload)
        out["record_collections"] = cands[:10]
        if cands:
            recs = query.get_records(payload, cands[0]["path"])
            out["fields_seen_in_first_500"] = sorted(
                {k for r in recs[:500] if isinstance(r, dict) for k in r})[:60]
            out["sample_records"] = recs[:2]
    out["coverage"] = query.coverage(meta, total=None, scanned=None, matched=None)
    return out


def _prep(op, handle, record_path):
    meta, payload, err = _open(op, handle)
    if err:
        return None, None, None, err
    try:
        recs = query.get_records(payload, record_path)
    except query.QueryError as exc:
        return None, None, None, _err(op, str(exc), handle)
    return meta, payload, recs, None


@mcp.tool()
def result_count(handle: str, where: list[dict] | None = None, group_by: list[str] | None = None,
                 record_path: str | None = None, case_insensitive: bool = False,
                 time_field: str | None = None, since: str | None = None,
                 until: str | None = None) -> dict:
    """Exact count (optionally grouped) of records matching `where`, over the WHOLE retained
    result. where = [{"field": "_key", "op": "startswith", "value": "Tunnel"}] ; for a
    dict-keyed collection (e.g. interface name) the key is the pseudo-field `_key`.
    group_by = ["status"]. since/until (ISO-8601, until exclusive) need time_field; records
    lacking a usable timestamp are excluded AND reported as a gap. Read `coverage.complete`
    before presenting any number as a total."""
    meta, payload, recs, err = _prep("result_count", handle, record_path)
    if err:
        return err
    try:
        s = query.scan(recs, where, ci=case_insensitive, time_field=time_field,
                       since=since, until=until)
    except query.QueryError as exc:
        return _err("result_count", str(exc), handle)
    groups, overflow = (query.group_count(s["matched"], group_by) if group_by else (None, False))
    reasons, gaps = [], []
    if overflow:
        reasons.append(f"more than {query.MAX_GROUPS} distinct groups; extra groups not counted")
    if s["no_timestamp"]:
        gaps.append(f"{s['no_timestamp']} record(s) had no usable '{time_field}' and could not "
                    "be placed in or out of the window")
    cov = query.coverage(meta, total=s["total"], scanned=s["scanned"], matched=len(s["matched"]),
                         extra_reasons=reasons, gaps=gaps,
                         record_path=query.chosen_path(payload, record_path))
    out = {"operation": "result_count", "handle": handle, "count": len(s["matched"]),
           "coverage": cov}
    if groups is not None:
        out["groups"] = groups
    return out


@mcp.tool()
def result_select(handle: str, where: list[dict] | None = None, fields: list[str] | None = None,
                  offset: int = 0, limit: int = 50, record_path: str | None = None,
                  case_insensitive: bool = False, time_field: str | None = None,
                  since: str | None = None, until: str | None = None) -> dict:
    """One bounded page of matching records (optional field projection). The page is never the
    whole answer unless coverage.truncated_page is false; follow coverage.next_offset."""
    meta, payload, recs, err = _prep("result_select", handle, record_path)
    if err:
        return err
    offset = max(int(offset), 0)
    limit = max(1, min(int(limit), query.MAX_PAGE))
    try:
        s = query.scan(recs, where, ci=case_insensitive, time_field=time_field,
                       since=since, until=until)
    except query.QueryError as exc:
        return _err("result_select", str(exc), handle)
    page = [query.project(r, fields) for r in s["matched"][offset: offset + limit]]
    path = query.chosen_path(payload, record_path)
    gaps = ([f"{s['no_timestamp']} record(s) had no usable '{time_field}'"]
            if s["no_timestamp"] else [])

    def build(rows):
        return {"rows": rows, "coverage": query.coverage(
            meta, total=s["total"], scanned=s["scanned"], matched=len(s["matched"]),
            returned=len(rows), truncated_page=True, next_offset=offset + len(rows),
            record_path=path, gaps=gaps)}

    page, trimmed = query.fit_rows(build, page)
    end = offset + len(page)
    truncated = trimmed or end < len(s["matched"])
    cov = query.coverage(meta, total=s["total"], scanned=s["scanned"],
                         matched=len(s["matched"]), returned=len(page),
                         truncated_page=truncated, next_offset=end if truncated else None,
                         record_path=path, gaps=gaps,
                         extra_reasons=(["response trimmed to fit the response size budget"]
                                        if trimmed else None))
    return {"operation": "result_select", "handle": handle, "rows": page, "coverage": cov}


def _text(op, handle):
    meta, payload, err = _open(op, handle)
    if err:
        return None, None, err
    if not isinstance(payload, str):
        return None, None, _err(op, "retained result is structured JSON; use result_select or "
                                    "result_count", handle)
    return meta, payload.splitlines(), None


@mcp.tool()
def result_lines(handle: str, offset: int = 0, limit: int = 200) -> dict:
    """Page through a plain-text retained result (CLI output, logs) by line number."""
    meta, lines, err = _text("result_lines", handle)
    if err:
        return err
    offset = max(int(offset), 0)
    limit = max(1, min(int(limit), query.MAX_PAGE))
    page = lines[offset: offset + limit]

    def build(rows):
        return {"lines": rows}

    page, trimmed = query.fit_rows(build, page)
    end = offset + len(page)
    truncated = end < len(lines)
    cov = query.coverage(meta, total=len(lines), scanned=len(lines), matched=len(lines),
                         returned=len(page), truncated_page=truncated,
                         next_offset=end if truncated else None)
    return {"operation": "result_lines", "handle": handle, "first_line_number": offset + 1,
            "lines": page, "coverage": cov}


@mcp.tool()
def result_text_search(handle: str, needle: str, case_insensitive: bool = True,
                       context: int = 0, limit: int = 50, offset: int = 0) -> dict:
    """Literal-substring search (NOT regex) over a plain-text retained result. Returns the
    total number of matching lines over ALL lines plus one bounded page of them."""
    meta, lines, err = _text("result_text_search", handle)
    if err:
        return err
    if not needle:
        return _err("result_text_search", "needle must be non-empty", handle)
    n = needle.lower() if case_insensitive else needle
    hits = [i for i, ln in enumerate(lines) if n in (ln.lower() if case_insensitive else ln)]
    context = max(0, min(int(context), 5))
    limit = max(1, min(int(limit), query.MAX_PAGE))
    offset = max(int(offset), 0)
    page = []
    for i in hits[offset: offset + limit]:
        page.append({"line": i + 1, "text": lines[i],
                     "before": lines[max(0, i - context): i] if context else [],
                     "after": lines[i + 1: i + 1 + context] if context else []})

    def build(rows):
        return {"matches": rows}

    page, trimmed = query.fit_rows(build, page)
    end = offset + len(page)
    truncated = end < len(hits)
    cov = query.coverage(meta, total=len(lines), scanned=len(lines), matched=len(hits),
                         returned=len(page), truncated_page=truncated,
                         next_offset=end if truncated else None)
    return {"operation": "result_text_search", "handle": handle, "matching_lines": len(hits),
            "matches": page, "coverage": cov}


if __name__ == "__main__":
    mcp.run(transport="stdio")
