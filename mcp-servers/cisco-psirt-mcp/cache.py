"""On-disk advisory cache.

Spec 078 FR-012, FR-012a, FR-012b, FR-012c. Research R6.

One JSON file per key under `~/.openclaw/cisco-psirt/`. No database and no
locking, because the access pattern is read-mostly with a single writer per key,
and a key/value store with no queries does not justify SQLite. `rag.db` is
explicitly off limits (spec 062 FR-030).

`fetched_at` lives *inside* each file so age is inspectable without a separate
index — which matters because cache age is itself the question during an incident.

**Never stores a token or credential.** Advisories are public data; the Bearer
token is not, and it stays in memory (see `auth.py`).
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

DEFAULT_TTL_S = 21600  # 6h — comfortably fresh against Cisco's bundled-Wednesday cadence


def cache_dir() -> Path:
    raw = os.environ.get("CISCO_PSIRT_CACHE_DIR")
    return Path(raw).expanduser() if raw else Path.home() / ".openclaw" / "cisco-psirt"


def ttl_seconds() -> int:
    raw = os.environ.get("CISCO_PSIRT_CACHE_TTL_S")
    if not raw:
        return DEFAULT_TTL_S
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_TTL_S
    # A zero or negative TTL would mean "never cache", which silently re-exhausts
    # the 30/min budget. Treat it as the default rather than honouring it.
    return value if value > 0 else DEFAULT_TTL_S


_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_DOT_RUN = re.compile(r"\.{2,}")


def key_to_filename(*parts: str) -> str:
    """Build a filesystem-safe cache filename from key parts.

    Version strings and CVE ids are caller-supplied, so anything that could escape the
    cache directory is replaced rather than trusted. Runs of dots are collapsed too:
    stripping separators alone already prevents traversal, but leaving `..` sequences in
    a filename invites the question, and a part consisting only of dots would otherwise
    produce a name the filesystem treats specially.
    """
    slug = "-".join(_DOT_RUN.sub("_", _UNSAFE.sub("_", str(p or ""))) for p in parts)
    return f"{slug}.json"


class AdvisoryCache:
    def __init__(self, directory: Path | None = None, ttl: int | None = None):
        self.directory = directory or cache_dir()
        self._ttl = ttl

    @property
    def ttl(self) -> int:
        return self._ttl if self._ttl is not None else ttl_seconds()

    def _path(self, *parts: str) -> Path:
        return self.directory / key_to_filename(*parts)

    def get(self, *parts: str) -> tuple[list | None, int | None]:
        """Return (payload, age_seconds) on a fresh hit, else (None, None).

        A corrupt or unreadable entry is treated as a miss, not an error — a bad
        cache file must never be able to fail a lookup that a live call could
        answer.
        """
        path = self._path(*parts)
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return None, None
        fetched_at = data.get("fetched_at")
        if not isinstance(fetched_at, (int, float)):
            return None, None
        age = int(time.time() - fetched_at)
        if age > self.ttl or age < 0:
            return None, None
        payload = data.get("payload")
        if not isinstance(payload, list):
            return None, None
        return payload, age

    def put(self, payload: list, api_path: str, *parts: str) -> None:
        """Write an entry. A cache write failure is never fatal to the lookup."""
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self._path(*parts)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(
                {"fetched_at": time.time(), "api_path": api_path, "payload": payload},
                indent=2))
            tmp.replace(path)  # atomic, so a reader never sees a half-written file
        except OSError:
            pass

    def stats(self) -> dict:
        """Non-secret cache posture for psirt_status."""
        entries, oldest = 0, None
        try:
            for path in self.directory.glob("*.json"):
                entries += 1
                try:
                    fetched = json.loads(path.read_text()).get("fetched_at")
                except (OSError, ValueError):
                    continue
                if isinstance(fetched, (int, float)):
                    age = int(time.time() - fetched)
                    oldest = age if oldest is None else max(oldest, age)
        except OSError:
            pass
        return {"entries": entries, "oldest_age_seconds": oldest,
                "directory": str(self.directory), "ttl_seconds": self.ttl}
