"""Fleet fan-out: one query, many devices, isolated failures.

Spec 076 FR-013 through FR-016. Contract:
specs/076-multivendor-cli-driver/contracts/mcp-tools.md

The invariant that matters: **every targeted device appears in the results,
including the ones that failed** (FR-014). A silently absent device reads as
success, which is the most dangerous possible output for a fleet query — an
operator scanning results sees no problem where there is one.

Concurrency defaults to 10 workers rather than Nornir's own default of 20. Each
worker holds an SSH session, and network devices commonly cap concurrent
management sessions somewhere between 5 and 15. Starting conservative and
documenting the override is safer than discovering a device's session limit under
load, in production, at 2am.

Threads rather than asyncio: netmiko and NAPALM are both synchronous, so a thread
pool is the honest model. Pretending otherwise would mean wrapping blocking calls
in an executor anyway.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from inventory import sources as inv
from tools import facts as fact_tools
from tools import raw as raw_tools

SERVER_ID = "multivendor-cli"

DEFAULT_MAX_WORKERS = int(os.environ.get("MULTIVENDOR_MAX_WORKERS", "10"))
DEFAULT_TIMEOUT = int(os.environ.get("MULTIVENDOR_TIMEOUT_S", "30"))


def _select(devices: list[inv.Device], target: str) -> list[inv.Device]:
    """Resolve a target into devices: a group name, a comma-list, or 'all'."""
    t = target.strip()
    if t in ("all", "*"):
        return list(devices)
    if "," in t:
        wanted = {n.strip() for n in t.split(",") if n.strip()}
        return [d for d in devices if d.name in wanted]
    by_group = [d for d in devices if t in d.groups]
    if by_group:
        return by_group
    return [d for d in devices if d.name == t]


def run_fleet(target: str, command: str | None = None,
              getters: list[str] | None = None,
              max_workers: int | None = None,
              timeout_s: int | None = None) -> dict:
    """Run one query across a group of devices, concurrently.

    Exactly one of `command` (raw) or `getters` (normalized) must be supplied.
    """
    if bool(command) == bool(getters):
        return {"server": SERVER_ID, "status": "error",
                "error": "supply exactly one of 'command' or 'getters'"}

    max_workers = max_workers or DEFAULT_MAX_WORKERS
    timeout_s = timeout_s or DEFAULT_TIMEOUT

    try:
        res = inv.resolve()
    except inv.InventoryError as exc:
        return {"server": SERVER_ID, "status": "error", "error": str(exc)}

    selected = _select(res.devices, target)
    if not selected:
        return {"server": SERVER_ID, "target": target, "status": "error",
                "error": f"target {target!r} matched no devices; "
                         f"known groups: {sorted({g for d in res.devices for g in d.groups})}"}

    def work(dev: inv.Device) -> dict:
        # Each device's failure is captured as its own result, never raised —
        # one device must not abort the operation for the others (FR-014).
        try:
            if command:
                return raw_tools.run_command(dev.name, command, timeout_s)
            return fact_tools.get_facts(dev.name, getters, timeout_s)
        except Exception as exc:  # noqa: BLE001
            return {"server": SERVER_ID, "device": dev.name, "platform": dev.platform,
                    "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(selected))) as pool:
        futures = {pool.submit(work, d): d for d in selected}
        for fut in as_completed(futures):
            dev = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001 - defensive; work() already catches
                results.append({"server": SERVER_ID, "device": dev.name,
                                "status": "error",
                                "error": f"{type(exc).__name__}: {str(exc)[:200]}"})

    # Preserve inventory order so output is stable and diffable across runs,
    # rather than reflecting whichever device happened to answer first.
    order = {d.name: i for i, d in enumerate(selected)}
    results.sort(key=lambda r: order.get(r.get("device", ""), 999))

    summary: dict[str, int] = {}
    for r in results:
        summary[r.get("status", "unknown")] = summary.get(r.get("status", "unknown"), 0) + 1

    return {
        "server": SERVER_ID,
        "target": target,
        "source_used": res.source.value,
        "requested": len(selected),
        "returned": len(results),
        "max_workers": max_workers,
        "timeout_s": timeout_s,
        "summary": summary,
        "results": results,
    }
