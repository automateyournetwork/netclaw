"""The DuckDB sandbox: allowlisted datasets in, nothing out.

Roadmap R17 carries a hard constraint: a SQL surface **must not** expose
`~/.openclaw/memory/` or `~/.openclaw/rag/rag.db`. A generic SQL engine is a backdoor to the
whole filesystem — `read_csv('/etc/passwd')`, `ATTACH '…/rag.db'`, `COPY … TO '/tmp/exfil'`,
`INSTALL httpfs` then read over the network. Blocking those by inspecting query strings is a
losing game: SQL has too many spellings, and the one you miss is the one that matters.

So containment here is enforced **by DuckDB, not by pattern matching**. The sequence is:

1. Materialise each allowlisted dataset into a real TABLE.
2. `SET enable_external_access=false` — every filesystem and network operation now fails.
3. `SET lock_configuration=true` — and that setting can no longer be turned back on.

Measured after step 3 (see specs/092-duckdb-analysis/spec.md, Verification): reading
`/etc/passwd`, globbing `/home/**`, attaching `rag.db`, attaching the memory store,
`COPY … TO`, `INSTALL`/`LOAD`, re-enabling `enable_external_access`, and unlocking the
configuration **all raise**. The materialised tables remain fully queryable.

One thing this forced, and it is worth stating plainly: a **VIEW does not survive the
lockdown.** Views are evaluated lazily, so a view over a CSV re-opens the file at query time
and fails once the door is shut. Datasets must be materialised, which bounds memory by the
data loaded — hence the row cap in `loader.py`. That trade is the price of enforcement that
does not depend on me writing a perfect regex.
"""

from __future__ import annotations

import re
import threading

# Imported lazily so the statement screen -- which is pure `re` and enforces R17's read-only
# rule -- stays importable where duckdb is absent (CI installs nothing, spec 075 SC-013).
# The Sandbox class raises on construction instead, which is the honest place to fail.
try:
    import duckdb
except ModuleNotFoundError:  # pragma: no cover - exercised by the CI path
    duckdb = None

# Statement forms an analyst needs. Anything else is refused before it reaches DuckDB --
# not as the security boundary (that is the lockdown above) but because R17 asks for
# "read-only analyst access, not a general write surface", and a DROP that silently empties
# a loaded table would waste an operator's afternoon for no benefit.
_ALLOWED_LEADS = ("select", "with", "explain", "describe", "show", "summarize", "from", "pivot", "unpivot", "values", "table")

# Refused with a specific message so the caller learns the model rather than guessing.
_REFUSED = (
    (re.compile(r"^\s*(insert|update|delete|drop|create|alter|truncate|replace)\b", re.I),
     "this is a read-only analyst surface; {0} is not available"),
    (re.compile(r"^\s*(attach|detach)\b", re.I),
     "ATTACH is blocked. The NetClaw memory and RAG stores are deliberately unreachable "
     "from this surface, and DuckDB itself refuses it after lockdown"),
    (re.compile(r"^\s*(copy|export)\b", re.I),
     "COPY/EXPORT is blocked: this surface reads, it does not write files"),
    (re.compile(r"^\s*(install|load|force)\b", re.I),
     "extensions cannot be installed or loaded here"),
    (re.compile(r"^\s*set\b", re.I),
     "SET is blocked: the sandbox configuration is locked and cannot be changed"),
    (re.compile(r"^\s*(pragma|call)\b", re.I),
     "PRAGMA/CALL is blocked; use SHOW or DESCRIBE for metadata"),
)


class QueryRefused(RuntimeError):
    """The query was rejected before execution, with a reason the caller can act on."""


class QueryTimeout(RuntimeError):
    """The query exceeded its time budget and was interrupted."""


def screen(sql: str) -> None:
    """Refuse anything that is not a read. Raises QueryRefused with a specific reason."""
    stripped = sql.strip()
    if not stripped:
        raise QueryRefused("empty query")

    # Multiple statements would let a refused form ride along behind an allowed one. Trailing
    # semicolons are fine; a second statement is not.
    body = stripped.rstrip(";")
    if ";" in body:
        raise QueryRefused("one statement per call: a second statement could carry a form "
                           "the first-statement check already refused")

    for pat, msg in _REFUSED:
        m = pat.match(body)
        if m:
            raise QueryRefused(msg.format(m.group(1).upper() if m.groups() else ""))

    lead = re.match(r"\s*(\w+)", body)
    if not lead or lead.group(1).lower() not in _ALLOWED_LEADS:
        raise QueryRefused(
            f"only read statements are accepted here "
            f"({', '.join(s.upper() for s in _ALLOWED_LEADS[:6])}…); got "
            f"'{(lead.group(1) if lead else body[:20])}'")


class Sandbox:
    """A locked-down in-memory DuckDB holding only what was explicitly loaded."""

    def __init__(self) -> None:
        if duckdb is None:
            raise RuntimeError(
                "the duckdb package is not installed; install "
                "mcp-servers/analysis-mcp/requirements.txt")
        self.conn = duckdb.connect(":memory:")
        self._locked = False
        self._lock = threading.Lock()

    def load_sql(self, sql: str) -> None:
        """Materialise a dataset. Only callable BEFORE lockdown, by construction."""
        if self._locked:
            raise RuntimeError("sandbox is locked; datasets must be loaded before lockdown")
        self.conn.execute(sql)

    def lock(self) -> None:
        """Shut the door. Every filesystem and network path becomes unavailable.

        Idempotent, and irreversible for the life of the connection: `lock_configuration`
        prevents `enable_external_access` from being turned back on, which is what makes this
        a boundary rather than a suggestion.
        """
        if self._locked:
            return
        self.conn.execute("SET enable_external_access=false")
        self.conn.execute("SET lock_configuration=true")
        self._locked = True

    @property
    def locked(self) -> bool:
        return self._locked

    def query(self, sql: str, timeout: int, max_rows: int) -> tuple[list[str], list[tuple], bool]:
        """Run a screened read query under a wall-clock budget.

        Returns (column_names, rows, truncated). Raises QueryTimeout if the budget expires --
        DuckDB has no statement timeout, so a watchdog calls `interrupt()`, which was verified
        to actually stop a long-running scan rather than merely being ignored.
        """
        if not self._locked:
            raise RuntimeError("refusing to run a query before lockdown")
        screen(sql)

        with self._lock:  # one query at a time: interrupt() is connection-wide, not per-query
            result: dict = {}

            def run() -> None:
                try:
                    cur = self.conn.execute(sql)
                    result["cols"] = [d[0] for d in (cur.description or [])]
                    # Fetch one extra row to detect truncation honestly rather than guessing.
                    result["rows"] = cur.fetchmany(max_rows + 1)
                except Exception as exc:  # surfaced to the caller verbatim
                    result["error"] = exc

            worker = threading.Thread(target=run, daemon=True)
            worker.start()
            worker.join(timeout)
            if worker.is_alive():
                self.conn.interrupt()
                worker.join(10)
                raise QueryTimeout(
                    f"query exceeded {timeout}s and was interrupted. Narrow it with a WHERE "
                    "clause or an explicit LIMIT.")

            if "error" in result:
                raise result["error"]
            rows = result.get("rows", [])
            truncated = len(rows) > max_rows
            return result.get("cols", []), rows[:max_rows], truncated
