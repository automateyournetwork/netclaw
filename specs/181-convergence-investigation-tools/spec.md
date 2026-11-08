# Spec 181: Convergence investigation tools

Created 2026-11-08; branch `181-convergence-investigation-tools`, on 1.19.1; status:
implementation and verification.

Convergence (set up by the `convergence-setup` skill) needs two capabilities that
exist only on a fork today. This spec adds them upstream without copying the fork's
extra behaviour.

## Problem

- After `n2n_delegate` or `n2n_route`, an agent calls `n2n_task_status` once, sees
  `working`, and stops. Long delegated work never reaches a result.
- `rag_snapshot` stores each investigation in its own Chroma collection
  (`snapshot_*`, registry `kind='snapshot'`). `rag_search(collection="investigations")`
  treats that name as one literal collection, so prior investigations are never found.

## Requirements

- FR-001: `n2n_task_wait(task_id, timeout_seconds=45, poll_interval_seconds=5.0)`
  polls the same `GET /n2n/tasks/{task_id}` as `n2n_task_status` (keeping the HTTP status) until
  the payload's `state` is terminal or this call's slice ends.
- FR-002: Clamp `timeout_seconds` to 10–50 and `poll_interval_seconds` to 2–15.
  Terminal states are the stored states `completed`, `failed`, `cancelled`,
  `outcome_unknown`, and `interrupted`. `submitted` and `working` are not terminal.
  `unknown` is a missing-task response, not a stored terminal state, and it ends
  the wait at once (FR-003a).
- FR-003: Read `state` only from the payload's `state` field when it is a string.
  Do not infer a terminal state from `status`, free text, or a nested `result`.
  Return the last payload through the existing `_gcf_dumps`. When the slice ends
  first, add `still_running: true` and a hint to call `n2n_task_wait` again with
  the same `task_id`. Do not invent or overwrite `state`. If `_get` raises, return
  `{task_id, state: "error", error}`.
- FR-003a: `n2n_task_wait` reads the HTTP status through its own
  `_get_with_status`; `_get`, `n2n_task_status`, and `n2n_task_result` are
  unchanged. Only an HTTP 404 (the daemon's `{"error": "unknown task"}`) or
  `state: "unknown"` means not found: return at once, without `still_running`,
  with `not_found: true`, a hint not to wait again, and `task_id` filled in when
  absent. Otherwise a coordinator would call `n2n_task_wait` forever on a purged
  task.
- FR-003b: Any other non-2xx (5xx, a scoped broker refusal) and a 2xx body
  without a string `state` return at once as `{task_id, state: "error",
  http_status, error, response?, hint}` with no `not_found`, so the caller can
  call `n2n_task_wait` again. `error` is the body's `error` string when present,
  else `HTTP <status>` or a no-state message.
- FR-004: `rag_search` collection tokens `investigations`, `snapshots`, and `cases`
  (exact after strip, case-sensitive) search every registry row with
  `kind='snapshot'`, `ingest_status='ready'`, and a truthy collection. Dedupe in
  registry order (`ingest_ts DESC`), apply `ingested_after` / `ingested_before`
  to each row's `ingest_ts`, then keep the newest
  `RAG_INVESTIGATION_MAX_COLLECTIONS` (default 50), and pass at most `2k` fused
  candidates per collection to the reranker. The success data adds
  `collections_searched` and `collections_skipped` (matching snapshots left out
  by the cap) as counts; the cap is also logged. With the cross-encoder on, one
  search reranks up to cap × 2k candidates (500 at the defaults with `k=5`).
  When ready snapshots exist but none is in the date range, the empty-corpus
  message says so. With the cross-encoder on, merge by
  its score. In passthrough (`RAG_RERANK_ENABLED=0` or the model unavailable) the
  score is the dense cosine and BM25-only hits score 0.0, so merge on the
  per-collection RRF score instead. RRF is rank-based, so passthrough
  interleaves collections by rank (every top hit scores 2/61 when both legs rank
  it first), not by match strength. Return the caller's top `k`. Each alias hit
  carries the collection that was searched.
- FR-005: `all` and `*` search `documents` plus those snapshot collections. Any
  other value, including `Investigations`, stays a literal collection search with
  today's envelope. There is no `any` alias.
- FR-006: When no ready snapshots are indexed, the snapshot aliases return the
  empty-corpus envelope and the message `No investigation snapshots are indexed.`
  A missing or unreadable snapshot collection is skipped and its exception text
  stays out of the tool response. When every listed snapshot collection is
  unreadable (count or retrieve fails), the snapshot aliases return
  `STORAGE_UNAVAILABLE`, not an empty corpus. A documents-collection failure on
  `all` or `*`, in `count` or in hybrid retrieval, returns `STORAGE_UNAVAILABLE`
  with the existing message and does not raise.
- FR-007: The retrieval log records an alias search as
  `<alias> -> <collections searched>`. `ingested_after` / `ingested_before`
  compare each chunk's `ingest_ts`, for snapshots too, not `capture_ts`; the rag
  skill and README say so.
- FR-008: The n2n-federation skill says to use `n2n_task_wait` when available and
  otherwise poll `n2n_task_status` every 5–15 s, because scoped Hermes operator
  profiles do not list `n2n_task_wait`.

## Out of scope

Hermes operator allowlist and `operator_policy.py` (the qualified subset does not
include every n2n task tool). `config/mcp-task-tools.json` and the frozen spec 141
catalogs. Rewriting `_gcf_dumps`. Version bump and changelog (release repair
PR #337 is open). Running the catalog builders.
