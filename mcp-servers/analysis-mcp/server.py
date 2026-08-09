#!/usr/bin/env python3
"""analysis-mcp — read-only DuckDB analysis over exported network data (roadmap R17).

Ad-hoc SQL over the files NetClaw's own tooling produces: Zeek TSV logs and Suricata
`eve.json` from `nsm-mcp` (spec 091), and generated reports under the workspace output
directory. **Read-only, and sandboxed by DuckDB itself rather than by string matching.**

R17 was explicitly blocked until something produced bulk exports -- surveyed on 2026-08-04
there were *zero* parquet files anywhere and no DuckDB installed, so the roadmap's own note
said building the query layer first "would ship a query engine with nothing to point at."
Spec 091 (R13) produced the data, which is what unblocked this.

The security model, which is the substance of this server:

    load allowlisted datasets as materialised TABLEs
    SET enable_external_access=false      -- all filesystem and network paths close
    SET lock_configuration=true           -- and cannot be reopened

After that DuckDB refuses `read_csv('/etc/passwd')`, `glob('/home/**')`, `ATTACH` of the
memory or RAG stores, `COPY … TO`, `INSTALL`/`LOAD`, and any attempt to re-enable access.
Verified, not assumed -- see specs/092-duckdb-analysis/spec.md, Verification. That is how R17's
"must not expose ~/.openclaw/memory/ or rag.db" is honoured: structurally, not by a regex.
"""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import loader  # noqa: E402
from sandbox import QueryRefused, QueryTimeout, Sandbox  # noqa: E402

mcp = FastMCP("analysis-mcp")

QUERY_TIMEOUT = int(os.environ.get("ANALYSIS_QUERY_TIMEOUT", "30"))
MAX_RESULT_ROWS = int(os.environ.get("ANALYSIS_MAX_RESULT_ROWS", "500"))

_sandbox: Sandbox | None = None
_loaded: list[dict] = []
_notes: list[str] = []


def _envelope(operation: str, **kw) -> dict:
    import datetime
    env = {
        "operation": operation,
        "observed_at": datetime.datetime.now(datetime.timezone.utc)
                               .replace(microsecond=0).isoformat(),
        "source": "analysis-mcp (DuckDB, read-only, sandboxed)",
    }
    env.update({k: v for k, v in kw.items() if v is not None})
    return env


def _ensure() -> Sandbox:
    """Build the sandbox once: discover, materialise, lock. Lockdown is irreversible."""
    global _sandbox, _loaded, _notes
    if _sandbox is not None:
        return _sandbox

    sb = Sandbox()
    datasets, notes = loader.discover()
    loaded: list[dict] = []
    for ds in datasets:
        try:
            sb.load_sql(loader.load_statement(ds))
            entry = dict(ds)
            # Zeek logs carry their real column names in a `#fields` header. Without applying
            # them the table is columnN and an analyst cannot guess that column2 is id.orig_h.
            names = loader.zeek_column_names(ds["path"])
            if names:
                cur = sb.conn.execute(f'SELECT * FROM "{ds["table"]}" LIMIT 0')
                have = [d[0] for d in (cur.description or [])]
                for old, new in zip(have, names):
                    safe = "".join(c if (c.isalnum() or c == "_") else "_" for c in new)
                    sb.load_sql(f'ALTER TABLE "{ds["table"]}" RENAME COLUMN "{old}" TO "{safe}"')
                entry["columns_from_zeek_header"] = True
            rows = sb.conn.execute(f'SELECT count(*) FROM "{ds["table"]}"').fetchone()[0]
            entry["rows"] = rows
            loaded.append(entry)
        except Exception as exc:
            notes.append(f"failed to load {ds['path']}: {type(exc).__name__}: {exc}")

    sb.lock()
    _sandbox, _loaded, _notes = sb, loaded, notes
    return sb


@mcp.tool()
def analysis_status() -> dict:
    """Report what this surface can see, what it deliberately cannot, and why.

    Call this first. An empty dataset list means no exports exist yet — run an NSM analysis
    (`nsm_analyze`) to produce Zeek and Suricata logs, which is what this surface reads.
    """
    sb = _ensure()
    return _envelope(
        "analysis_status",
        data={
            "sandbox_locked": sb.locked,
            "datasets_loaded": len(_loaded),
            "allowed_roots": loader.roots(),
            "never_readable": list(loader.DENIED_SUBSTRINGS),
            "query_timeout_seconds": QUERY_TIMEOUT,
            "max_result_rows": MAX_RESULT_ROWS,
            "max_rows_per_table": loader.MAX_ROWS_PER_TABLE,
            "enforcement": ("DuckDB with enable_external_access=false and "
                            "lock_configuration=true: filesystem and network access are "
                            "closed and cannot be reopened for the life of the process"),
        },
        gaps=(["No datasets loaded. This surface reads exported files; run nsm_analyze to "
               "produce Zeek/Suricata logs, or place exports under an allowed root."]
              if not _loaded else None),
        notes=_notes or None,
    )


@mcp.tool()
def analysis_datasets() -> dict:
    """List the loaded tables with their row counts, source paths and columns.

    Every table here was materialised from a file under an allowlisted root before the
    sandbox locked. Nothing can be added afterwards.
    """
    sb = _ensure()
    out = []
    for ds in _loaded:
        try:
            cur = sb.conn.execute(f'SELECT * FROM "{ds["table"]}" LIMIT 0')
            cols = [d[0] for d in (cur.description or [])]
        except Exception:
            cols = []
        out.append({"table": ds["table"], "rows": ds.get("rows"), "columns": cols,
                    "source": ds["path"], "bytes": ds["bytes"],
                    "columns_from_zeek_header": ds.get("columns_from_zeek_header", False)})
    return _envelope("analysis_datasets", data={"datasets": out, "count": len(out)},
                     notes=_notes or None)


@mcp.tool()
def analysis_query(sql: str, max_rows: int | None = None) -> dict:
    """Run one read-only SQL query against the loaded datasets.

    Accepts SELECT / WITH / DESCRIBE / SHOW / SUMMARIZE / EXPLAIN. Writes, ATTACH, COPY,
    INSTALL, LOAD, SET and PRAGMA are refused with a specific reason — and are independently
    impossible, since the sandbox has no filesystem or network access.

    Results are capped and `truncated` is reported honestly: a capped result is a page, never
    the whole answer, and must not be presented as a total. Use COUNT(*) for totals.
    """
    sb = _ensure()
    if not _loaded:
        return _envelope("analysis_query", query=sql,
                         error="no datasets are loaded; there is nothing to query. "
                               "Run nsm_analyze to produce exports, then retry.")
    cap = max(1, min(max_rows or MAX_RESULT_ROWS, MAX_RESULT_ROWS))
    try:
        cols, rows, truncated = sb.query(sql, QUERY_TIMEOUT, cap)
    except QueryRefused as exc:
        return _envelope("analysis_query", query=sql, error=f"refused: {exc}")
    except QueryTimeout as exc:
        return _envelope("analysis_query", query=sql, error=str(exc))
    except Exception as exc:
        return _envelope("analysis_query", query=sql,
                         error=f"{type(exc).__name__}: {exc}")
    return _envelope(
        "analysis_query", query=sql,
        data={"columns": cols,
              "rows": [list(r) for r in rows],
              "row_count": len(rows),
              "truncated": truncated},
        gaps=([f"Result capped at {cap} rows — this is a page, not the total. "
               "Use COUNT(*) if you need the true count."] if truncated else None),
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
