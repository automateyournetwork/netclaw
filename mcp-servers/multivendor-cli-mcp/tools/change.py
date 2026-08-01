"""Gated configuration change: baseline -> CR -> approval -> apply -> verify -> rollback.

Spec 076 FR-024 through FR-028, FR-025a/b/c. Constitution Principles I, II, III,
IV, VIII.

Every arrow above is a **gate, not a step**. There is no path to `applied` that
skips one.

The distinction that took a `/speckit.analyze` finding to surface: **human approval
and an ITSM Change Request are two different gates.** FR-025 wants a person to say
yes. Constitution Principle III wants change-management authorisation with an
Assess -> Authorize -> Implement -> Review lifecycle. Satisfying one does not
satisfy the other, and an earlier draft of this feature had Principle III marked
"inherited from the existing approval path" — an assertion with no implementation
behind it.

Lab devices are exempt from the CR requirement (FR-025c) but still audited. An
**unclassified** device is treated as production, never assumed to be lab: the
failure mode of guessing wrong in that direction is an unauthorised production
change.

Write tools are absent from the MCP surface entirely unless MULTIVENDOR_WRITE_ENABLED
is set (FR-022) — absent, not present-and-refusing, so an agent cannot even attempt
a change that was never sanctioned.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import routing
from credentials import CredentialError, resolve as resolve_credential
from inventory import sources as inv
from policy.filter import Mode, evaluate

SERVER_ID = "multivendor-cli"

# Per-device timeout, shared default with tools/raw.py and tools/facts.py.
DEFAULT_TIMEOUT = int(os.environ.get("MULTIVENDOR_TIMEOUT_S", "30"))

# Baselines are written here and nowhere else. Path is sandboxed: a traversal in a
# device name must not be able to write outside this root.
BASELINE_ROOT = Path(os.environ.get(
    "MULTIVENDOR_BASELINE_DIR",
    os.path.expanduser("~/.openclaw/multivendor/baselines")))

# Inventory groups that mark a device as lab. Everything else is production.
LAB_GROUPS = {g.strip().lower() for g in
              os.environ.get("MULTIVENDOR_LAB_GROUPS", "lab,srlinux,frr,sandbox").split(",")
              if g.strip()}

# ServiceNow change states that count as authorised to implement.
APPROVED_CR_STATES = {"implement", "scheduled", "-1", "-2"}
REJECTED_CR_STATES = {"canceled", "cancelled", "closed", "rejected", "4", "7"}


class Stage(str, Enum):
    REFUSED = "refused"
    LAB_EXEMPT = "lab_exempt"
    CR_REQUIRED = "cr_required"
    CR_NOT_APPROVED = "cr_not_approved"
    AWAITING_APPROVAL = "awaiting_approval"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"
    # Distinct from FAILED on purpose. FAILED means state is definitively wrong.
    # INCONCLUSIVE means the push reported success but the change could not be
    # confirmed in the after-state — which on some platforms is a limitation of
    # this verifier, not evidence of failure. SR Linux is the known case: `set`
    # lands in a candidate datastore and needs an explicit `commit`, and its
    # running-config rendering does not echo the input line verbatim. Both are
    # rolled back regardless (fail-safe), but conflating them would misreport a
    # tooling gap as a device fault.
    VERIFICATION_INCONCLUSIVE = "verification_inconclusive"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_FAILED = "rollback_failed"
    DENIED = "denied"
    ERROR = "error"


def is_lab(dev: inv.Device) -> bool:
    """Lab classification from inventory metadata only (FR-025c).

    An unclassified device is production. Guessing "lab" wrongly permits an
    unauthorised production change; guessing "production" wrongly costs one CR.
    """
    return any(g.lower() in LAB_GROUPS for g in dev.groups)


def _audit(event: str, **fields) -> None:
    """Append to the audit trail (FR-028, Principle IV).

    Writes alongside the baselines rather than into GAIT directly: GAIT is a git
    repo with its own commit discipline, and this module must not assume it is
    initialised. A future task wires this into gait-mcp proper.
    """
    BASELINE_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    safe = {k: v for k, v in fields.items() if "password" not in k.lower()}
    line = f"{stamp} {event} " + " ".join(f"{k}={v!r}" for k, v in safe.items())
    with open(BASELINE_ROOT / "audit.log", "a") as f:
        f.write(line + "\n")


def check_change_request(cr_number: str | None) -> dict:
    """Look up a ServiceNow change request and decide whether it authorises work.

    Returns a verdict dict rather than raising, so the caller can report *why* a
    change is blocked. Absence of ServiceNow configuration is reported as
    unconfigured rather than treated as approval.
    """
    url = os.environ.get("SERVICENOW_INSTANCE_URL")
    user = os.environ.get("SERVICENOW_USERNAME")
    pw = os.environ.get("SERVICENOW_PASSWORD")

    if not cr_number:
        return {"approved": False, "reason": "no change request supplied"}
    if not (url and user and pw):
        return {"approved": False,
                "reason": "ServiceNow is not configured (SERVICENOW_INSTANCE_URL / "
                          "USERNAME / PASSWORD); a production change cannot be "
                          "authorised without it"}

    import httpx

    endpoint = url.rstrip("/") + "/api/now/table/change_request"
    try:
        r = httpx.get(endpoint, auth=(user, pw), timeout=20,
                      params={"sysparm_query": f"number={cr_number}",
                              "sysparm_fields": "number,state,short_description,approval",
                              "sysparm_limit": 1})
        r.raise_for_status()
        rows = r.json().get("result", [])
    except Exception as exc:  # noqa: BLE001
        return {"approved": False,
                "reason": f"could not verify change request: {type(exc).__name__}: {str(exc)[:160]}"}

    if not rows:
        return {"approved": False, "reason": f"change request {cr_number!r} not found"}

    cr = rows[0]
    state = str(cr.get("state", "")).strip().lower()
    approval = str(cr.get("approval", "")).strip().lower()

    if state in REJECTED_CR_STATES:
        return {"approved": False, "cr": cr, "state": state,
                "reason": f"change request {cr_number} is in state {state!r} — "
                          f"rejected or closed, so work must halt"}
    if approval == "approved" or state in APPROVED_CR_STATES:
        return {"approved": True, "cr": cr, "state": state,
                "reason": f"change request {cr_number} authorises implementation "
                          f"(state={state!r}, approval={approval!r})"}
    return {"approved": False, "cr": cr, "state": state,
            "reason": f"change request {cr_number} is not authorised "
                      f"(state={state!r}, approval={approval!r})"}


def _baseline_path(device: str) -> Path:
    """Sandboxed baseline path — a traversal in a device name cannot escape."""
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in device)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    BASELINE_ROOT.mkdir(parents=True, exist_ok=True)
    resolved = (BASELINE_ROOT / f"{safe}-{stamp}.cfg").resolve()
    if BASELINE_ROOT.resolve() not in resolved.parents:
        raise ValueError(f"refusing to write baseline outside {BASELINE_ROOT}")
    return resolved


def apply_config(device: str, config: str, change_request: str | None = None,
                 approved_by: str | None = None) -> dict:
    """Apply configuration, only if every gate is satisfied.

    Gate order is deliberate and each returns before the next is considered:
      routing -> filter -> lab/production -> CR -> human approval -> baseline -> apply
    """
    if os.environ.get("MULTIVENDOR_WRITE_ENABLED", "").lower() not in ("1", "true", "yes"):
        return {"server": SERVER_ID, "device": device, "status": Stage.REFUSED.value,
                "refused_reason": "write mode is not enabled "
                                  "(set MULTIVENDOR_WRITE_ENABLED=true)"}

    try:
        res = inv.resolve()
        dev = inv.find(res.devices, device)
    except inv.InventoryError as exc:
        return {"server": SERVER_ID, "device": device, "status": Stage.ERROR.value,
                "error": str(exc)}

    base = {"server": SERVER_ID, "device": device, "platform": dev.platform,
            "source": res.source.value}

    # --- Gate 1: routing. Writes are single-pathed per platform (FR-010). ---
    decision = routing.route(dev.platform, routing.Operation.WRITE)
    if decision.refused:
        _audit("change.refused.routing", device=device, owner=decision.owning_server)
        payload = routing.refusal_payload(device, dev.platform, decision)
        payload.update(base)
        return payload

    # --- Gate 2: filter. Destructive config is refused regardless of approval. ---
    for line in [ln for ln in config.splitlines() if ln.strip()]:
        verdict = evaluate(line, dev.platform, Mode.WRITE_ENABLED)
        if not verdict.allowed:
            _audit("change.denied.filter", device=device, line=line[:60])
            return {**base, "status": Stage.DENIED.value,
                    "denied_reason": f"config line {line.strip()!r}: {verdict.denied_reason}"}

    # --- Gate 3: lab vs production (FR-025c) ---
    lab = is_lab(dev)

    # --- Gate 4: ServiceNow CR, for production only (FR-025a, Principle III) ---
    cr_verdict = None
    if not lab:
        cr_verdict = check_change_request(change_request)
        if not cr_verdict["approved"]:
            _audit("change.blocked.cr", device=device, cr=change_request,
                   reason=cr_verdict["reason"][:80])
            return {**base, "status": Stage.CR_NOT_APPROVED.value,
                    "classification": "production",
                    "change_request": change_request,
                    "cr_reason": cr_verdict["reason"],
                    "note": "production changes require an approved ServiceNow change "
                            "request; human approval alone is not sufficient "
                            "(Constitution Principle III)"}

    # --- Gate 5: explicit human approval (FR-025, Principle I) ---
    if not approved_by:
        _audit("change.awaiting_approval", device=device, cr=change_request)
        return {**base, "status": Stage.AWAITING_APPROVAL.value,
                "classification": "lab" if lab else "production",
                "change_request": change_request,
                "cr_reason": cr_verdict["reason"] if cr_verdict else None,
                "note": "supply approved_by to proceed; a change request authorises "
                        "the work but a human must still approve this execution"}

    # --- Gate 6: baseline BEFORE any modification (FR-024, Principle II) ---
    from tools.raw import run_command
    probe = 'vtysh -c "show running-config"' if (dev.platform or "").lower() in ("frr", "linux") \
        else "show running-config"
    snapshot = run_command(device, probe)
    if snapshot["status"] != "ok":
        _audit("change.aborted.no_baseline", device=device, status=snapshot["status"])
        return {**base, "status": Stage.ERROR.value,
                "error": f"could not capture a baseline (status={snapshot['status']}); "
                         f"refusing to modify anything without one",
                "detail": snapshot.get("error") or snapshot.get("denied_reason")}

    path = _baseline_path(device)
    path.write_text(snapshot.get("output") or "")
    _audit("change.baseline", device=device, baseline=str(path),
           bytes=len(snapshot.get("output") or ""))

    gates = ["routing", "filter", "classification",
             "change_request" if not lab else "lab_exempt",
             "human_approval", "baseline"]
    common = {**base,
              "classification": "lab" if lab else "production",
              "change_request": change_request,
              "cr_reason": cr_verdict["reason"] if cr_verdict else None,
              "approved_by": approved_by,
              "baseline_ref": str(path),
              "gates_passed": gates}

    # --- Apply (FR-026 path begins) ---
    _audit("change.applying", device=device, lines=len(config.splitlines()))
    applied = _send_config(dev, config, timeout_s=DEFAULT_TIMEOUT)
    if not applied["ok"]:
        _audit("change.apply_failed", device=device, error=str(applied["error"])[:80])
        return {**common, "status": Stage.ERROR.value,
                "error": f"config application failed: {applied['error']}",
                "note": "nothing was verified; inspect the device against the baseline"}

    # --- Verify: compare ACTUAL state against expected, not exit status (FR-026) ---
    after = _capture(device, dev)
    if after is None:
        _audit("change.verify_unreadable", device=device)
        return {**common, "status": Stage.VERIFICATION_FAILED.value,
                "error": "could not re-read configuration after applying, so the "
                         "change cannot be verified",
                "rollback": _rollback(dev, device, path, common)["rollback"]}

    diff = _structured_diff(path.read_text(), after)
    _audit("change.verified" if diff["changed"] else "change.noop",
           device=device, added=len(diff["added"]), removed=len(diff["removed"]))

    # Every non-comment config line supplied must be present afterwards. A command
    # that "succeeded" while leaving no trace is the failure mode FR-026 exists for:
    # exit status is not evidence.
    expected = [ln.strip() for ln in config.splitlines() if ln.strip()]
    missing = [ln for ln in expected if ln not in after]
    if missing:
        rb = _rollback(dev, device, path, common)
        # If the device's config changed at all, something happened but this
        # verifier could not attribute it — inconclusive. If nothing changed AND
        # the lines are absent, the push genuinely had no effect.
        inconclusive = diff["changed"] or _needs_commit(dev.platform)
        return {**common,
                "status": (Stage.VERIFICATION_INCONCLUSIVE if inconclusive
                           else Stage.VERIFICATION_FAILED).value,
                "diff": diff,
                "missing_after_apply": missing,
                "error": ("configuration was pushed and reported success, but could not "
                          "be confirmed in the after-state. "
                          + (f"Platform {dev.platform!r} uses a candidate datastore "
                             f"requiring an explicit commit, which this verifier does "
                             f"not yet issue — treat as UNVERIFIED, not as applied."
                             if _needs_commit(dev.platform) else
                             "Command success is not evidence of state change."))
                if inconclusive else
                ("applied configuration is absent from the device afterwards and nothing "
                 "changed; command success is not evidence of state change"),
                **rb}

    return {**common, "status": Stage.VERIFIED.value, "diff": diff,
            "rollback": "not_needed"}


# Platforms whose configuration lands in a candidate datastore and requires an
# explicit commit. Writes to these are NOT fully supported yet: this module pushes
# but does not commit, so a change cannot be confirmed. Reads are unaffected.
COMMIT_REQUIRED = {"nokia_srl", "nokia_srlinux", "nokia_sros", "juniper_junos", "vyos"}


def _needs_commit(platform: str | None) -> bool:
    from policy.platform_deny import canonical
    return canonical(platform) in COMMIT_REQUIRED or (platform or "").lower() in COMMIT_REQUIRED


def _capture(device: str, dev: inv.Device) -> str | None:
    """Read the running configuration, or None if it cannot be read."""
    from tools.raw import run_command
    probe = 'vtysh -c "show running-config"' if (dev.platform or "").lower() in ("frr", "linux") \
        else "show running-config"
    r = run_command(device, probe)
    return r.get("output") if r["status"] == "ok" else None


def _send_config(dev: inv.Device, config: str, timeout_s: int) -> dict:
    """Push configuration lines via netmiko's config mode."""
    from tools.raw import NETMIKO_DRIVER
    driver = NETMIKO_DRIVER.get((dev.platform or "").lower())
    if driver is None:
        return {"ok": False, "error": f"no driver for platform {dev.platform!r}"}
    try:
        cred = resolve_credential(dev.credential_ref)
    except CredentialError as exc:
        return {"ok": False, "error": str(exc)}

    from netmiko import ConnectHandler
    try:
        conn = ConnectHandler(device_type=driver, host=dev.hostname,
                              username=cred.username, password=cred.password or "",
                              secret=cred.enable or "", fast_cli=False,
                              conn_timeout=min(timeout_s, 30))
        lines = [ln for ln in config.splitlines() if ln.strip()]
        out = conn.send_config_set(lines, read_timeout=timeout_s)
        conn.disconnect()
        return {"ok": True, "output": out}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def _structured_diff(before: str, after: str) -> dict:
    """Structured before/after comparison.

    Uses jdiff when the payloads are structured, and a line-set comparison for raw
    config text — which is what `show running-config` actually returns. Either way
    the comparison is of STATE, never of whether a command returned successfully.
    """
    b = {ln.rstrip() for ln in before.splitlines() if ln.strip()}
    a = {ln.rstrip() for ln in after.splitlines() if ln.strip()}
    added, removed = sorted(a - b), sorted(b - a)
    return {"changed": bool(added or removed),
            "added": added[:40], "removed": removed[:40],
            "added_count": len(added), "removed_count": len(removed)}


def _rollback(dev: inv.Device, device: str, baseline: Path, common: dict) -> dict:
    """Attempt rollback to the captured baseline (FR-027).

    A failed rollback HALTS and alerts rather than continuing (Principle VIII):
    the device is in an unknown state and only a human should decide what next.
    """
    _audit("change.rollback.attempt", device=device, baseline=str(baseline))
    text = baseline.read_text()
    if not text.strip():
        _audit("change.rollback.failed", device=device, reason="empty baseline")
        return {"rollback": Stage.ROLLBACK_FAILED.value,
                "rollback_error": "captured baseline is empty; refusing to push it, "
                                  "which would erase the device. HALT — human required."}
    result = _send_config(dev, text, timeout_s=DEFAULT_TIMEOUT)
    if result["ok"]:
        _audit("change.rollback.ok", device=device)
        return {"rollback": Stage.ROLLED_BACK.value}
    _audit("change.rollback.failed", device=device, error=str(result["error"])[:80])
    return {"rollback": Stage.ROLLBACK_FAILED.value,
            "rollback_error": f"{result['error']} — device is in an UNKNOWN state. "
                              f"HALT and alert: baseline is at {baseline}"}
