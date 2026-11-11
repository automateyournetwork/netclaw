# Feature Specification: Bounded, coverage-annotated analysis of large diagnostic results

**Feature Branch**: `187-large-result-analysis`
**Created**: 2026-11-11
**Status**: Draft
**Input**: GitHub issue #322 ("Complete Read-Only Analysis of Large Diagnostic Results Without Code Mode") and the follow-up comment broadening scope to routing tables, historical logs/syslog and bounded live-log analysis.

## Background and the honest answer to the issue's question

The reporter observed a 169,859-byte structured `show ip interface brief` result reach the
agent as ~20,000 characters ending in `[truncated]`, and attributes this to OpenClaw's Tool
Search broker (`renderToolSearchControlText`, which caps results treated as network content at
20,000 characters).

What we verified on this branch, and what we did not:

- **Verified**: nothing in NetClaw's own servers (pyATS_MCP, multivendor-cli-mcp,
  analysis-mcp) imposes a 20,000-character cap on tool output; NetClaw servers return whole
  results and could, before this spec, only rely on whatever the host does with them.
  NetClaw has no mechanism for a complete result to be re-read in bounded pieces, and no
  convention for stating whether an answer covered all of the data.
- **Not verified**: the cap itself. OpenClaw is not installed in this environment and its
  `dist/` code is not in this repository, so we cannot confirm the cap's existence, version,
  or whether it is configurable. We take the reporter's quoted code as the working premise.
- **Not answerable from NetClaw**: *why* the boundary exists (security, context budget, or
  other). The quoted code suggests a context/untrusted-content bound, but that is inference. The
  question belongs to OpenClaw maintainers. This spec does not ask for the limit to be removed
  and does not work around it by patching or bypassing it.

NetClaw-side supported solution: keep the host limit intact, and make it irrelevant for
analysis by (1) retaining the **complete** result server-side, (2) returning an inline-safe
envelope plus a **handle**, and (3) offering a read-only, **declarative** (no code execution)
query surface over the handle whose every answer states exactly what it covered.

## Clarifications

### Session 2026-11-11 (resolved autonomously; no human available)

- Q: Where does retention live? -> A: A stdlib library inside the new `result-analysis-mcp`
  directory that producers import; one store (`~/.openclaw/results/`).
- Q: Should handles survive restarts? -> A: Yes on disk, but short-lived (1 h TTL).
- Q: Regex in filters? -> A: No. Literal ops only, to keep "no arbitrary execution" and avoid
  regex CPU abuse.
- Q: Is a page of results "complete"? -> A: No; `complete` is true only on a full scan of an
  untruncated copy with no recorded loss, and a page is false until the last page.
- Q: Which producers now? -> A: multivendor-cli-mcp; pyATS is an untracked upstream (follow-up).
- Q: Streams? -> A: Library + semantics now; live wiring is a follow-up (issue permits).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Count and group records in a result larger than the display limit (Priority: P1)

A support engineer asks the agent to count Tunnel interfaces and their up/down distribution
from `show ip interface brief` on a router whose parsed result is over 170 KB. The agent
receives a small envelope containing a handle, then asks for a grouped count over the retained
result and gets an exact answer stating it scanned every record.

**Why this priority**: it is the issue's acceptance case.

**Independent Test**: retain a synthetic 170 KB+ interface table with a known number of Tunnel
interfaces per status; run the grouped-count query; the numbers equal the known truth and the
coverage block says `complete: true`, `scanned == total`.

**Acceptance Scenarios**:

1. **Given** a retained result of >170 KB with N Tunnel interfaces, **When** the agent counts
   records whose key starts with `Tunnel` grouped by `status`, **Then** the counts are exact and
   coverage reports all records scanned.
2. **Given** a match set larger than the page size, **When** the agent selects records, **Then**
   one bounded page is returned with `truncated_page: true`, the total matched count, and
   next-offset, never presented as the full list.
3. **Given** a query on a handle that does not exist, expired, or is malformed, **Then** the
   answer is an explicit error, never an empty "0 results" that reads as complete.

---

### User Story 2 - Producers return an inline-safe envelope instead of an oversized blob (Priority: P1)

When a pyATS show command's result would exceed the inline budget (default 15,000 chars, safely
below the reported 20,000), the tool retains the full result and returns an envelope: handle,
size, record count, a small preview, and a statement that the inline preview is **not** the
whole result and how to query the rest. Small results are returned unchanged.

**Independent Test**: call the retention helper with small and large payloads; small passes
through byte-identical, large yields an envelope under the inline budget whose handle resolves
to the exact original (sha256 matches).

**Acceptance Scenarios**:

1. **Given** a result under the budget, **Then** output is unchanged (no behaviour change for
   existing small calls).
2. **Given** a result over the budget, **Then** the envelope is under the budget, marks
   `inline_complete: false`, and carries the sha256 of the retained original.
3. **Given** retention fails (disk, size cap), **Then** the envelope says the result is **not**
   retained and the preview is incomplete; the tool does not silently claim completeness and
   does not re-run the device command.

---

### User Story 3 - Honest coverage when retention itself is capped or the source was filtered (Priority: P2)

Retention has its own ceiling (default 32 MiB per result). If a result exceeds it, the retained
copy is explicitly marked `retention_truncated`, and every later answer says its basis is a
truncated copy. If a producer filtered fields (`partial=true`) or capped records, that note is
stored and surfaced so "complete analysis", "field filtering" and "record-list truncation" are
distinguishable.

**Independent Test**: retain an oversized payload with a producer note; every query response
includes `coverage.basis`, `retention_truncated: true` and the producer notes, and `complete` is
never `true`.

