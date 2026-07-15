#!/usr/bin/env python3
"""iN2N durable-runtime service generator (feature 057, US5/FR-013/014/015).

Makes the mesh daemon and the always-on member claws DURABLE systemd --user
services (Restart=always, survive session/terminal churn + host reboot) — the way
the OpenClaw gateway already runs. Repeatable (a generator), not hand-authored
one-offs: this is the formalization of the 056 netclaw-mesh.service hotfix.

Design (contracts/durable-services.md):
  * ONE unit per always-on member (mirrors the mesh daemon) → independent restart,
    honest per-member `systemctl status`, and trivial single-owner (a member with a
    running unit is NOT cold-started by the Border → no double-launch).
  * The mesh-daemon unit is generated from the checked-in template
    scripts/systemd/netclaw-mesh.service.
  * Always-on members are those provisioned with on_demand=false (a local,
    spawnable member with a launch_cmd). Generating a member's unit BINDS it to
    service management (managed_by=service) so the cold-start path defers to it.
  * Non-systemd hosts: degrade gracefully — write the units and print the
    documented fallback; the daemon's posture reports the durability aspect
    accordingly.

Usage:
  python3 scripts/in2n-services.py generate        # write units for daemon + always-on members
  python3 scripts/in2n-services.py enable          # daemon-reload + enable --now each
  python3 scripts/in2n-services.py status          # per-unit active/failed
  python3 scripts/in2n-services.py disable <name>  # tear a member's unit down
"""

import argparse
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
UNIT_DIR = os.path.join(HOME, ".config", "systemd", "user")
TEMPLATE = os.path.join(REPO, "scripts", "systemd", "netclaw-mesh.service")
DEFENSECLAW_TEMPLATE = os.path.join(REPO, "scripts", "systemd", "defenseclaw-sidecar.service")

sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))


def _slug(member_id: str) -> str:
    return member_id.replace("/", "-")


def _member_path() -> str:
    """Build a PATH for member units that includes wherever the tools actually
    live (openclaw/node under nvm, defenseclaw/openshell under ~/.local/bin) — an
    explicit systemd PATH must not drop them, or the member can't exec openclaw /
    its enforcement CLIs (feature 057)."""
    dirs = []
    for tool in ("openclaw", "node", "defenseclaw", "openshell", "python3"):
        p = shutil.which(tool)
        if p:
            d = os.path.dirname(p)
            if d and d not in dirs:
                dirs.append(d)
    for d in (os.path.join(HOME, ".local", "bin"), "/usr/local/sbin",
              "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin"):
        if d not in dirs:
            dirs.append(d)
    return ":".join(dirs)


