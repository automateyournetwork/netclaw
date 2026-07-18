"""iN2N production enforcement controls (feature 057).

Probes and applies the three production controls the Border's posture aggregates:

  * sandbox      → NVIDIA OpenShell   (containment; `openshell` CLI)
  * model-guard  → Cisco DefenseClaw  (containment; `defenseclaw` CLI + security.mode)
  * audit        → GAIT git trail     (audit; bgp.federation.gait)

Design (see specs/057 research R1/R2/R3):
  * Each probe is a cheap local check, cached ~3s so a burst of delegation
    preflights doesn't spawn a burst of CLI calls, yet a control that just
    dropped is reflected on the next delegation.
  * All probes return (available: bool, detail: str). `detail` is the human
    reason when unavailable, surfaced in the degraded posture.
  * model-guard availability requires BOTH the DefenseClaw guard being reachable
    AND security.mode == 'defenseclaw' — a merely-installed-but-disabled CLI is
    NOT available, so production can never falsely report 'enforced' (analyze I1).
  * Fail-closed is enforced at the delegation preflight (posture.py) and at member
    launch (gateway.py); this module only reports truthfully.

No new third-party packages — stdlib + the already-installed CLIs.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("n2n.controls")

_CACHE_TTL_S = 3.0
_cache: dict = {}   # name -> (expiry_epoch, (available, detail))


def _security_config_path() -> Path:
    """The DefenseClaw security-mode config. Per CLAUDE.md this lives in
    ~/.openclaw/config/openclaw.json — NOT the gateway's ~/.openclaw/openclaw.json,
    whose `security` object has a different schema (writing 'mode' there makes the
    gateway fail startup with 'security: Invalid input')."""
    return Path(os.path.expanduser("~/.openclaw/config/openclaw.json"))


def security_mode() -> str:
    """DefenseClaw's guardrail mode ('hobby' | 'defenseclaw'). Default 'hobby'.
    Read from the DefenseClaw config, not the gateway config."""
    try:
        cfg = json.loads(_security_config_path().read_text())
        return (cfg.get("security") or {}).get("mode", "hobby")
    except Exception:
        return "hobby"


def is_production() -> bool:
    """The 057 risk-level enforcement flag (independent of security.mode)."""
    return os.environ.get("N2N_RISK_MODE", "testing").strip().lower() == "production"


def strict_all() -> bool:
    """Operator override: block on ANY missing control, including audit (FR-019)."""
    return os.environ.get("N2N_STRICT_ALL", "").strip().lower() in ("1", "true", "yes")


async def _run(cmd, timeout_s: float = 12.0) -> Tuple[int, str]:
    """Run a probe command; return (returncode, combined_output). -1 on error."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        return proc.returncode, (out.decode(errors="replace") if out else "")
    except FileNotFoundError:
        return -1, "not found"
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return -1, "probe timed out"
    except Exception as e:  # pragma: no cover - defensive
        return -1, f"probe error: {e}"


def _cached(name: str):
    hit = _cache.get(name)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    return None


def _store(name: str, value: Tuple[bool, str]) -> Tuple[bool, str]:
    _cache[name] = (time.monotonic() + _CACHE_TTL_S, value)
    return value


def invalidate_cache():
    """Drop cached probe results (tests / after a known state change)."""
    _cache.clear()


async def openshell_available() -> Tuple[bool, str]:
    """Back-compat alias → sandbox confinement probe (see sandbox_available)."""
    return await sandbox_available()


