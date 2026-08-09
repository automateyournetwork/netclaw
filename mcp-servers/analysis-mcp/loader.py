"""Dataset discovery: which files this surface may load, and which it must never touch.

R17's constraint is a **denylist in the roadmap** ("must not expose `~/.openclaw/memory/` or
`~/.openclaw/rag/rag.db`"), but a denylist is the wrong shape to implement. New stores appear
— feature 033 added the memory store, 062 added RAG, 052 added `federation.db` — and a
denylist silently fails open for whatever arrives next.

So this is an **allowlist of roots**, and the denied paths are additionally checked so that a
misconfiguration cannot quietly re-admit them. Two mechanisms rather than one, because the
consequence of getting it wrong is a backdoor onto the operator's own memory.
"""

from __future__ import annotations

import os

# Roots an analyst may read. Each holds *exported network data* -- the thing R17 was waiting
# for and R13 finally produced.
DEFAULT_ROOTS = [
    # Zeek TSV and Suricata eve.json from nsm-mcp (spec 091). The reason R17 was unblocked.
    os.path.join(os.path.expanduser("~"), ".openclaw", "nsm", "runs"),
    # Generated documents and diagram/report exports (specs 046, 082).
    os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "output"),
    # An explicitly-named scratch area for an operator's own exports.
    os.path.join(os.path.expanduser("~"), ".openclaw", "analysis"),
]

# Never readable, whatever the roots say. These are NetClaw's own cognition, not network data:
# a generic SQL surface over either would be a backdoor, which is the wider constraint R17
# imposes on spec 062's isolation principle.
DENIED_SUBSTRINGS = (
    os.path.join(".openclaw", "memory"),
    os.path.join(".openclaw", "rag"),
    os.path.join(".openclaw", "n2n"),      # federation.db: consent records and pinned keys
    os.path.join(".openclaw", "gait"),     # the immutable audit trail (Principle IV)
    ".ssh", ".aws", ".kube", ".env",
)

# Extensions DuckDB can read natively without an extension install (which is blocked).
READABLE = {
    ".csv": "read_csv",
    ".tsv": "read_csv",
    ".log": "read_csv",       # Zeek writes TSV with a .log suffix
    ".json": "read_json",
    ".jsonl": "read_json",
    ".ndjson": "read_json",
    ".parquet": "read_parquet",
}

# Materialisation bounds memory (a VIEW cannot survive the lockdown -- see sandbox.py), so
# both a per-file size cap and a per-table row cap exist. Overridable, deliberately visible.
MAX_FILE_BYTES = int(os.environ.get("ANALYSIS_MAX_FILE_BYTES", str(256 * 1024 * 1024)))
MAX_ROWS_PER_TABLE = int(os.environ.get("ANALYSIS_MAX_ROWS", "2000000"))


def roots() -> list[str]:
    extra = os.environ.get("ANALYSIS_EXTRA_ROOTS", "")
    out = list(DEFAULT_ROOTS)
    for p in extra.split(os.pathsep):
        p = p.strip()
        if p:
            out.append(os.path.abspath(os.path.expanduser(p)))
    return out


def denied(path: str) -> str | None:
    """The reason this path is off limits, or None."""
    norm = os.path.abspath(os.path.expanduser(path))
    for frag in DENIED_SUBSTRINGS:
        if frag in norm:
            return (f"refused: {frag} is never readable from this surface. NetClaw's memory, "
                    "RAG, federation and audit stores are deliberately unreachable — a SQL "
                    "surface over them would be a backdoor, not an analysis tool.")
    return None


def within_roots(path: str) -> bool:
    norm = os.path.abspath(path)
    for r in roots():
        r = os.path.abspath(r)
        if norm == r or norm.startswith(r + os.sep):
            return True
    return False


def table_name(root: str, path: str) -> str:
    """A stable, SQL-safe identifier derived from the path relative to its root."""
    rel = os.path.relpath(path, root)
    base = os.path.splitext(rel)[0]
    name = "".join(ch if ch.isalnum() else "_" for ch in base).strip("_").lower()
    while "__" in name:
        name = name.replace("__", "_")
    return name or "dataset"


def discover() -> tuple[list[dict], list[str]]:
    """Find loadable datasets under the allowlisted roots. Returns (datasets, notes)."""
    found: list[dict] = []
    notes: list[str] = []
    seen: set[str] = set()

    for root in roots():
        if not os.path.isdir(root):
            notes.append(f"root not present (nothing to load): {root}")
            continue
        if denied(root):
            notes.append(denied(root))
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune denied directories rather than filtering files afterwards, so a symlinked
            # store cannot be walked into at all.
            dirnames[:] = [d for d in dirnames if not denied(os.path.join(dirpath, d))]
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext not in READABLE:
                    continue
                if denied(full) or not within_roots(os.path.realpath(full)):
                    # realpath check: a symlink inside an allowed root pointing at the memory
                    # store must not be readable just because its link lives somewhere legal.
                    notes.append(f"skipped (outside allowed roots or denied): {full}")
                    continue
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size == 0:
                    notes.append(f"skipped (empty, would look like a dataset with no rows): {full}")
                    continue
                if size > MAX_FILE_BYTES:
                    notes.append(f"skipped ({size // 1048576} MB exceeds the "
                                 f"{MAX_FILE_BYTES // 1048576} MB cap): {full}")
                    continue
                name = table_name(root, full)
                if name in seen:
                    name = f"{name}_{len(seen)}"
                seen.add(name)
                found.append({"table": name, "path": full, "bytes": size,
                              "reader": READABLE[ext], "root": root})
    return found, notes


def load_statement(ds: dict) -> str:
    """The CREATE TABLE that materialises one dataset.

    A TABLE, never a VIEW: a view is lazily evaluated and would break the moment the sandbox
    locks the filesystem. Zeek logs are TSV with `#`-prefixed header blocks, so they need
    explicit options rather than sniffing.
    """
    path = ds["path"].replace("'", "''")
    if ds["reader"] == "read_csv":
        is_zeek = ds["path"].endswith(".log")
        opts = ("delim='\\t', header=false, comment='#', ignore_errors=true, "
                "all_varchar=true" if is_zeek else
                "ignore_errors=true, all_varchar=true")
        src = f"read_csv('{path}', {opts})"
    elif ds["reader"] == "read_json":
        src = f"read_json('{path}', ignore_errors=true, format='auto')"
    else:
        src = f"read_parquet('{path}')"
    return (f'CREATE TABLE "{ds["table"]}" AS '
            f"SELECT * FROM {src} LIMIT {MAX_ROWS_PER_TABLE}")


def zeek_column_names(path: str) -> list[str] | None:
    """Zeek's real column names, from its `#fields` header.

    Without this a Zeek log loads as column0..columnN, which is technically queryable and
    practically useless -- an analyst cannot guess that column2 is `id.orig_h`. Returns None
    for a file with no Zeek header.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("#fields"):
                    return line.rstrip("\n").split("\t")[1:]
                if not line.startswith("#"):
                    return None
    except OSError:
        return None
    return None
