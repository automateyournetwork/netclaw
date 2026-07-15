# Contract: GAIT Federation Event Emit

`gait.py` commits an immutable git record per federation security event, complementing (never replacing) the SQLite audit row. Wired via `audit.py::_gait_ref`.

## Python (`gait.py`)

```python
GAIT_DIR = Path("~/.openclaw/n2n/gait").expanduser()

def ensure_repo() -> bool:
    """git init GAIT_DIR if absent; return True if the repo is ready/writable."""

def emit(event: str, *, actor: str, subject: str, target: str|None,
         channel_kind: str, sqlite_row_id: int|None) -> str|None:
    """Append the event JSON to the trail file and `git commit` it.
    event ∈ {delegation, enrollment, removal, quarantine}.
    Return the commit SHA (stored in remote_invocation_record.gait_ref), or None
    on failure (best-effort — the SQLite row stays authoritative)."""

def recent(limit: int = 50) -> list[dict]:
    """Read-only: last N events from the trail for review/HUD."""
```

## Committed record (one JSON object per commit)

```json
{"event":"delegation","actor":"johns-risk/border","subject":"risk/cml",
 "target":"cml-lab-lifecycle#req-abc","channel_kind":"in2n",
 "sqlite_row_id":142,"ts":"2026-07-13T14:20:00Z"}
```

Commit message: `gait: <event> <subject> by <actor> @ <ts>`.

## `audit.py` integration

`_gait_ref(...)` (today returns `None`) becomes:
```python
def _gait_ref(self, peer_identity, decision, *, event, actor, target, channel_kind, row_id):
    return gait.emit(event, actor=actor, subject=peer_identity, target=target,
                     channel_kind=channel_kind, sqlite_row_id=row_id)
```
The SHA is written to the existing `gait_ref` column (already present in the schema). In production, if `ensure_repo()`/`emit()` fails, posture reports `degraded(audit)` (FR-011) but the delegation still runs and is tagged `audit-degraded` (FR-019).

## Invariants

- Append-only; **never** amend/rebase/force (Constitution IV, FR-012).
- Attributable (`actor`) + time-ordered (`ts` + commit order), FR-012.
- Unbounded; `git gc` only, no rotation (FR-012a).
- Separate repo from netclaw source.

## Acceptance mapping

- FR-010/011/012/012a, SC-004: each delegation/enrollment/removal/quarantine in production produces both a commit and a SQLite row; trail is immutable and unbounded.
