# result-analysis-mcp — complete, bounded, read-only analysis of large results

Spec [187](../../specs/187-large-result-analysis/spec.md), GitHub issue #322. NetClaw-authored,
stdlib plus FastMCP. **No code execution, no SQL, no regex, no device access, no command re-run.**

| | |
|---|---|
| Tools | **7** — `result_status`, `result_list`, `result_describe`, `result_count`, `result_select`, `result_lines`, `result_text_search` |
| Reads | only results a producer retained in `~/.openclaw/results/` (private, `0700`/`0600`) |
| Library | `result_retention.py` (producers import it), `result_stream.py` (bounded stream window) |

## Why

A host can cap how much of a tool result a model sees; issue #322 reports 20,000 characters
for network content in OpenClaw's Tool Search broker. That cap is upstream; NetClaw neither
sets nor can change it, and we have not verified it ourselves (OpenClaw is not in this repo).
We do not ask for it to be removed and we do not bypass it. Instead:

1. A producer that would return more than the inline budget (15,000 chars) **retains the whole
   result** and returns an envelope: `handle`, `inline_complete: false`, size, sha256, a small
   preview, and an explicit statement that the envelope is not the result.
2. The agent asks bounded questions of the handle with the tools above.
3. **Every answer carries a `coverage` block** — see below.

## Coverage block (read it before quoting a number)

`records_total / scanned / matched / returned`, `truncated_page`, `next_offset`, `complete`,
`incomplete_reasons`, `basis` (`complete-retained-copy` | `truncated-retained-copy`),
`retention_truncated`, `producer_notes` (e.g. "Genie-parsed: unmodelled fields absent" — field
filtering is not record truncation), `gaps` (e.g. records with no usable timestamp), `stream`
(drops and reconnect gaps), and traceability: `handle`, `command`, `device`, `retrieved_at`,
`source_sha256`, `source_bytes`.

`complete` is `true` only when the whole retained copy was scanned, the retained copy is itself
untruncated, no stream loss is recorded, no records are unplaceable in a time window, and the
response is not a page. A page (`result_select`, `result_lines`, `result_text_search`) is
`complete: false` until the last page.

## The issue's acceptance case

```
result_count(handle, record_path="output.interface",
             where=[{"field":"_key","op":"startswith","value":"Tunnel"}], group_by=["status"])
```
For a dict-keyed collection the key is the pseudo-field `_key`. Filters are
`(field, op, literal)`; ops: `eq ne startswith endswith contains in gt ge lt le exists
not_exists`. Time windows: `time_field` + `since`/`until` (ISO-8601 or epoch; `until` exclusive).

## Limits (env, all with defaults)

| Variable | Default | Meaning |
|---|---|---|
| `NETCLAW_RESULTS_DIR` | `~/.openclaw/results` | store |
| `NETCLAW_RESULT_INLINE_BUDGET` | 15000 | max chars a producer returns inline |
| `NETCLAW_RESULT_MAX_BYTES` | 32 MiB | per-result retention cap (over it: truncated copy, flagged) |
| `NETCLAW_RESULT_STORE_MAX_BYTES` | 256 MiB | total store; oldest evicted |
| `NETCLAW_RESULT_TTL_SECONDS` | 3600 | handle lifetime; expired handles error explicitly |
| `NETCLAW_RESULT_MAX_SCAN` | 2,000,000 | records scanned per query; over it: `complete: false` |

## Producers

- **multivendor-cli-mcp** (`run_command`, `get_facts`, `run_fleet`) uses it today, after policy,
  filter and credential checks. Small results are byte-identical to before.
- **pyATS_MCP** is cloned from a pinned upstream into the runtime venv and is not tracked in this
  repository, so it is **not** modified here. Integrating it needs an upstream change or a
  wrapper; `result_retention.envelope()` / `bounded_dict()` is the one call it needs.
- **Streams**: `result_stream.StreamBuffer` is a bounded window counting `received`, `dropped`
  and recorded reconnect `gaps`; `snapshot()` retains it so answers report that loss. Wiring a
  live source (syslog-mcp, telemetry) is a follow-up; no live stream has been validated.

## Security notes

Retention stores only what the producer had already filtered and was about to return to the
agent; it adds no new device access. Handles are 128-bit random and strictly format-checked
(no path traversal). Retained files are integrity-checked on load. The audit log
(`audit.jsonl`) records handle, operation and source command, never content. Retained results
may contain whatever the producer returned (including configuration text); the store is private
to the user and short-lived, but treat it like the producer's own output.

## Tests

`tests/result-analysis/` (pytest), declared in `tests/contract-suites.json`.
