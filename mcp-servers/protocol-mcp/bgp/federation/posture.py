"""Risk posture — the Border's truthful production/degraded/testing self-report (057).

US1 / FR-001..003a, FR-019/020. The single most important property: the risk
NEVER claims full production while a control is missing. Posture aggregates the
three enforcement controls (controls.py) and drives the per-delegation preflight
decision (fail-closed on containment, warn on audit-only).

`compute_posture` is async (it awaits the control probes). `posture_ok_for_delegation`
is pure logic over an already-computed posture, so the delegation path computes
posture once then decides synchronously.
"""

import logging
import time
from typing import Optional

from . import controls

logger = logging.getLogger("n2n.posture")

# Control definitions: name → kind (containment blocks fail-closed; audit warns).
_CONTROL_KIND = {"sandbox": "containment", "model-guard": "containment", "audit": "audit"}


async def _probe_controls() -> list:
    """Probe all three controls; return the list of control dicts (data-model §2)."""
    sandbox_ok, sandbox_detail = await controls.sandbox_available()
    guard_ok, guard_detail = await controls.defenseclaw_available()
    audit_ok, audit_detail = controls.gait_recording()
    now = time.time()
    return [
        {"name": "sandbox", "kind": "containment", "available": sandbox_ok,
         "detail": sandbox_detail, "probed_at": now},
        {"name": "model-guard", "kind": "containment", "available": guard_ok,
         "detail": guard_detail, "probed_at": now},
        {"name": "audit", "kind": "audit", "available": audit_ok,
         "detail": audit_detail, "probed_at": now},
    ]


async def compute_posture(service=None) -> dict:
    """Return the current RiskPosture (data-model §1). `service` is accepted for
    signature stability / future use (e.g. per-risk overrides) but posture is
    derived from N2N_RISK_MODE + the control probes."""
    production = controls.is_production()
    strict = controls.strict_all()
    ctrls = await _probe_controls()
    missing = [c["name"] for c in ctrls if not c["available"]]

    if not production:
        # testing: guards intentionally off — never a false production claim (FR-006).
        state = "testing"
        summary = "testing"
    elif not missing:
        state = "enforced"
        summary = "production — enforced"
    else:
        state = "degraded"
        summary = f"production — DEGRADED ({', '.join(missing)} missing)"

    return {
        "mode": "production" if production else "testing",
        "state": state,
        "controls": ctrls,
        "missing": missing,
        "strict_all": strict,
        "model": _local_model(),
        "channel_security": _channel_security(service),
        "computed_at": time.time(),
        "summary": summary,
    }


def _channel_security(service) -> dict:
    """Feature 060 (FR-019): summarize channel trust — peers by trust model, any
    degraded (legacy/refused) channels, and credentials aging into amber/red."""
    if service is None:
        return {}
    import datetime as _dt
    try:
        peers = service.manager.list_peers()
        by_model, degraded = {}, 0
        for p in peers:
            tm = p.get("trust_model") or "legacy"
            by_model[tm] = by_model.get(tm, 0) + 1
            if tm == "legacy" or p.get("verify_state") == "refused-pending-patch":
                degraded += 1
        amber = red = failing = 0
        now = _dt.datetime.now(_dt.timezone.utc)
        for c in service.manager.list_credentials():
            if c.get("state") == "failed":
                failing += 1
            na = c.get("not_after")
            if na:
                try:
                    d = (_dt.datetime.fromisoformat(na) - now).days
                    if d < 14:
                        red += 1
                    elif d < 30:
                        amber += 1
                except Exception:
                    pass
        return {"mode": ("enforce" if getattr(service, "cert_enforce", False) else
                         ("on" if getattr(service, "cert_mode", False) else "off")),
                "by_trust_model": by_model, "degraded": degraded,
                "amber": amber, "red": red, "renewals_failing": failing}
    except Exception:
        return {}


def _local_model() -> dict:
    """This claw's primary model + whether it's routed through the DefenseClaw
    guardrail — surfaced in posture (HUD/heartbeat) and mirrored in the A2A card."""
    import json as _json
    import os as _os
    try:
        cfg = _json.loads(open(_os.path.expanduser("~/.openclaw/openclaw.json")).read())
        ag = (cfg.get("agents") or {}).get("defaults") or {}
        m = ag.get("model")
        primary = m.get("primary") if isinstance(m, dict) else m
        primary = primary or ""
        guarded = primary.startswith("defenseclaw/")
        return {"primary": primary.split("/", 1)[1] if guarded and "/" in primary else primary,
                "guarded": guarded}
    except Exception:
        return {"primary": None, "guarded": False}


def posture_ok_for_delegation(posture: dict, *, strict_all: Optional[bool] = None) -> dict:
    """Preflight decision for a delegation (FR-003a/019/020).

    Returns {allow, enforcement, refused_control, reason}:
      * testing mode                         → allow, enforcement='testing'
      * production, all controls up          → allow, enforcement='enforced'
      * production, a CONTAINMENT gap        → refuse (fail-closed)
      * production, AUDIT-only gap           → allow, enforcement='audit-degraded'
      * strict_all + ANY gap                 → refuse
    """
    if strict_all is None:
        strict_all = bool(posture.get("strict_all"))

    if posture.get("mode") != "production":
        return {"allow": True, "enforcement": "testing", "refused_control": None,
                "reason": "testing mode — guards intentionally off"}

    missing = posture.get("missing") or []
    if not missing:
        return {"allow": True, "enforcement": "enforced", "refused_control": None,
                "reason": ""}

    # Classify the gaps.
    kinds = {c["name"]: c["kind"] for c in posture.get("controls", [])}
    containment_gaps = [m for m in missing if kinds.get(m, "containment") == "containment"]
    audit_gaps = [m for m in missing if kinds.get(m) == "audit"]

    if containment_gaps:
        ctrl = containment_gaps[0]
        return {"allow": False, "enforcement": f"refused:{ctrl}", "refused_control": ctrl,
                "reason": f"production containment control unavailable: {ctrl} — "
                          f"delegation refused (fail-closed)"}

    # Only audit gaps remain.
    if strict_all:
        ctrl = audit_gaps[0]
        return {"allow": False, "enforcement": f"refused:{ctrl}", "refused_control": ctrl,
                "reason": f"strict-all: audit control unavailable ({ctrl}) — refused"}

    return {"allow": True, "enforcement": "audit-degraded", "refused_control": None,
            "reason": f"audit control unavailable ({', '.join(audit_gaps)}) — "
                      f"running but flagged audit-degraded"}
