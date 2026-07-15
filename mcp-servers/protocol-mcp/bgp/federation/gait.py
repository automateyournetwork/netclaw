"""GAIT — Git-based Audit and Immutable Trail for iN2N federation events (057).

Constitution IV requires an immutable git audit trail. The SQLite
`remote_invocation_record` table (feature 056) is queryable but mutable; this
module adds the immutable git record that complements it. Each federation
security event (delegation, enrollment, member removal, quarantine) becomes one
append-only git commit in a dedicated repo at ~/.openclaw/n2n/gait/, separate
from the netclaw source repo.

Wired from audit.py::_gait_ref — the returned commit SHA is stored in the
existing `gait_ref` column so the SQLite row and the git commit cross-reference.

Invariants (FR-012/012a):
  * append-only — never amend/rebase/force; corrections are new commits
  * attributable (actor) + time-ordered (ts + commit order)
  * unbounded — rely on `git gc`; no rotation, so history is never rewritten
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("n2n.gait")

TRAIL_FILE = "federation-events.jsonl"

VALID_EVENTS = ("delegation", "enrollment", "removal", "quarantine")

_repo_ready: dict = {}   # gait_dir(str) -> (ready, detail), cached per process


def default_gait_dir() -> Path:
    """The daemon/Border trail location. Equals <manager base_dir>/gait for a
    live Border (base_dir=~/.openclaw/n2n), so controls and the Auditor agree."""
    return Path(os.path.expanduser(
        os.environ.get("N2N_GAIT_DIR", "~/.openclaw/n2n/gait")))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _git(gait_dir: Path, *args, timeout_s: float = 15.0) -> Tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(gait_dir), *args],
            capture_output=True, text=True, timeout=timeout_s)
        return proc.returncode, (proc.stdout + proc.stderr)
    except FileNotFoundError:
        return -1, "git not found"
    except subprocess.TimeoutExpired:
        return -1, "git timed out"
    except Exception as e:  # pragma: no cover
        return -1, f"git error: {e}"


def ensure_repo(gait_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """git init the GAIT repo if absent and confirm it is writable.
    Returns (ready, detail). Cached per gait_dir once ready."""
    gait_dir = Path(gait_dir) if gait_dir else default_gait_dir()
    key = str(gait_dir)
    if _repo_ready.get(key, (False,))[0]:
        return _repo_ready[key]
    try:
        gait_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _repo_ready[key] = (False, f"cannot create {gait_dir}: {e}")
        return _repo_ready[key]
    if not (gait_dir / ".git").exists():
        rc, out = _git(gait_dir, "init")
        if rc != 0:
            _repo_ready[key] = (False, f"git init failed: {out.strip()[:120]}")
            return _repo_ready[key]
        # Local identity so commits succeed without global git config.
        _git(gait_dir, "config", "user.name", "netclaw-gait")
        _git(gait_dir, "config", "user.email", "gait@netclaw.local")
        trail = gait_dir / TRAIL_FILE
        if not trail.exists():
            trail.write_text("")
            _git(gait_dir, "add", TRAIL_FILE)
            _git(gait_dir, "commit", "-m", "gait: initialize federation audit trail")
    if not os.access(gait_dir, os.W_OK):
        _repo_ready[key] = (False, f"{gait_dir} not writable")
        return _repo_ready[key]
    _repo_ready[key] = (True, "")
    return _repo_ready[key]


def emit(event: str, *, actor: str, subject: str, target: Optional[str] = None,
         channel_kind: str = "in2n", sqlite_row_id: Optional[int] = None,
         gait_dir: Optional[Path] = None) -> Optional[str]:
    """Append one federation event to the trail and commit it immutably.
    Returns the commit SHA, or None on failure (best-effort — the SQLite row
    stays authoritative; production drives posture degraded if this returns None)."""
    gait_dir = Path(gait_dir) if gait_dir else default_gait_dir()
    if event not in VALID_EVENTS:
        logger.warning("gait.emit: unknown event %r (recording anyway)", event)
    ready, detail = ensure_repo(gait_dir)
    if not ready:
        logger.warning("gait.emit skipped — trail not ready: %s", detail)
        return None
    record = {
        "event": event, "actor": actor, "subject": subject, "target": target,
        "channel_kind": channel_kind, "sqlite_row_id": sqlite_row_id, "ts": _now(),
    }
    try:
        trail = gait_dir / TRAIL_FILE
        with trail.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
        rc, out = _git(gait_dir, "add", TRAIL_FILE)
        if rc != 0:
            logger.warning("gait.emit git add failed: %s", out.strip()[:120])
            return None
        msg = f"gait: {event} {subject} by {actor} @ {record['ts']}"
        rc, out = _git(gait_dir, "commit", "-m", msg)
        if rc != 0:
            logger.warning("gait.emit git commit failed: %s", out.strip()[:120])
            return None
        rc, sha = _git(gait_dir, "rev-parse", "HEAD")
        return sha.strip() if rc == 0 else None
    except Exception as e:  # pragma: no cover
        logger.warning("gait.emit error: %s", e)
        return None


def recent(limit: int = 50, gait_dir: Optional[Path] = None) -> list:
    """Read-only: last N events from the trail (newest first) for review/HUD."""
    gait_dir = Path(gait_dir) if gait_dir else default_gait_dir()
    ready, _ = ensure_repo(gait_dir)
    if not ready:
        return []
    trail = gait_dir / TRAIL_FILE
    if not trail.exists():
        return []
    out = []
    try:
        for line in trail.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except Exception:
        return []
    return list(reversed(out))[:limit]
