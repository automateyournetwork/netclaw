---
name: result-analysis
description: "Complete, read-only counting, filtering, paging and text search over a large diagnostic result that a tool returned as a handle envelope (inline_complete false). Use when a result says it is too large to return inline, or when asked to count/group records (e.g. Tunnel interfaces by status), search a long show logging or routing table, or analyse a bounded time window, without ever presenting a partial result as complete"
version: 1.0.0
license: Apache-2.0
tags: [analysis, read-only, large-results, coverage, logs, routing]
---

# Large Result Analysis (read-only, coverage-annotated)

## MCP Server

- **Server**: `result-analysis-mcp` (NetClaw-authored, spec 187, issue #322)
- **Tools**: `result_status`, `result_list`, `result_describe`, `result_count`, `result_select`, `result_lines`, `result_text_search`

## When to use

A device/diagnostic tool returned `"inline_complete": false` with a `handle` (`r_...`). The inline
text is **not** the result. Never count, total or summarise from it.

## Procedure

1. `result_describe(handle)` — shape, record collections, fields, producer notes, retention truncation.
2. `result_count` for totals and distributions (`group_by`), `result_select` for rows (follow
   `coverage.next_offset`), `result_lines`/`result_text_search` for plain text and logs.
   Dict-keyed collections (interface name) expose the key as `_key`.
3. Quote a number as a total **only if `coverage.complete` is true**. Otherwise say what the
   answer covered using `coverage.incomplete_reasons` (page only, retained copy truncated,
   records with no timestamp, stream drops/gaps, scan budget).
4. Cite `coverage.command`, `device`, `retrieved_at` and `source_sha256` so the answer is traceable.

## Never

- Do not re-run the device command because a result was large; query the handle.
- Do not ask for or use Code Mode, raw CLI, or arbitrary execution; filters are
  `(field, op, literal)` only (no regex, SQL or code). This surface cannot reach devices.
- An unknown or expired handle is an error, not "zero results". Say it is no longer retained.
- Field filtering by the producer (`producer_notes`) is not the same as complete data; report it.

## Example

Count Tunnel interfaces by status:
`result_count(handle, record_path="output.interface", where=[{"field":"_key","op":"startswith","value":"Tunnel"}], group_by=["status"])`