def _risk_mode() -> str:
    """The risk's production/testing mode, so member units run production-aware
    (their model I/O guard fires). Reads the env, else the mesh systemd env file."""
    m = os.environ.get("N2N_RISK_MODE")
    if m:
        return m.strip()
    envf = os.path.join(HOME, ".openclaw", "mesh.systemd.env")
    try:
        for line in open(envf):
            if line.startswith("N2N_RISK_MODE="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "testing"


def _unit_name(member_id: str) -> str:
    return f"netclaw-member-{_slug(member_id)}.service"


_full_sandbox_cache = None


def _full_sandbox_supported() -> bool:
    """Can the systemd --user manager apply capability/namespace hardening?
    Under WSL2 it cannot (fails 218/CAPABILITIES), so we detect once by launching a
    throwaway transient unit with a capability-dropping directive."""
    global _full_sandbox_cache
    if _full_sandbox_cache is not None:
        return _full_sandbox_cache
    if not shutil.which("systemd-run"):
        _full_sandbox_cache = False
        return False
    try:
        r = subprocess.run(
            ["systemd-run", "--user", "--wait", "--collect", "--quiet",
             "-p", "ProtectKernelModules=yes", "-p", "RestrictNamespaces=yes",
             "/bin/true"],
            capture_output=True, timeout=20)
        _full_sandbox_cache = (r.returncode == 0)
    except Exception:
        _full_sandbox_cache = False
    return _full_sandbox_cache


def _has_systemctl_user() -> bool:
    if not shutil.which("systemctl"):
        return False
    try:
        r = subprocess.run(["systemctl", "--user", "show-environment"],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def _risk():
    """Open the live federation DB and return (manager, risk_mgr)."""
    from bgp.federation.manager import FederationManager
    from bgp.federation.risk import RiskManager
    base = os.path.expanduser(os.environ.get("N2N_BASE_DIR", "~/.openclaw/n2n"))
    mgr = FederationManager(base_dir=base)
    return mgr, RiskManager(mgr)


def _mesh_unit_text() -> str:
    with open(TEMPLATE) as fh:
        return fh.read().replace("@REPO@", REPO).replace("@HOME@", HOME)


def _defenseclaw_unit_text() -> str:
    """Sidecar unit text with the defenseclaw-gateway path substituted, or None if
    defenseclaw-gateway isn't installed (model-guard optional at the tooling level)."""
    dg = shutil.which("defenseclaw-gateway")
    if not dg:
        return None
    with open(DEFENSECLAW_TEMPLATE) as fh:
        return fh.read().replace("@DGDIR@", os.path.dirname(dg)).replace("@DG@", dg)


def _hardening_block(harden: bool) -> str:
    """Feature 057 US2 sandbox = HOST-LEVEL KERNEL CONFINEMENT via systemd
    sandboxing directives. The member keeps its real scoped home, tools, and
    network (so it actually runs its skills), but with reduced privileges and
    syscall/namespace/filesystem restrictions — a compromised member cannot
    escalate, load kernel modules, use raw sockets, or read the operator's master
    secrets. This is the confinement the OpenShell *container* could not provide
    for a live-infrastructure member (empty container, no tools/network).

    Node's JIT needs W^X, so MemoryDenyWriteExecute is intentionally NOT set.
    Blast-radius note: %h stays writable (the member needs its own state); the
    master ~/.openclaw/.env (all integration secrets) is made inaccessible.
    Per-member filesystem isolation (hiding sibling member homes via
    ProtectHome=tmpfs + binds) is the documented tightening step."""
    if not harden:
        return ""
    # NOTE: capability/namespace directives (ProtectKernelModules, RestrictNamespaces,
    # RestrictAddressFamilies, etc.) require privileges the systemd --user manager
    # lacks under WSL2 (fails 218/CAPABILITIES). We apply the filesystem +
    # no-new-privileges set that works everywhere, and add the capability/namespace
    # hardening only when the manager supports it (detected at generate time). On a
    # native-Linux production host the full set applies; on WSL2 the member is still
    # confined at the filesystem + privilege layer (and the master secrets hidden).
    base = """# ── feature 057: host-level confinement (US2 sandbox) — portable set ──
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=%h
InaccessiblePaths=-%h/.openclaw/.env
"""
    extra = """# ── kernel/namespace confinement (native Linux; skipped where unsupported) ──
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
RestrictNamespaces=yes
LockPersonality=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM
"""
    return base + (extra if _full_sandbox_supported() else "")


def _member_unit_text(member_id: str, launch_cmd: str, harden: bool = True) -> str:
    # launch_cmd is typically `bash <run.sh>` (run.sh sets N2N_MEMBER_ENV_FILE and
    # execs in2n-member.py with the member's own scoped env). Resolve `bash` to an
    # absolute path so systemd accepts ExecStart.
    exec_start = launch_cmd
    parts = launch_cmd.split()
    if parts and parts[0] == "bash":
        exec_start = " ".join([shutil.which("bash") or "/bin/bash", *parts[1:]])
    return f"""[Unit]
Description=NetClaw iN2N member {member_id} — durable + confined, feature 057
After=network-online.target netclaw-mesh.service
Wants=netclaw-mesh.service

[Service]
Type=simple
WorkingDirectory={REPO}
Environment=N2N_RISK_MODE={_risk_mode()}
# Include the dirs where openclaw/node (nvm) + defenseclaw/openshell (~/.local/bin)
# actually live — a confined member with an explicit PATH must still find them,
# or it can't exec openclaw / its enforcement CLIs (feature 057).
Environment=PATH={_member_path()}
ExecStart={exec_start}
Restart=always
RestartSec=5
{_hardening_block(harden)}
[Install]
WantedBy=default.target
"""


def _always_on_members(risk) -> list:
    """Local, spawnable, always-on members (on_demand=false with a launch_cmd)."""
    out = []
    for m in risk.list_members():
        launch_cmd = m.get("launch_cmd")
        if launch_cmd and not m.get("on_demand"):
            out.append((m["member_id"], launch_cmd))
    return out


def cmd_generate(args) -> int:
    os.makedirs(UNIT_DIR, exist_ok=True)
    written = []
    # 1. mesh daemon unit (from the checked-in template)
    mesh_path = os.path.join(UNIT_DIR, "netclaw-mesh.service")
    with open(mesh_path, "w") as fh:
        fh.write(_mesh_unit_text())
    written.append("netclaw-mesh.service")
    # 2. DefenseClaw guardrail sidecar (model-guard proxy) — durable so production
    #    posture stays enforced across reboot (feature 057). Skipped if not installed.
    dc_text = _defenseclaw_unit_text()
    if dc_text:
        with open(os.path.join(UNIT_DIR, "defenseclaw-sidecar.service"), "w") as fh:
            fh.write(dc_text)
        written.append("defenseclaw-sidecar.service")
    # 3. one unit per always-on member (binds it to service management)
    mgr, risk = _risk()
    try:
        for member_id, launch_cmd in _always_on_members(risk):
            unit = _unit_name(member_id)
            with open(os.path.join(UNIT_DIR, unit), "w") as fh:
                fh.write(_member_unit_text(member_id, launch_cmd))
            risk.set_managed_by(member_id, "service", service_unit=unit)
            written.append(unit)
    finally:
        mgr.close()
    print("Generated units in %s:" % UNIT_DIR)
    for u in written:
        print("  -", u)
    if not _has_systemctl_user():
        print("\nNOTE: `systemctl --user` is not available on this host. Units were "
              "written but NOT enabled. The risk posture will report the durable-"
              "runtime aspect as degraded; run the daemon/members via your platform's "
              "service manager (documented fallback).")
    else:
        print("\nNext: python3 scripts/in2n-services.py enable")
    return 0


def cmd_enable(args) -> int:
    if not _has_systemctl_user():
        print("systemctl --user unavailable — cannot enable (see `generate` note).")
        return 1
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    units = ["netclaw-mesh.service"]
    if _defenseclaw_unit_text():
        units.append("defenseclaw-sidecar.service")
    mgr, risk = _risk()
    try:
        units += [_unit_name(mid) for mid, _ in _always_on_members(risk)]
    finally:
        mgr.close()
    rc = 0
    for u in units:
        r = subprocess.run(["systemctl", "--user", "enable", "--now", u])
        print(("enabled " if r.returncode == 0 else "FAILED  ") + u)
        rc = rc or r.returncode
    return rc


def cmd_status(args) -> int:
    if not _has_systemctl_user():
        print("systemctl --user unavailable.")
        return 1
    units = ["netclaw-mesh.service"]
    if _defenseclaw_unit_text():
        units.append("defenseclaw-sidecar.service")
    mgr, risk = _risk()
    try:
        units += [_unit_name(mid) for mid, _ in _always_on_members(risk)]
    finally:
        mgr.close()
    for u in units:
        r = subprocess.run(["systemctl", "--user", "is-active", u],
                           capture_output=True, text=True)
        print(f"{r.stdout.strip() or 'unknown':10} {u}")
    return 0


def cmd_disable(args) -> int:
    member_id = args.member if "/" in args.member else None
    mgr, risk = _risk()
    try:
        if member_id is None:
            # accept a bare name → resolve against the risk
            r = risk.get_risk()
            member_id = f"{r.get('risk_name')}/{args.member}"
        unit = risk.service_unit(member_id) or _unit_name(member_id)
        if _has_systemctl_user():
            subprocess.run(["systemctl", "--user", "disable", "--now", unit])
        path = os.path.join(UNIT_DIR, unit)
        if os.path.exists(path):
            os.remove(path)
        risk.set_managed_by(member_id, "cold")
        print(f"disabled + removed {unit}; {member_id} reverts to cold-start")
    finally:
        mgr.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="iN2N durable-runtime service generator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate")
    sub.add_parser("enable")
    sub.add_parser("status")
    d = sub.add_parser("disable")
    d.add_argument("member", help="member id (<risk>/<name>) or bare name")
    args = ap.parse_args()
    return {"generate": cmd_generate, "enable": cmd_enable,
            "status": cmd_status, "disable": cmd_disable}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