### User Story 4 - Traceable, time-windowed and text/log analysis (Priority: P2)

Routing tables, syslog-like JSON records and plain-text CLI output can be queried: filter by
field conditions, restrict to a time window (reporting records with no parseable timestamp as
an explicit gap), search plain text by literal substring with context lines, and page lines.
Every answer cites the handle, source command/device, retrieval time and sha256.

**Independent Test**: a retained record list with some missing/invalid timestamps and a window;
counts include the excluded-for-no-timestamp number; a text result is searchable and pageable
with exact line totals.

### User Story 5 - Bounded stream capture with explicit drops and gaps (Priority: P3)

A bounded in-memory stream buffer accepts events with a maximum size, drops oldest on
overflow, and counts every drop; reconnects record a gap (time and reason). A snapshot of the
buffer can be retained and queried with the drop and gap counters in its coverage. Wiring
specific live sources (e.g. syslog-mcp) is a documented follow-up per the issue's allowance for
a linked follow-up issue.

**Independent Test**: push more events than capacity with a simulated reconnect; snapshot
reports exact `dropped`, `received`, `gaps`, and `complete: false`.

### Edge Cases

- Results that are neither JSON nor text (binary): rejected from retention with a clear reason.
- Handle strings crafted for path traversal: rejected by strict format validation.
- Regex/CPU abuse: no regex in record filters; text search is literal; scan work is bounded.
- Expired handles (default TTL 1 hour) and store-size pressure (default 256 MiB total):
  oldest evicted; querying an evicted handle is an explicit error stating expiry.
- Result with no record collection (scalar JSON): `describe` says so; count falls back to
  top-level item count with that stated.
- Concurrent writers/readers: handles are immutable once written (atomic rename).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST retain a complete producer result server-side under an
  unguessable handle with immutable content, recorded sha256, byte size, producing tool,
  device, command, retrieval time, expiry, and producer notes.
- **FR-002**: Producers MUST return unchanged output for results under the inline budget and an
  envelope (< budget) with handle and explicit `inline_complete: false` otherwise.
- **FR-003**: The query surface MUST be read-only and declarative: describe, count, grouped
  count, select (field projection, filter, offset/limit), line paging, literal text search,
  time-window filtering. It MUST NOT execute code, shell, SQL, or regex, and MUST NOT contact
  devices or re-run commands.
- **FR-004**: Every query response MUST include a coverage block: handle, source facts,
  `records_total`, `records_scanned`, `records_matched`, `records_returned`, `complete`,
  `truncated_page`, `next_offset`, `basis` (`complete-retained-copy` or `truncated-retained-copy`),
  `retention_truncated`, `producer_notes`, and gaps (including records excluded for lacking a
  usable timestamp).
- **FR-005**: An answer MUST NOT be labelled complete when any of: retention was truncated, the
  page was capped, the scan was budget-limited, or the stream dropped events.
- **FR-006**: Invalid, unknown or expired handles MUST yield explicit errors.
- **FR-007**: The store MUST be private (0700 dir, 0600 files), bounded by per-result size,
  total size and TTL, and MUST NOT retain anything the producer did not already return to the
  agent; credentials stay protected because producers retain only their already-filtered
  output. Query activity is audit-logged without result content.
- **FR-008**: A bounded stream buffer MUST count received, dropped and gap events and expose
  them in coverage.
- **FR-009**: Existing producer allowlists, command validation and read-only restrictions MUST
  remain in force and unchanged; retention happens after those checks.
- **FR-010**: Documentation MUST state the honest answer to the issue's question, the limits
  of what NetClaw can and cannot fix, and the configuration/limits of this solution.

### Key Entities

- **Retained result**: immutable stored complete payload plus metadata.
- **Handle**: opaque unguessable identifier for a retained result.
- **Coverage block**: the statement of what an answer scanned and what it omitted.
- **Stream buffer**: bounded event window with drop and gap counters.

## Success Criteria *(mandatory)*

- **SC-001**: Tunnel interface counts and status distribution from a result >170 KB are exact
  (match ground truth in tests) with complete coverage.
- **SC-002**: No response from the new surface is `complete: true` when any listed incompleteness
  condition holds (verified by tests for each condition).
- **SC-003**: Every inline envelope is under 15,000 characters regardless of source size.
- **SC-004**: Zero arbitrary-execution paths: no tool accepts code, SQL, shell or regex.
- **SC-005**: Existing small-result producer behaviour is byte-identical.

## Assumptions (defaults chosen without a human; review these)

- Inline budget 15,000 chars (reporter's cap is 20,000; wrapper overhead was ~300 chars).
- Retention ceiling 32 MiB/result, 256 MiB total, TTL 1 hour; all env-configurable.
- Handles live under `~/.openclaw/results/` (outside memory/RAG/n2n stores).
- Producer integration in this spec: `multivendor-cli-mcp` (`run_command`, `get_facts`,
  `run_fleet`). `pyATS_MCP` is cloned from a pinned upstream into the runtime venv and is NOT
  tracked in this repository (`scripts/setup-pyats-runtime.py`), so it is not modified; it needs
  an upstream change or wrapper and is a documented follow-up (one call: `result_retention.envelope`).
  An early local edit of pyATS was reverted for this reason.
- Stream wiring to live sources (syslog-mcp) is a follow-up issue; this spec ships the bounded
  buffer and coverage semantics only, and says so.
- Log/stream scenarios are **not** live-validated (the issue notes they are untested requested
  coverage); validation here is synthetic-data tests.
- No live router was available; no live-device validation is claimed.