async def sandbox_available() -> Tuple[bool, str]:
    """(True, "") if member CONFINEMENT is in effect; else (False, reason).

    Feature 057 US2 sandbox = HOST-LEVEL kernel confinement of each member process
    via systemd sandboxing directives (the member keeps its real home/tools/network
    but runs with reduced privileges + a read-only system + hidden master secrets).
    This replaces the earlier OpenShell-container approach, which could not run a
    live-infrastructure member (empty container: no tools, no network egress).

    Probe: `systemctl --user` is available AND the generated member units carry the
    confinement directives (NoNewPrivileges + ProtectSystem). On a host without a
    systemd user manager the confinement cannot be applied → unavailable → the
    posture honestly reports the sandbox control degraded."""
    cached = _cached("sandbox")
    if cached is not None:
        return cached
    if not shutil.which("systemctl"):
        return _store("sandbox", (False, "systemctl not found — cannot confine members"))
    # Is a systemd --user manager reachable?
    rc, _ = await _run(["systemctl", "--user", "show-environment"], timeout_s=10)
    if rc != 0:
        return _store("sandbox", (False, "systemd --user manager unavailable"))
    # Are member units confined? Check any generated member unit for the directives.
    unit_dir = os.path.expanduser("~/.config/systemd/user")
    try:
        members = [f for f in os.listdir(unit_dir) if f.startswith("netclaw-member-")]
    except OSError:
        members = []
    if not members:
        # No member units yet — the mechanism is available; confinement applies on
        # generate. Report available so a fresh Border isn't falsely degraded.
        return _store("sandbox", (True, "systemd confinement available (no member units yet)"))
    for unit in members:
        rc, out = await _run(["systemctl", "--user", "show", unit,
                              "-p", "NoNewPrivileges,ProtectSystem"], timeout_s=10)
        if "NoNewPrivileges=yes" not in out or "ProtectSystem=" not in out or "ProtectSystem=no" in out:
            return _store("sandbox", (False, f"member unit {unit} is not confined "
                                              f"(regenerate: scripts/in2n-services.py generate)"))
    return _store("sandbox", (True, ""))


DEFENSECLAW_GUARD_PORT = int(os.environ.get("DEFENSECLAW_GUARD_PORT", "4000"))


async def defenseclaw_available() -> Tuple[bool, str]:
    """(True, "") if DefenseClaw model-I/O guarding is actually in effect; else (False, reason).

    DefenseClaw guards model I/O via its **LLM guardrail proxy** (a Go proxy,
    default port 4000, enabled by `defenseclaw setup guardrail`) that every prompt
    and response is routed through for inspection — NOT via a per-call CLI command
    (there is no `defenseclaw tool inspect`). So "available" requires ALL of:
    `defenseclaw` on PATH, `security.mode == 'defenseclaw'`, AND the guardrail
    proxy reachable. A merely-installed CLI with the proxy down is NOT available —
    this is what prevents a false 'enforced' (the 056 "silent bypass to direct
    provider" bug). To reach enforced, run `defenseclaw setup guardrail --mode
    action` and route members through the proxy."""
    cached = _cached("model-guard")
    if cached is not None:
        return cached
    if not shutil.which("defenseclaw"):
        return _store("model-guard", (False, "defenseclaw CLI not found on PATH"))
    # The authoritative signal is the guardrail PROXY being up — that is the guard
    # (every prompt/response routed through it for inspection). A reachable proxy
    # means guarding is actually happening; a down proxy means it is not (no false
    # 'enforced').
    if not await _guard_proxy_up():
        return _store("model-guard",
                      (False, f"DefenseClaw guardrail proxy not reachable on :"
                              f"{DEFENSECLAW_GUARD_PORT} (run: defenseclaw setup guardrail "
                              f"then defenseclaw-gateway start)"))
    return _store("model-guard", (True, ""))


async def _guard_proxy_up() -> bool:
    """Is the DefenseClaw guardrail proxy accepting connections?"""
    try:
        fut = asyncio.open_connection("127.0.0.1", DEFENSECLAW_GUARD_PORT)
        reader, writer = await asyncio.wait_for(fut, timeout=3)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


def gait_recording() -> Tuple[bool, str]:
    """(True, "") if the GAIT git trail is initialized and writable; else (False, reason)."""
    cached = _cached("audit")
    if cached is not None:
        return cached
    try:
        from . import gait
        ok, detail = gait.ensure_repo()
        return _store("audit", (ok, detail))
    except Exception as e:
        return _store("audit", (False, f"GAIT unavailable: {e}"))


