"""Server-side retention of complete diagnostic results (spec 187, issue #322).

A host (OpenClaw) may cap how much of a tool result a model sees. NetClaw cannot change that,
so producers retain the COMPLETE result here, return a small envelope with a handle, and the
read-only query surface (query.py / server.py) answers from the retained copy with explicit
coverage metadata. Stdlib only. Nothing here talks to a device or runs code.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

import result_query as query

HANDLE_RE = re.compile(r"^r_[0-9a-f]{32}$")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def store_dir() -> Path:
    base = os.environ.get("NETCLAW_RESULTS_DIR") or os.path.join(
        os.path.expanduser("~"), ".openclaw", "results")
    return Path(base)


def inline_budget() -> int:
    return _env_int("NETCLAW_RESULT_INLINE_BUDGET", 15000)


def max_result_bytes() -> int:
    return _env_int("NETCLAW_RESULT_MAX_BYTES", 32 * 1024 * 1024)


def max_store_bytes() -> int:
    return _env_int("NETCLAW_RESULT_STORE_MAX_BYTES", 256 * 1024 * 1024)


def ttl_seconds() -> int:
    return _env_int("NETCLAW_RESULT_TTL_SECONDS", 3600)


class RetentionError(Exception):
    """Retention could not be completed; the caller must not claim completeness."""


class HandleError(Exception):
    """Unknown, malformed or expired handle."""


def _ensure_dir() -> Path:
    d = store_dir()
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def _canon(payload: Any) -> str:
    return payload if isinstance(payload, str) else json.dumps(
        payload, separators=(",", ":"), sort_keys=True, default=str)


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


def _fit(payload: Any, limit: int) -> tuple[Any, dict | None]:
    """Return (payload_that_fits, truncation_info|None). Never returns invalid JSON."""
    raw = _canon(payload)
    if len(raw.encode("utf-8", "replace")) <= limit:
        return payload, None
    if isinstance(payload, str):
        cut = raw.encode("utf-8", "replace")[:limit].decode("utf-8", "ignore")
        nl = cut.rfind("\n")
        cut = cut[:nl] if nl > 0 else cut
        return cut, {"kind": "text", "lines_total": raw.count("\n") + 1,
                     "lines_kept": cut.count("\n") + 1}
    # structured: trim the largest record collection until the whole payload fits
    cands = query.find_collections(payload)
    if not cands:
        raise RetentionError("result exceeds retention limit and has no record collection to trim")
    path = cands[0]["path"]
    import copy
    work = copy.deepcopy(payload)
    parent, key = query.resolve_parent(work, path)
    coll = parent[key] if parent is not None else work
    total = len(coll)
    keep = total
    while keep > 0:
        keep = keep // 2
        if isinstance(coll, list):
            new = coll[:keep]
        else:
            new = dict(list(coll.items())[:keep])
        if parent is not None:
            parent[key] = new
        else:
            work = new
        if len(_canon(work).encode("utf-8", "replace")) <= limit:
            break
    return work, {"kind": "records", "record_path": path, "records_total": total,
                  "records_kept": keep}


def _audit(op: str, **kw: Any) -> None:
    try:
        d = _ensure_dir()
        f = d / "audit.jsonl"
        if f.exists() and f.stat().st_size > 5 * 1024 * 1024:
            f.replace(d / "audit.jsonl.1")
        rec = {"ts": int(time.time()), "op": op, **kw}
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    except OSError:
        pass


def purge() -> int:
    """Drop expired handles, then evict oldest while the store exceeds its size cap."""
    d = _ensure_dir()
    now = time.time()
    removed = 0
    files = []
    for p in d.glob("r_*.json"):
        try:
            meta = json.loads(p.read_text()).get("meta", {})
            if meta.get("expires_at", 0) <= now:
                p.unlink(missing_ok=True)
                removed += 1
                continue
            files.append((p.stat().st_mtime, p.stat().st_size, p))
        except (OSError, ValueError):
            p.unlink(missing_ok=True)
            removed += 1
    total = sum(s for _, s, _ in files)
    for _, size, p in sorted(files):
        if total <= max_store_bytes():
            break
        p.unlink(missing_ok=True)
        total -= size
        removed += 1
    return removed


def retain(payload: Any, *, tool: str, device: str | None = None, command: str | None = None,
           notes: list[str] | None = None, stream: dict | None = None) -> dict:
    """Store `payload` immutably; returns its metadata (including the handle)."""
    if isinstance(payload, (bytes, bytearray)):
        raise RetentionError("binary results are not retained")
    d = _ensure_dir()
    purge()
    source = _canon(payload)
    stored, trunc = _fit(payload, max_result_bytes())
    stored_canon = _canon(stored)
    now = time.time()
    handle = "r_" + secrets.token_hex(16)
    meta = {
        "handle": handle, "tool": tool, "device": device, "command": command,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "expires_at": now + ttl_seconds(),
        "kind": "text" if isinstance(stored, str) else "json",
        "source_bytes": len(source.encode("utf-8", "replace")),
        "source_sha256": _sha(source),
        "retained_bytes": len(stored_canon.encode("utf-8", "replace")),
        "retained_sha256": _sha(stored_canon),
        "retention_truncated": trunc is not None,
        "retention_truncation": trunc,
        "producer_notes": list(notes or []),
        "stream": stream,
    }
    tmp = d / f".{handle}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump({"meta": meta, "payload": stored}, fh, default=str)
    os.replace(tmp, d / f"{handle}.json")
    _audit("retain", handle=handle, tool=tool, device=device, command=command,
           source_bytes=meta["source_bytes"], retention_truncated=meta["retention_truncated"])
    return meta


def load(handle: str) -> tuple[dict, Any]:
    if not isinstance(handle, str) or not HANDLE_RE.match(handle):
        raise HandleError("malformed handle (expected r_ + 32 hex chars)")
    p = store_dir() / f"{handle}.json"
    if not p.is_file():
        raise HandleError("unknown handle (never existed, expired, or evicted); "
                          "the result is no longer retained and no answer can be given from it")
    try:
        doc = json.loads(p.read_text())
    except (OSError, ValueError) as exc:
        raise HandleError(f"retained result unreadable: {exc}")
    meta = doc["meta"]
    if meta.get("expires_at", 0) <= time.time():
        p.unlink(missing_ok=True)
        raise HandleError("handle expired; the result is no longer retained")
    if _sha(_canon(doc["payload"])) != meta["retained_sha256"]:
        raise HandleError("retained result failed its integrity check")
    return meta, doc["payload"]


def list_handles() -> list[dict]:
    d = _ensure_dir()
    out = []
    now = time.time()
    for p in sorted(d.glob("r_*.json")):
        try:
            m = json.loads(p.read_text())["meta"]
        except (OSError, ValueError, KeyError):
            continue
        if m.get("expires_at", 0) > now:
            out.append({k: m.get(k) for k in (
                "handle", "tool", "device", "command", "retrieved_at", "source_bytes",
                "retention_truncated", "source_sha256")})
    return out


def _preview(payload: Any, room: int) -> dict:
    cands = query.find_collections(payload) if not isinstance(payload, str) else []
    if isinstance(payload, str):
        lines = payload.splitlines()
        head = "\n".join(lines[:20])
        return {"kind": "text", "lines_total": len(lines), "head": head[:max(room, 200)]}
    info: dict = {"kind": "json", "record_collections": cands[:3]}
    if cands:
        recs = query.get_records(payload, cands[0]["path"])
        info["sample_records"] = recs[:2]
        info["fields_seen"] = sorted({k for r in recs[:200] if isinstance(r, dict) for k in r})[:40]
    return info


def envelope(payload: Any, rendered: str, *, tool: str, device: str | None = None,
             command: str | None = None, notes: list[str] | None = None) -> str:
    """Return `rendered` unchanged if within the inline budget; otherwise retain `payload`
    and return a bounded envelope. Never claims the inline text is complete when it is not,
    never re-runs the source command."""
    budget = inline_budget()
    if len(rendered) <= budget:
        return rendered
    env: dict[str, Any] = {"status": "completed", "inline_complete": False,
                           "tool": tool, "device": device, "command": command}
    try:
        meta = retain(payload, tool=tool, device=device, command=command, notes=notes)
        env.update({
            "retained": True, "handle": meta["handle"],
            "source_bytes": meta["source_bytes"], "source_sha256": meta["source_sha256"],
            "retention_truncated": meta["retention_truncated"],
            "producer_notes": meta["producer_notes"],
            "message": ("The full result is too large to return inline. This envelope is NOT the "
                        "complete result and must not be counted or summarised as if it were. "
                        "Use the result-analysis tools (result_describe, result_count, "
                        "result_select, result_text_search, result_lines) with this handle; each "
                        "answer states what it covered. Do not re-run the device command."),
        })
        if meta["retention_truncated"]:
            env["message"] += (" WARNING: the retained copy itself is truncated "
                               f"({meta['retention_truncation']}); answers will say so.")
    except Exception as exc:  # retention failed: say so loudly, keep a short preview
        env.update({"retained": False, "handle": None,
                    "error": f"result could not be retained: {type(exc).__name__}: {exc}",
                    "message": ("The result is too large to return inline and was NOT retained; "
                                "the preview below is incomplete and no count or total can be "
                                "derived from it. Do not re-run automatically.")})
    room = budget - 2500
    prev = _preview(payload, room)
    env["preview"] = prev
    out = json.dumps(env, indent=1, default=str)
    while len(out) > budget - 200 and "preview" in env:
        p = env["preview"]
        if p.get("sample_records"):
            p["sample_records"] = p["sample_records"][:-1]
        elif "head" in p and len(p["head"]) > 100:
            p["head"] = p["head"][: len(p["head"]) // 2]
        elif p.get("record_collections"):
            p["record_collections"] = p["record_collections"][:-1]
        else:
            env.pop("preview")
        out = json.dumps(env, indent=1, default=str)
    return out


def bounded_dict(result: dict, *, tool: str, device: str | None = None,
                 command: str | None = None, notes: list[str] | None = None) -> dict:
    """Dict-returning producers: `result` unchanged if inline-safe, else the envelope as a dict.

    A dict whose bulk is a plain-text `output` field is retained as TEXT (so it is line-pageable
    and searchable); its small sibling fields travel in the envelope as `source_fields`."""
    rendered = json.dumps(result, indent=1, default=str)
    if len(rendered) <= inline_budget():
        return result
    payload: Any = result
    extra: dict = {}
    if isinstance(result.get("output"), str):
        payload = result["output"]
        extra = {k: v for k, v in result.items() if k != "output"}
    out = json.loads(envelope(payload, rendered, tool=tool, device=device, command=command,
                              notes=notes))
    if extra and len(json.dumps(extra, default=str)) < 1500:
        out["source_fields"] = extra
    return out
