"""Declarative, read-only queries over a retained result (spec 187).

No code, SQL, shell or regex is accepted anywhere: filters are (field, op, literal value)
triples, text search is a literal substring. Work per query is bounded by NETCLAW_RESULT_MAX_SCAN.
Every function returns data plus the counts needed to build an honest coverage block.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any

OPS = {"eq", "ne", "startswith", "endswith", "contains", "in", "gt", "ge", "lt", "le",
       "exists", "not_exists"}
MAX_DEPTH = 4
MAX_GROUPS = 1000
MAX_PAGE = 500
MAX_RESPONSE_CHARS = 15000


class QueryError(Exception):
    pass


def max_scan() -> int:
    try:
        return int(os.environ.get("NETCLAW_RESULT_MAX_SCAN", 2_000_000))
    except ValueError:
        return 2_000_000


# ---- locating records -------------------------------------------------------------------

def find_collections(payload: Any) -> list[dict]:
    """Candidate record collections (largest first): dotted path, shape, count."""
    out: list[dict] = []

    def walk(node: Any, path: str, depth: int) -> None:
        if isinstance(node, list) and node:
            out.append({"path": path, "shape": "list", "count": len(node)})
            return
        if isinstance(node, dict) and node:
            if len(node) >= 2 and sum(isinstance(v, dict) for v in node.values()) >= 0.8 * len(node):
                out.append({"path": path, "shape": "dict", "count": len(node)})
            if depth < MAX_DEPTH:
                for k, v in node.items():
                    if isinstance(v, (dict, list)):
                        walk(v, f"{path}.{k}" if path else str(k), depth + 1)

    walk(payload, "", 0)
    # dedupe: a dict candidate's children are often reported too; keep all, sort by count
    return sorted(out, key=lambda c: -c["count"])


def _split(path: str) -> list[str]:
    return [p for p in path.split(".") if p] if path else []


def resolve_parent(root: Any, path: str) -> tuple[Any, Any]:
    parts = _split(path)
    if not parts:
        return None, None
    node = root
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    return node, (int(parts[-1]) if isinstance(node, list) else parts[-1])


def _resolve(root: Any, path: str) -> Any:
    node = root
    for p in _split(path):
        if isinstance(node, dict) and p in node:
            node = node[p]
        elif isinstance(node, list) and p.isdigit() and int(p) < len(node):
            node = node[int(p)]
        else:
            raise QueryError(f"record_path '{path}' not found in the retained result")
    return node


def get_records(payload: Any, record_path: str | None) -> list:
    """Records as a list. A dict collection yields its values with the key as `_key`."""
    if isinstance(payload, str):
        raise QueryError("this retained result is plain text; use result_lines or "
                         "result_text_search")
    if record_path is None:
        cands = find_collections(payload)
        if not cands:
            return [payload] if isinstance(payload, dict) else []
        record_path = cands[0]["path"]
    node = _resolve(payload, record_path)
    if isinstance(node, list):
        return [x if isinstance(x, dict) else {"_value": x} for x in node]
    if isinstance(node, dict):
        return [({"_key": k, **v} if isinstance(v, dict) else {"_key": k, "_value": v})
                for k, v in node.items()]
    raise QueryError(f"record_path '{record_path}' is not a list or object")


def chosen_path(payload: Any, record_path: str | None) -> str | None:
    if record_path is not None:
        return record_path
    c = find_collections(payload) if not isinstance(payload, str) else []
    return c[0]["path"] if c else None


# ---- filters ----------------------------------------------------------------------------

def _field(rec: Any, name: str) -> tuple[bool, Any]:
    node = rec
    for p in name.split("."):
        if isinstance(node, dict) and p in node:
            node = node[p]
        else:
            return False, None
    return True, node


def _num(x: Any) -> float | None:
    if isinstance(x, bool):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def validate_where(where: list[dict] | None) -> list[dict]:
    out = []
    for c in where or []:
        if not isinstance(c, dict) or "field" not in c or "op" not in c:
            raise QueryError("each condition needs 'field' and 'op' (and 'value' for most ops)")
        if c["op"] not in OPS:
            raise QueryError(f"unsupported op '{c['op']}'; allowed: {sorted(OPS)} "
                             "(no regex, code or SQL is accepted)")
        if c["op"] not in ("exists", "not_exists") and "value" not in c:
            raise QueryError(f"op '{c['op']}' needs a 'value'")
        out.append(c)
    return out


def match(rec: dict, where: list[dict], ci: bool = False) -> bool:
    for c in where:
        present, val = _field(rec, c["field"])
        op = c["op"]
        if op == "exists":
            if not present:
                return False
            continue
        if op == "not_exists":
            if present:
                return False
            continue
        if not present:
            return False
        want = c["value"]
        if op == "in":
            pool = want if isinstance(want, list) else [want]
            if ci:
                ok = str(val).lower() in {str(x).lower() for x in pool}
            else:
                ok = val in pool or str(val) in {str(x) for x in pool}
        elif op in ("gt", "ge", "lt", "le"):
            a, b = _num(val), _num(want)
            if a is None or b is None:
                return False
            ok = {"gt": a > b, "ge": a >= b, "lt": a < b, "le": a <= b}[op]
        else:
            a, b = str(val), str(want)
            if ci:
                a, b = a.lower(), b.lower()
            ok = {"eq": a == b, "ne": a != b, "startswith": a.startswith(b),
                  "endswith": a.endswith(b), "contains": b in a}[op]
        if not ok:
            return False
    return True


def parse_ts(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return x / 1000.0 if x > 1e11 else x
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            d = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            n = _num(s)
            return parse_ts(n) if n is not None else None
        if d.tzinfo is None:
            d = d.replace(tzinfo=_dt.timezone.utc)
        return d.timestamp()
    return None


# ---- scan ---------------------------------------------------------------------------------

def scan(records: list, where: list[dict] | None, *, ci: bool = False,
         time_field: str | None = None, since: str | None = None,
         until: str | None = None) -> dict:
    """Single bounded pass. Returns matched records plus the accounting for coverage."""
    where = validate_where(where)
    lo = parse_ts(since) if since else None
    hi = parse_ts(until) if until else None
    if (since and lo is None) or (until and hi is None):
        raise QueryError("since/until must be ISO-8601 or epoch seconds/milliseconds")
    if (since or until) and not time_field:
        raise QueryError("since/until require time_field")
    cap = max_scan()
    scanned = no_ts = 0
    matched: list = []
    for rec in records:
        if scanned >= cap:
            break
        scanned += 1
        if time_field:
            ok, raw = _field(rec, time_field)
            ts = parse_ts(raw) if ok else None
            if ts is None:
                no_ts += 1
                continue
            if (lo is not None and ts < lo) or (hi is not None and ts >= hi):
                continue
        if match(rec, where, ci):
            matched.append(rec)
    return {"matched": matched, "scanned": scanned, "total": len(records),
            "no_timestamp": no_ts, "scan_budget_hit": scanned < len(records)}


def group_count(matched: list, group_by: list[str]) -> tuple[list[dict], bool]:
    counts: dict[tuple, int] = {}
    overflow = False
    for rec in matched:
        key = []
        for f in group_by:
            ok, v = _field(rec, f)
            key.append(v if ok else "<missing>")
        k = tuple(json.dumps(x, sort_keys=True, default=str) for x in key)
        if k not in counts and len(counts) >= MAX_GROUPS:
            overflow = True
            continue
        counts[k] = counts.get(k, 0) + 1
    rows = []
    for k, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        rows.append({**{f: json.loads(x) for f, x in zip(group_by, k)}, "count": n})
    return rows, overflow


# ---- coverage ---------------------------------------------------------------------------

def coverage(meta: dict, *, total: int | None, scanned: int | None, matched: int | None,
             returned: int | None = None, truncated_page: bool = False,
             next_offset: int | None = None, extra_reasons: list[str] | None = None,
             gaps: list[str] | None = None, record_path: str | None = None) -> dict:
    reasons = list(extra_reasons or [])
    if meta.get("retention_truncated"):
        reasons.append("retained copy is truncated: " + json.dumps(meta.get("retention_truncation")))
    if truncated_page:
        reasons.append("response is one page of the matches, not all of them")
    if total is not None and scanned is not None and scanned < total:
        reasons.append(f"scan budget reached after {scanned} of {total} records")
    st = meta.get("stream")
    if st:
        if st.get("dropped"):
            reasons.append(f"stream dropped {st['dropped']} events before this window")
        if st.get("gaps"):
            reasons.append(f"stream has {len(st['gaps'])} recorded gap(s) (reconnects)")
    cov = {
        "handle": meta["handle"], "tool": meta.get("tool"), "device": meta.get("device"),
        "command": meta.get("command"), "retrieved_at": meta.get("retrieved_at"),
        "source_sha256": meta.get("source_sha256"), "source_bytes": meta.get("source_bytes"),
        "record_path": record_path,
        "records_total": total, "records_scanned": scanned, "records_matched": matched,
        "records_returned": returned, "truncated_page": truncated_page,
        "next_offset": next_offset,
        "retention_truncated": bool(meta.get("retention_truncated")),
        "basis": "truncated-retained-copy" if meta.get("retention_truncated")
                 else "complete-retained-copy",
        "producer_notes": meta.get("producer_notes") or [],
        "stream": st,
        "gaps": list(gaps or []),
        "complete": not reasons and not gaps,
        "incomplete_reasons": reasons + list(gaps or []),
    }
    return cov


def fit_rows(build, rows: list, budget: int = MAX_RESPONSE_CHARS) -> tuple[list, bool]:
    """Trim rows from the end until build(rows) serialises within the response budget."""
    trimmed = False
    while rows and len(json.dumps(build(rows), default=str)) > budget:
        rows = rows[: max(len(rows) // 2, 0) if len(rows) > 1 else 0]
        trimmed = True
    return rows, trimmed


def project(rec: dict, fields: list[str] | None) -> dict:
    if not fields:
        return rec
    out = {}
    for f in fields:
        ok, v = _field(rec, f)
        out[f] = v if ok else None
    return out