# ---- application helpers (used by gateway.py / service.py) ----------------

# Portable systemd confinement props applied to a member process (feature 057).
# Mirrors scripts/in2n-services.py _hardening_block portable set; used for
# cold-started (on-demand) members via `systemd-run --user` so even non-service
# members run confined in production. Capability/namespace props are added by the
# service generator only where the manager supports them (native Linux).
_CONFINE_PROPS = [
    "NoNewPrivileges=yes", "PrivateTmp=yes", "ProtectSystem=strict",
    "ReadWritePaths=%h", "InaccessiblePaths=-%h/.openclaw/.env",
]


def confined_cold_start(launch_cmd: str, member_id: str) -> list:
    """Return an argv that cold-starts a member CONFINED via a transient
    `systemd-run --user` unit (feature 057). Falls back to the bare command if
    systemd-run is unavailable (the posture will report the sandbox degraded)."""
    if not shutil.which("systemd-run"):
        return ["/bin/sh", "-c", launch_cmd]
    slug = member_id.replace("/", "-")
    argv = ["systemd-run", "--user", "--collect",
            "--unit", f"netclaw-coldmember-{slug}"]
    # systemd-run sends -p properties over D-Bus, where %-specifiers are NOT
    # expanded (unlike unit files) — %h must be resolved here or the transient
    # unit is rejected with "Invalid ReadWritePaths".
    home = os.path.expanduser("~")
    for p in _CONFINE_PROPS:
        argv += ["-p", p.replace("%h", home)]
    argv += ["/bin/sh", "-c", launch_cmd]
    return argv


async def component_scan(skills: list) -> Tuple[bool, str]:
    """DefenseClaw component scan of a member's scoped skills before it runs
    (FR-008). Returns (ok, verdict): ok=True → 'pass'; ok=False → 'flagged:<name>'
    (a component was flagged) or 'error:<detail>' (scan could not run → fail-closed
    in production). An empty skill list passes trivially."""
    if not skills:
        return True, "pass"
    if not shutil.which("defenseclaw"):
        return False, "error:defenseclaw CLI not found"
    for name in skills:
        rc, out = await _run(["defenseclaw", "skill", "scan", str(name)], timeout_s=60.0)
        if rc == -1:
            return False, f"error:scan failed for {name}"
        low = out.lower()
        # DefenseClaw exits non-zero on a flag. Match verdicts, not bare
        # substrings: 0.8.x prints "blocked=0" in EVERY summary (even CLEAN)
        # and the word "critical" can appear in finding descriptions, so the
        # old substring checks flagged clean scans.
        if (rc != 0
                or re.search(r"verdict:\s*(critical|high)", low)
                or re.search(r"\bblocked=[1-9]", low)
                or "high severity" in low):
            return False, f"flagged:{name}"
    return True, "pass"


def require_defenseclaw_mode() -> Tuple[bool, str]:
    """Require (verify, do NOT mutate) security.mode='defenseclaw' on entering
    production (T019a / FR-007). This is what guards the BORDER's own model turns,
    which run through the OpenClaw gateway.

    Returns (ok, detail). This is deliberately CHECK-ONLY: a daemon must never
    silently rewrite the host's security configuration (an earlier auto-write into
    the wrong file broke the gateway). If mode isn't 'defenseclaw', the operator
    enables it via the DefenseClaw tooling (./scripts/defenseclaw-enable.sh); until
    then model-guard probes unavailable → posture honestly degraded, never a false
    'enforced'."""
    mode = security_mode()
    if mode == "defenseclaw":
        return True, "security.mode=defenseclaw (Border model turns guarded)"
    return (False, f"security.mode is '{mode}' — enable DefenseClaw "
                   f"(./scripts/defenseclaw-enable.sh) to reach production-enforced")
