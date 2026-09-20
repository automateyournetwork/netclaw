"""
Disposable Jev (TypeSafe System One) client for the jev-audit harness.

Throwaway tooling for branch jev-audit — not integrated into NetClaw, not
meant to be maintained long-term. See docs/jev-audit/findings.md.
"""
from __future__ import annotations

import os
import secrets
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

API_KEY = os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
if not API_KEY:
    raise RuntimeError("Set JEV_API_KEY (or TYPESAFE_API_KEY) in .env at repo root")

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
PRICE_PER_MTOK_INPUT = 0.042  # USD; output tokens are free
SWEEP_STOP_USD = 1.50

_lock = threading.Lock()
_usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}


def usage_snapshot() -> dict:
    with _lock:
        return dict(_usage)


def cost_so_far() -> float:
    with _lock:
        return _usage["input_tokens"] / 1_000_000 * PRICE_PER_MTOK_INPUT


def est_tokens(obj) -> int:
    """Rough chars/4 heuristic for pre-flight estimates only. Real cost comes from API usage."""
    import json

    s = obj if isinstance(obj, str) else json.dumps(obj)
    return max(1, len(s) // 4)


# Wall-clock guard against low-level connection stalls observed live on this host (WSL2):
# a subset of requests around ~20KB+ would sit with unacknowledged data in the TCP send
# queue indefinitely, with requests' own `timeout=` never firing (no exception, no progress,
# CPU pinned at 0). A stuck attempt is abandoned (its thread may leak/die on its own; harmless
# for a short-lived script) and retried fresh rather than allowed to block the whole sweep.
_send_pool = ThreadPoolExecutor(max_workers=256)
HARD_CALL_TIMEOUT_S = 20


def _post(body: dict, headers: dict):
    return requests.post(ENDPOINT, headers=headers, json=body, timeout=15)


def call(state, questions: dict, max_retries: int = 6) -> dict:
    """POST one evaluation request to /v1/systemone. Retries on 429/5xx/timeout/stall with backoff."""
    body = {"state": state, "model": MODEL, "questions": questions}
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    delay = 1.0
    last_err = None
    for attempt in range(max_retries):
        fut = _send_pool.submit(_post, body, headers)
        try:
            resp = fut.result(timeout=HARD_CALL_TIMEOUT_S)
        except FutureTimeoutError:
            last_err = f"stalled past {HARD_CALL_TIMEOUT_S}s (attempt {attempt + 1}/{max_retries})"
            print(f"[common] {last_err}, retrying with a fresh connection", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 30)
            continue
        except requests.RequestException as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(delay)
            delay = min(delay * 2, 30)
            continue

        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            with _lock:
                _usage["input_tokens"] += usage.get("input_tokens", 0)
                _usage["output_tokens"] += usage.get("output_tokens", 0)
                _usage["calls"] += 1
            return data
        if resp.status_code == 429 or resp.status_code >= 500:
            last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
            retry_after = resp.headers.get("retry-after")
            wait = float(retry_after) if retry_after else delay
            time.sleep(wait)
            delay = min(delay * 2, 30)
            continue
        raise RuntimeError(f"Jev call failed: {resp.status_code} {resp.text[:500]}")
    raise RuntimeError(f"Jev call failed after {max_retries} retries: {last_err}")


MID_BAND = (0.30, 0.70)  # per the self-consistency: nouls cookbook


def is_mid_band(noul: float) -> bool:
    return MID_BAND[0] <= noul <= MID_BAND[1]


def _add_uid(state):
    uid = secrets.token_hex(4)
    if isinstance(state, dict):
        s = dict(state)
        s["_uid"] = uid
        return s
    return {"content": state, "_uid": uid}


def self_consistency_recheck(state, question: dict, n: int = 5, stable_stdev: float = 0.15) -> dict:
    """Re-run one noul question n times with a fresh throwaway uid each time.
    Mirrors the self-consistency: nouls cookbook. Only meaningful for `noul` questions.
    The n reruns are independent, so they're fired concurrently rather than in a
    sequential loop — sequential reruns were the main reason phase B throughput stayed
    sublinear even after raising worker count (each target's 5 calls serialized inside
    one worker thread)."""
    # A dedicated, short-lived pool: `call()` itself submits to the module-level
    # `_send_pool` for its own hard-timeout guard, so submitting `call()` onto that
    # same pool would nest submissions and could exhaust/deadlock it.
    with ThreadPoolExecutor(max_workers=n) as recheck_pool:
        futs = [recheck_pool.submit(call, _add_uid(state), {"q": question}) for _ in range(n)]
        vals = [f.result()["answers"]["q"]["noul"] for f in futs]
    mean = statistics.mean(vals)
    stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return {"values": vals, "mean": mean, "stdev": stdev, "stable": stdev < stable_stdev}


def enforce_budget(sweep_name: str, estimated_usd: float) -> None:
    print(f"[{sweep_name}] estimated cost: ${estimated_usd:.4f} (stop threshold ${SWEEP_STOP_USD:.2f})")
    if estimated_usd > SWEEP_STOP_USD:
        raise SystemExit(
            f"[{sweep_name}] estimated ${estimated_usd:.4f} exceeds the ${SWEEP_STOP_USD:.2f} "
            "per-sweep stop threshold. Halting before spending anything."
        )
