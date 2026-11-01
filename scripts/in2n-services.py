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

  --system (spec 165, any command): member units become system-manager units with
  User=/Group= under /etc/systemd/system and the full hardening — for OpenClaw
  releases that cannot run inside mount-namespaced user units. Installed and
  managed only through `sudo -n`; if that needs a password the exact commands are
  printed instead. The mesh daemon (and DefenseClaw sidecar) stay user scope.
  Run it as the operator user, never as root.

  coldstart install|remove|status (spec 166): on-demand members cannot use the
  user-scope `systemd-run` cold-start on those OpenClaw releases either. `install`
  puts a hardened system template unit (netclaw-coldmember@.service, User= the
  operator) and a polkit rule letting ONLY the operator start/stop ONLY instances
  of that template, so the Border cold-starts on-demand members as confined system
  instances without sudo. Same `sudo -n` handling; never run as root.
"""

import argparse
import grp
import hashlib
import json
from pathlib import Path
import os
import pwd
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
UNIT_DIR = os.path.join(HOME, ".config", "systemd", "user")
SYSTEM_UNIT_DIR = "/etc/systemd/system"
POLKIT_RULES_DIR = "/etc/polkit-1/rules.d"
# Spec 166: system template for on-demand members + its narrow polkit rule.
COLDSTART_UNIT = "netclaw-coldmember@.service"
COLDSTART_PROBE_UNIT = "netclaw-coldmember@probe.service"   # reserved no-op instance
COLDSTART_LAUNCHER = os.path.join(REPO, "scripts", "in2n-coldstart.py")
# Embedded verbatim in the polkit rule (JavaScript); conservative so no quoting
# question arises. Matches the instance names in2n-coldstart.py accepts.
_SAFE_USER = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,31}")
TEMPLATE = os.path.join(REPO, "scripts", "systemd", "netclaw-mesh.service")
DEFENSECLAW_TEMPLATE = os.path.join(REPO, "scripts", "systemd", "defenseclaw-sidecar.service")

sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))


def _runtime():
    from bgp.federation.runtime import selected
    return selected()


def _suffix():
    runtime=_runtime()
    return '' if runtime.kind=='openclaw' and str(runtime.home)==str(Path(HOME)/'.openclaw') else '-'+hashlib.sha256(str(runtime.home).encode()).hexdigest()[:10]


def _mesh_name():return 'netclaw-mesh'+_suffix()+'.service'


def _quote(value):return json.dumps(str(value).replace('%','%%'))


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
    envf = str(_runtime().home/"mesh.systemd.env")
    try:
        for line in open(envf):
            if line.startswith("N2N_RISK_MODE="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "testing"


def _unit_name(member_id: str) -> str:
    return f"netclaw-member-{_slug(member_id)}{_suffix()}.service"


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


def _base_dir() -> str:
    """The federation DB directory (N2N_BASE_DIR, else the selected runtime's)."""
    return os.path.expanduser(os.environ.get("N2N_BASE_DIR", str(_runtime().base)))


def _risk():
    """Open the live federation DB and return (manager, risk_mgr)."""
    from bgp.federation.manager import FederationManager
    from bgp.federation.risk import RiskManager
    mgr = FederationManager(base_dir=_base_dir())
    return mgr, RiskManager(mgr)


def _n2n_python() -> str:
    """The n2n interpreter from the runtime records, else this one."""
    record=_runtime().home/'python-runtimes/records/n2n'
    return record.read_text().strip() if record.exists() else sys.executable


def _mesh_unit_text() -> str:
    runtime=_runtime()
    python=_n2n_python()
    with open(TEMPLATE) as fh:text=fh.read()
    environment='\n'.join('Environment='+_quote(k+'='+v) for k,v in runtime.environment({}).items())
    return text.replace('@REPO@',REPO).replace('@HOME@',HOME).replace('@RUNTIME_ENV@',_quote(runtime.home/'mesh.systemd.env')).replace('@PYTHON@',_quote(python)).replace('@SELECTION@',environment)


def _defenseclaw_unit_text() -> str:
    """Sidecar unit text with the defenseclaw-gateway path substituted, or None if
    defenseclaw-gateway isn't installed (model-guard optional at the tooling level)."""
    dg = shutil.which("defenseclaw-gateway")
    if not dg:
        return None
    with open(DEFENSECLAW_TEMPLATE) as fh:
        return fh.read().replace("@DGDIR@", os.path.dirname(dg)).replace("@DG@", dg)


def _hardening_block(harden: bool, system: bool = False) -> str:
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
@BORDER_SECRETS@
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
    runtime=_runtime()
    protected='InaccessiblePaths=-'+_quote(runtime.env_file)+' -'+_quote(runtime.config)+' -'+_quote(runtime.home/'netclaw-hud')+' -'+_quote(runtime.state)
    if system:
        # The system manager supports the full set, and resolves %h to /root
        # whatever User= says, so the literal home is pinned (spec 165).
        return base.replace('%h',_quote(HOME)).replace('@BORDER_SECRETS@',protected) + extra
    return base.replace('@BORDER_SECRETS@',protected) + (extra if _full_sandbox_supported() else '')


def _member_unit_text(member_id: str, launch_cmd: str, harden: bool = True, system: bool = False) -> str:
    # launch_cmd is typically `bash <run.sh>` (run.sh sets N2N_MEMBER_ENV_FILE and
    # execs in2n-member.py with the member's own scoped env). Resolve `bash` to an
    # absolute path so systemd accepts ExecStart.
    exec_start = launch_cmd
    parts = launch_cmd.split()
    if parts and parts[0] == "bash":
        exec_start = " ".join([shutil.which("bash") or "/bin/bash", *parts[1:]])
    order, identity, target = f"After=network-online.target {_mesh_name()}\nWants={_mesh_name()}", "", "default.target"
    if system:
        # A system unit cannot order after or want the user manager's mesh unit.
        order, target = "After=network-online.target", "multi-user.target"
        identity = _system_identity()
    return f"""[Unit]
Description=NetClaw iN2N member {member_id} — durable + confined, feature 057
{order}

[Service]
Type=simple
{identity}WorkingDirectory={REPO}
Environment=N2N_RISK_MODE={_risk_mode()}
# Include the dirs where openclaw/node (nvm) + defenseclaw/openshell (~/.local/bin)
# actually live — a confined member with an explicit PATH must still find them,
# or it can't exec openclaw / its enforcement CLIs (feature 057).
Environment={_quote('PATH='+_member_path())}
ExecStart={exec_start}
Restart=always
RestartSec=5
{_hardening_block(harden, system)}
[Install]
WantedBy={target}
"""


def _system_identity() -> str:
    """User=/Group=/HOME lines that run a system unit as the invoking operator."""
    user = pwd.getpwuid(os.getuid())
    return f"User={user.pw_name}\nGroup={grp.getgrgid(user.pw_gid).gr_name}\nEnvironment={_quote('HOME='+HOME)}\n"


def _always_on_members(risk) -> list:
    """Local, spawnable, always-on members (on_demand=false with a launch_cmd)."""
    out = []
    for m in risk.list_members():
        launch_cmd = m.get("launch_cmd")
        if launch_cmd and not m.get("on_demand"):
            out.append((m["member_id"], launch_cmd))
    return out


def _sudo_run(argv) -> int:
    """One privileged command through `sudo -n` (never prompts)."""
    try:
        return subprocess.run(["sudo", "-n", *argv], check=False).returncode
    except FileNotFoundError:
        return 127


def _print_manual(rc, cmds):
    print(f"\nsudo -n failed (exit {rc}). Run `sudo -v` and retry, or run as an administrator:")
    for a in cmds:
        print("  sudo " + shlex.join(a))


def _sudo(cmds) -> int:
    """Run each privileged command through `sudo -n` (never prompts). On a failure
    print the commands not yet run, for the operator, and return non-zero."""
    for i, argv in enumerate(cmds):
        rc = _sudo_run(argv)
        if rc:
            _print_manual(rc, cmds[i:])
            return rc
    return 0


def _install_system_units(units) -> int:
    """Stage each unit in a private temp dir, then `sudo -n install` it. Every unit
    is attempted; on any failure the units that did install are still
    daemon-reloaded, and exactly which were / were not installed is printed with the
    remaining commands. The staging dir is kept on failure so those still work."""
    stage = tempfile.mkdtemp(prefix="netclaw-system-units-")
    installed, missing, rc = [], [], 0
    for unit, text in units:
        with open(os.path.join(stage, unit), "w") as fh:
            fh.write(text)
    for unit, _ in units:
        cmd = ["install", "-m", "0644", os.path.join(stage, unit), os.path.join(SYSTEM_UNIT_DIR, unit)]
        code = _sudo_run(cmd)
        if code:
            rc = rc or code
            missing.append((unit, cmd))
        else:
            installed.append(unit)
    reload = ["systemctl", "daemon-reload"]
    reload_rc = _sudo_run(reload) if installed else 0
    if not missing and not reload_rc:
        shutil.rmtree(stage, ignore_errors=True)
        return 0
    print(f"\nInstalled in {SYSTEM_UNIT_DIR}: " + (", ".join(installed) or "none"))
    print("NOT installed: " + (", ".join(u for u, _ in missing) or "none"))
    if installed:
        print("daemon-reload of the installed units: " + (f"FAILED (exit {reload_rc})" if reload_rc else "done"))
    _print_manual(rc or reload_rc, [c for _, c in missing] + [reload])
    return rc or reload_rc


def _system_active(unit) -> bool:
    return all(subprocess.run(["systemctl", verb, "--quiet", unit], check=False).returncode == 0
               for verb in ("is-enabled", "is-active"))


def cmd_generate(args) -> int:
    system = getattr(args, "system", False)
    os.makedirs(UNIT_DIR, exist_ok=True)
    written = []
    # 1. mesh daemon unit (from the checked-in template)
    mesh_path = os.path.join(UNIT_DIR, _mesh_name())
    with open(mesh_path, "w") as fh:
        fh.write(_mesh_unit_text())
    written.append(_mesh_name())
    # 2. DefenseClaw guardrail sidecar (model-guard proxy) — durable so production
    #    posture stays enforced across reboot (feature 057). Skipped if not installed.
    dc_text = _defenseclaw_unit_text()
    if dc_text:
        with open(os.path.join(UNIT_DIR, "defenseclaw-sidecar.service"), "w") as fh:
            fh.write(dc_text)
        written.append("defenseclaw-sidecar.service")
    # 3. one unit per always-on member (binds it to service management)
    mgr, risk = _risk()
    staged = []
    try:
        for member_id, launch_cmd in _always_on_members(risk):
            unit = _unit_name(member_id)
            if system:
                staged.append((unit, _member_unit_text(member_id, launch_cmd, system=True)))
                continue
            with open(os.path.join(UNIT_DIR, unit), "w") as fh:
                fh.write(_member_unit_text(member_id, launch_cmd))
            # Generated files alone do not establish an active service owner.
            # Binding occurs only after enable --now succeeds.
            written.append(unit)
    finally:
        mgr.close()
    failed = bool(staged) and _install_system_units(staged)
    print("Generated units in %s:" % UNIT_DIR)
    for u in written:
        print("  -", u)
    if failed:
        return 1
    if system:
        print(f"Installed system units in {SYSTEM_UNIT_DIR}:")
        for u, _ in staged:
            print("  -", u)
            if os.path.exists(os.path.join(UNIT_DIR, u)):
                # `disable <member>` now refuses while the system unit exists.
                print("    NOTE: a user-scope copy remains; remove it before enabling: "
                      f"systemctl --user disable --now {u} && rm {shlex.quote(os.path.join(UNIT_DIR, u))}")
    if not _has_systemctl_user():
        print("\nNOTE: `systemctl --user` is not available on this host. Units were "
              "written but NOT enabled. The risk posture will report the durable-"
              "runtime aspect as degraded; run the daemon/members via your platform's "
              "service manager (documented fallback).")
    else:
        print("\nNext: python3 scripts/in2n-services.py enable" + (" --system" if system else ""))
    return 0


def cmd_enable(args) -> int:
    system = getattr(args, "system", False)
    if not _has_systemctl_user():
        print("systemctl --user unavailable — cannot enable (see `generate` note).")
        return 1
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    units = [_mesh_name()]
    if _defenseclaw_unit_text():
        units.append("defenseclaw-sidecar.service")
    mgr, risk = _risk()
    try:
        units += [_unit_name(mid) for mid, _ in _always_on_members(risk)]
    finally:
        mgr.close()
    rc = 0
    for u in units:
        if system and u.startswith('netclaw-member-'):
            # Already enabled + active (e.g. the operator ran the printed sudo
            # commands): bind without sudo.
            code = 0 if _system_active(u) else _sudo([["systemctl", "enable", "--now", u]])
        else:
            code = subprocess.run(["systemctl", "--user", "enable", "--now", u]).returncode
        print(("enabled " if code == 0 else "FAILED  ") + u)
        if code==0 and u.startswith('netclaw-member-'):
            mgr,risk=_risk()
            try:
                for member_id,_ in _always_on_members(risk):
                    if _unit_name(member_id)==u:risk.set_managed_by(member_id,'service',service_unit=u)
            finally:mgr.close()
        rc = rc or code
    return rc


def cmd_status(args) -> int:
    if not _has_systemctl_user():
        print("systemctl --user unavailable.")
        return 1
    units = [_mesh_name()]
    if _defenseclaw_unit_text():
        units.append("defenseclaw-sidecar.service")
    mgr, risk = _risk()
    try:
        units += [_unit_name(mid) for mid, _ in _always_on_members(risk)]
    finally:
        mgr.close()
    system = getattr(args, "system", False)
    for u in units:
        scope = [] if system and u.startswith("netclaw-member-") else ["--user"]
        r = subprocess.run(["systemctl", *scope, "is-active", u],
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
        system_path = os.path.join(SYSTEM_UNIT_DIR, unit)
        if getattr(args, "system", False):
            if os.path.exists(system_path):
                cmds = [["systemctl", "disable", "--now", unit], ["rm", "-f", system_path]]
            else:
                # Unit file already removed (e.g. by hand): undo only what is left —
                # a still-running unit and a dangling enablement link. No sudo if
                # nothing needs root.
                cmds = []
                if subprocess.run(["systemctl", "is-active", "--quiet", unit], check=False).returncode == 0:
                    cmds.append(["systemctl", "stop", unit])
                wants = os.path.join(SYSTEM_UNIT_DIR, "multi-user.target.wants", unit)
                if os.path.lexists(wants):
                    cmds.append(["rm", "-f", wants])
                if not cmds:
                    print(f"{system_path} already absent; nothing to remove")
            # Stay service-managed unless the system unit is really gone.
            if cmds and _sudo(cmds + [["systemctl", "daemon-reload"]]):
                return 1
        elif os.path.exists(system_path):
            # A user-scope disable cannot stop a system unit; reverting to cold
            # here would let the cold-start path double-launch the member.
            print(f"{unit} is a system unit ({system_path}); use: "
                  f"python3 scripts/in2n-services.py disable --system {args.member}")
            return 1
        else:
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


# ---- spec 166: confined system cold-start of on-demand members -------------

def _coldstart_unit_text() -> str:
    """System template for on-demand members, started per instance by the Border
    (`systemctl start --no-block netclaw-coldmember@<member-slug>.service`). The
    instance launcher resolves %i against the Risk registry and execs only a
    registered on-demand member's launch command — never an argument from the
    unit name. Runs as the operator with the spec 165 system hardening; Restart=no
    because an on-demand member idle-exits and is cold-started again on the next
    route. No [Install] section: instances are only ever started on demand."""
    launcher = " ".join([_quote(_n2n_python()), _quote(COLDSTART_LAUNCHER), "%i"])
    return f"""[Unit]
Description=NetClaw iN2N on-demand member %i — confined system cold-start, spec 166
After=network-online.target

[Service]
Type=simple
{_system_identity()}WorkingDirectory={REPO}
Environment=N2N_RISK_MODE={_risk_mode()}
Environment={_quote('PATH='+_member_path())}
# The launcher's Risk registry (removed from the member's environment before exec).
Environment={_quote('NETCLAW_COLDSTART_BASE_DIR='+_base_dir())}
ExecStart={launcher}
Restart=no
{_hardening_block(True, system=True)}"""


def _coldstart_rule_name(user: str) -> str:
    return f"60-netclaw-coldmember-{user}.rules"


def _coldstart_rule_text(user: str) -> str:
    """polkit rule: the operator may start/stop instances of the cold-start
    template and nothing else. Anything not matched returns no result, so other
    rules / the auth_admin default still apply (no blanket grant)."""
    if not _SAFE_USER.fullmatch(user or ""):
        raise ValueError(f"refusing to write a polkit rule for unsafe user name {user!r}")
    template = os.path.join(SYSTEM_UNIT_DIR, COLDSTART_UNIT)
    test_bin = "/usr/bin/test" if os.path.exists("/usr/bin/test") else "/bin/test"
    # systemd 257+ also asks manage-units/verb "start" with the requested name for
    # StartTransientUnit. A transient unit cannot reuse a name that has a unit file,
    # so the grant is only safe while the template exists: re-check it every time.
    return f"""// NetClaw spec 166 (scripts/in2n-services.py coldstart install): lets {user} start
// and stop instances of the confined system template netclaw-coldmember@.service,
// so the Border cold-starts on-demand members without sudo. Nothing else is granted.
// The grant requires the template file to exist (it blocks transient units of the
// same name on systemd 257+); without it the rule returns no result.
polkit.addRule(function(action, subject) {{
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        subject.user == {json.dumps(user)}) {{
        var unit = action.lookup("unit");
        var verb = action.lookup("verb");
        if (typeof unit == "string" &&
            /^netclaw-coldmember@[A-Za-z0-9_.-]+\\.service$/.test(unit) &&
            (verb == "start" || verb == "stop")) {{
            try {{
                polkit.spawn([{json.dumps(test_bin)}, "-f", {json.dumps(template)}]);
            }} catch (error) {{
                return;
            }}
            return polkit.Result.YES;
        }}
    }}
}});
"""


def _coldstart_paths(user: str):
    return (os.path.join(SYSTEM_UNIT_DIR, COLDSTART_UNIT),
            os.path.join(POLKIT_RULES_DIR, _coldstart_rule_name(user)))


def _coldstart_install(user: str) -> int:
    """Stage the template + rule privately and `sudo -n install` them in order:
    template, daemon-reload, and only then the rule, so the rule never exists
    without the template (see _coldstart_rule_text). The first failure stops the
    install, reports what was installed, prints the remaining commands and keeps
    the staging directory."""
    try:
        files = [(COLDSTART_UNIT, _coldstart_unit_text()),
                 (_coldstart_rule_name(user), _coldstart_rule_text(user))]
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    stage = tempfile.mkdtemp(prefix="netclaw-coldstart-")    # 0700
    (unit_name, unit_text), (rule_name, rule_text) = files
    unit_dest, rule_dest = _coldstart_paths(user)
    steps = []
    for name, text, dest in ((unit_name, unit_text, unit_dest), (rule_name, rule_text, rule_dest)):
        src = os.path.join(stage, name)
        with open(src, "w") as fh:
            fh.write(text)
        steps.append((dest, ["install", "-m", "0644", src, dest]))
    steps.insert(1, (None, ["systemctl", "daemon-reload"]))
    # A reinstall replaces the template (install unlinks then recreates it): drop any
    # loaded rule first so it is never live while the template is momentarily absent.
    steps.insert(0, (None, ["rm", "-f", rule_dest]))
    installed = []
    for i, (dest, cmd) in enumerate(steps):
        code = _sudo_run(cmd)
        if code:
            print("\nInstalled: " + (", ".join(installed) or "none"))
            print("NOT installed: " + (", ".join(d for d, _ in steps[i:] if d) or "none")
                  + (f" ({cmd[0]} {cmd[1]} FAILED)" if dest is None else ""))
            print("The polkit rule is installed only after the template and daemon-reload "
                  "succeed. Run the commands below in order and stop at the first error.")
            _print_manual(code, [c for _, c in steps[i:]])
            return code
        if dest:
            installed.append(dest)
    shutil.rmtree(stage, ignore_errors=True)
    print("Installed:\n  - " + "\n  - ".join(installed))
    print("\nNext: python3 scripts/in2n-services.py coldstart status")
    return 0


def _coldstart_remove(user: str) -> int:
    """Delete the template and rule (rm -f: an absent file is fine — the rules
    directory is not readable by the operator, so presence is not checked)."""
    if not _SAFE_USER.fullmatch(user or ""):
        print(f"refusing unsafe user name {user!r}", file=sys.stderr)
        return 1
    unit, rule = _coldstart_paths(user)
    # Rule first: the grant must never outlive the template (see _coldstart_rule_text).
    if _sudo([["rm", "-f", rule], ["rm", "-f", unit], ["systemctl", "daemon-reload"]]):
        return 1
    print(f"removed {unit} and {rule} (if present)")
    print("Running instances keep running until their member idle-exits; to stop them now: "
          "sudo systemctl stop 'netclaw-coldmember@*.service'")
    return 0


def _coldstart_probe():
    """Start the reserved no-op instance as the operator, without sudo and
    without a password prompt: succeeds only if the polkit rule authorizes us."""
    try:
        r = subprocess.run(["systemctl", "--no-ask-password", "start", COLDSTART_PROBE_UNIT],
                           capture_output=True, text=True, timeout=30, check=False)
        return r.returncode, (r.stderr or r.stdout or "").strip()
    except FileNotFoundError:
        return 127, "systemctl not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"


def _coldstart_status() -> int:
    unit = os.path.join(SYSTEM_UNIT_DIR, COLDSTART_UNIT)
    if not os.path.exists(unit):
        print(f"template: missing ({unit}); authorization probe not run")
        print("install: python3 scripts/in2n-services.py coldstart install")
        return 1
    print(f"template: installed ({unit})")
    rc, out = _coldstart_probe()
    if rc == 0:
        print(f"authorization probe: authorized (started {COLDSTART_PROBE_UNIT})")
        return 0
    print(f"authorization probe: NOT authorized (exit {rc}): {out or 'no output'}")
    print("the polkit rule is missing or does not match this user; rerun: "
          "python3 scripts/in2n-services.py coldstart install")
    return 1


def cmd_coldstart(args) -> int:
    user = pwd.getpwuid(os.getuid()).pw_name
    if args.action == "install":
        return _coldstart_install(user)
    if args.action == "remove":
        return _coldstart_remove(user)
    return _coldstart_status()


def main() -> int:
    ap = argparse.ArgumentParser(description="iN2N durable-runtime service generator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    parsers = [sub.add_parser(name) for name in ("generate", "enable", "status", "disable")]
    parsers[3].add_argument("member", help="member id (<risk>/<name>) or bare name")
    for p in parsers:
        p.add_argument("--system", action="store_true",
                       help="member units in the system manager via sudo -n (spec 165)")
    cold = sub.add_parser("coldstart", help="system cold-start template + polkit rule for "
                                            "on-demand members (spec 166; system scope)")
    cold.add_argument("action", choices=("install", "remove", "status"))
    args = ap.parse_args()
    if (getattr(args, "system", False) or args.cmd == "coldstart") and os.geteuid() == 0:
        # User=/HOME and the user-scope mesh unit come from the invoking account.
        print(("--system" if args.cmd != "coldstart" else "coldstart") +
              " must be run as the operator user, not root; it uses sudo -n itself "
              "for the privileged steps.", file=sys.stderr)
        return 1
    return {"generate": cmd_generate, "enable": cmd_enable, "status": cmd_status,
            "disable": cmd_disable, "coldstart": cmd_coldstart}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
