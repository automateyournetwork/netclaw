# Implementation Plan: Large result analysis (187)

**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

## Summary
Retain complete results server-side; return inline-safe envelopes with handles; answer bounded
declarative read-only queries over handles with a coverage block on every response.

## Technical context
Python 3.10+, stdlib for retention/query/stream, FastMCP 4.0.11 / mcp 2.3.0 pins like sibling
servers. Storage `~/.openclaw/results/` (0700, files 0600, immutable, TTL, size caps). Tests:
pytest suite `tests/result-analysis`, declared in `tests/contract-suites.json`.

## Constitution / repo gates
Principle XVI (spec/plan/tasks/research present); docs/ADDING-AN-MCP.md steps: config
registration, catalog.json + regenerated catalog.sh, install step, README/SOUL counts, skill,
.env.example, server README, `reconcile-mcp.py`.

## Design
- `result_retention.py`: retain/load/purge/envelope/bounded_dict; handle `r_`+128 bit hex.
- `result_query.py`: collection detection, filters, scan, group, coverage, response fitting.
- `result_stream.py`: `StreamBuffer` (capacity, dropped, gaps, snapshot->retain).
- `server.py`: 7 tools.
- `multivendor-cli-mcp/server.py`: `_bounded()` around run_command/get_facts/run_fleet.
- Out of scope: pyATS upstream, live stream sources, OpenClaw cap.

## Tasks
(see tasks.md)
