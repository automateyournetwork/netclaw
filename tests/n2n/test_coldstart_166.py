"""Spec 166: confined system cold-start of on-demand members — the template unit +
narrow polkit rule (`in2n-services.py coldstart`), the instance launcher
(`in2n-coldstart.py`), the controls probe/argv and the production cold-start path.
systemctl/sudo/polkit are stubbed — no root, systemd or polkit required."""

import asyncio
import grp
import importlib.util
import json
import os
import pwd
import subprocess
import sys
import time
import types

import pytest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))

from bgp.federation import controls

PROBE = ["systemctl", "--no-ask-password", "start", "netclaw-coldmember@probe.service"]
SYSTEM_ARGV = ["systemctl", "start", "--no-block", "--no-ask-password",
               "netclaw-coldmember@risk-viz.service"]
REGEX = r"/^netclaw-coldmember@[A-Za-z0-9_.-]+\.service$/"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, "scripts", path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _fresh_controls():
    controls.invalidate_cache()
    yield
    controls.invalidate_cache()


# ---- in2n-services.py coldstart ------------------------------------------

def _services(monkeypatch, tmp_path):
    monkeypatch.setenv("NETCLAW_RUNTIME", "openclaw")
    monkeypatch.setenv("OPENCLAW_HOME", str(tmp_path / "oc"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    monkeypatch.setenv("N2N_BASE_DIR", str(tmp_path / "base"))
    mod = _load("in2n_services_166", "in2n-services.py")
    mod.SYSTEM_UNIT_DIR = str(tmp_path / "etc")
    mod.POLKIT_RULES_DIR = str(tmp_path / "polkit")
    os.makedirs(mod.SYSTEM_UNIT_DIR)
    mod._full_sandbox_cache = False
    mod._risk = lambda: pytest.fail("coldstart must not open the risk registry")
    return mod


def _fake_run(monkeypatch, fail=lambda argv: 0, probe_rc=0):
    calls, staged = [], {}
    def run(argv, *a, **k):
        calls.append(list(argv))
        if argv[:3] == ["sudo", "-n", "install"]:
            with open(argv[-2]) as fh:
                staged[argv[-1]] = fh.read()
        if argv[0] == "sudo":
            return subprocess.CompletedProcess(argv, fail(argv))
        if argv == PROBE:
            return subprocess.CompletedProcess(argv, probe_rc, stdout="",
                                               stderr="" if not probe_rc else "Access denied")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", run)
    return calls, staged


def _me():
    return pwd.getpwuid(os.getuid()).pw_name


def test_template_text_identity_hardening_and_launcher(monkeypatch, tmp_path):
    svc = _services(monkeypatch, tmp_path)
    record = tmp_path / "oc" / "python-runtimes" / "records" / "n2n"
    record.parent.mkdir(parents=True)
    record.write_text("/opt/n2n venv/bin/python\n")
    text = svc._coldstart_unit_text()
    user = pwd.getpwuid(os.getuid())
    assert "Description=NetClaw iN2N on-demand member %i" in text
    assert "After=network-online.target\n" in text and "netclaw-mesh" not in text
    assert "Type=simple\n" in text and "Restart=no\n" in text and "Restart=always" not in text
    assert f"User={user.pw_name}\n" in text
    assert f"Group={grp.getgrgid(user.pw_gid).gr_name}\n" in text
    assert f'Environment="HOME={svc.HOME}"\n' in text
    assert f"WorkingDirectory={svc.REPO}\n" in text
    assert "Environment=N2N_RISK_MODE=production\n" in text
    assert 'Environment="PATH=' in text and "Environment=PATH=" not in text
    assert f'Environment="NETCLAW_COLDSTART_BASE_DIR={tmp_path / "base"}"\n' in text
    launcher = os.path.join(svc.REPO, "scripts", "in2n-coldstart.py")
    assert f'ExecStart="/opt/n2n venv/bin/python" "{launcher}" %i\n' in text
    for d in ("NoNewPrivileges=yes", "PrivateTmp=yes", "ProtectSystem=strict",
              "ProtectKernelTunables=yes", "ProtectKernelModules=yes", "ProtectControlGroups=yes",
              "RestrictSUIDSGID=yes", "RestrictNamespaces=yes", "LockPersonality=yes",
              "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6",
              "SystemCallFilter=@system-service", "SystemCallErrorNumber=EPERM",
              f'ReadWritePaths="{svc.HOME}"', "InaccessiblePaths=-"):
        assert d in text
    # the system manager resolves %h to /root: only literal home paths
    assert "%h" not in text and "[Install]" not in text and "WantedBy" not in text
    # identical hardening to a --system member unit
    member = svc._member_unit_text("risk/cml", "bash /x/run.sh", system=True)
    assert text[text.index("# ── feature 057"):] == member[member.index("# ── feature 057"):member.index("\n[Install]")]


def test_template_falls_back_to_this_interpreter(monkeypatch, tmp_path):
    svc = _services(monkeypatch, tmp_path)
    assert f'ExecStart="{sys.executable}" ' in svc._coldstart_unit_text()


def test_polkit_rule_text_is_narrow(monkeypatch, tmp_path):
    svc = _services(monkeypatch, tmp_path)
    rule = svc._coldstart_rule_text("op_er.1")
    assert 'action.id == "org.freedesktop.systemd1.manage-units"' in rule
    assert 'subject.user == "op_er.1"' in rule
    assert REGEX + ".test(unit)" in rule
    assert '(verb == "start" || verb == "stop")' in rule
    assert rule.count("polkit.Result.") == 1 and rule.count("return ") == 1
    # systemd 257+ authorizes StartTransientUnit by name: grant only while the
    # template exists (it blocks a transient unit of the same name).
    template = os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-coldmember@.service")
    spawn = f'polkit.spawn([{json.dumps("/usr/bin/test" if os.path.exists("/usr/bin/test") else "/bin/test")}, "-f", {json.dumps(template)}]);'
    assert spawn in rule
    assert rule.index("try {") < rule.index(spawn) < rule.index("} catch (error) {") \
        < rule.index("return;") < rule.index("return polkit.Result.YES")
    assert rule.count("action.id") == 1 and rule.count("verb ==") == 2
    for other in ("restart", "enable", "reload", "mask", "AUTH_", "subject.isInGroup",
                  "manage-unit-files", "Result.NO"):
        assert other not in rule
    assert svc._coldstart_rule_name("op_er.1") == "60-netclaw-coldmember-op_er.1.rules"


@pytest.mark.parametrize("user", ["", "-x", "a\"b", "a b", "a;b", "a/b", "../x", "a\\b",
                                  "x" * 33, "1abc", "user\n"])
def test_polkit_rule_refuses_unsafe_user(monkeypatch, tmp_path, user):
    svc = _services(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        svc._coldstart_rule_text(user)
    calls, _ = _fake_run(monkeypatch)
    assert svc._coldstart_install(user) == 1
    assert svc._coldstart_remove(user) == 1
    assert calls == []


def test_install_through_sudo_n(monkeypatch, tmp_path, capsys):
    svc = _services(monkeypatch, tmp_path)
    calls, staged = _fake_run(monkeypatch)
    assert svc.cmd_coldstart(types.SimpleNamespace(action="install")) == 0
    unit = os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-coldmember@.service")
    rule = os.path.join(svc.POLKIT_RULES_DIR, f"60-netclaw-coldmember-{_me()}.rules")
    install = [c for c in calls if c[:3] == ["sudo", "-n", "install"]]
    assert [c[3:5] for c in install] == [["-m", "0644"]] * 2
    assert [c[-1] for c in install] == [unit, rule]
    # Old rule removed, template, daemon-reload, then the rule: the rule is never live
    # while the template is absent (including during a reinstall).
    assert calls[0] == ["sudo", "-n", "rm", "-f", rule]
    assert calls[1] == install[0] and calls[2] == ["sudo", "-n", "systemctl", "daemon-reload"]
    assert calls[3] == install[1] and len(calls) == 4
    assert staged[unit] == svc._coldstart_unit_text()
    assert staged[rule] == svc._coldstart_rule_text(_me())
    assert not os.path.exists(os.path.dirname(install[0][-2]))   # staging removed
    assert "coldstart status" in capsys.readouterr().out


def test_install_sudo_failure_prints_commands_and_keeps_staging(monkeypatch, tmp_path, capsys):
    svc = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch, fail=lambda argv: 1)
    assert svc.cmd_coldstart(types.SimpleNamespace(action="install")) != 0
    out = capsys.readouterr().out
    assert "Installed: none" in out and "NOT installed: " in out
    manual = [line for line in out.splitlines() if line.startswith("  sudo ")]
    assert len(calls) == 1                                          # first failure stops
    unit = os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-coldmember@.service")
    rule = os.path.join(svc.POLKIT_RULES_DIR, f"60-netclaw-coldmember-{_me()}.rules")
    assert manual[0] == f"  sudo rm -f {rule}"
    assert manual[1].startswith("  sudo install -m 0644 ") and manual[1].endswith(" " + unit)
    assert manual[2] == "  sudo systemctl daemon-reload"
    assert manual[3].startswith("  sudo install -m 0644 ") and manual[3].endswith(".rules")
    srcs = [manual[1].split()[4], manual[3].split()[4]]
    assert all(os.path.exists(x) for x in srcs)                     # kept for the printed commands
    assert "stop at the first error" in out
    assert os.stat(os.path.dirname(srcs[0])).st_mode & 0o077 == 0
    assert all(c[:2] == ["sudo", "-n"] for c in calls)            # never interactive sudo
    assert ["sudo", "-n", "systemctl", "daemon-reload"] not in calls   # nothing installed


def test_install_partial_reloads_template_and_reports_rule(monkeypatch, tmp_path, capsys):
    svc = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch, fail=lambda argv: 1 if argv[2] == "install"
                         and argv[-1].endswith(".rules") else 0)
    assert svc.cmd_coldstart(types.SimpleNamespace(action="install")) != 0
    out = capsys.readouterr().out
    unit = os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-coldmember@.service")
    assert f"Installed: {unit}\n" in out and ".rules\n" in out
    assert calls[2] == ["sudo", "-n", "systemctl", "daemon-reload"] and len(calls) == 4
    manual = [line for line in out.splitlines() if line.startswith("  sudo ")]
    assert len(manual) == 1 and manual[0].startswith("  sudo install -m 0644 ") \
        and manual[0].endswith(".rules")


def test_remove_and_its_failure(monkeypatch, tmp_path, capsys):
    svc = _services(monkeypatch, tmp_path)
    unit = os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-coldmember@.service")
    rule = os.path.join(svc.POLKIT_RULES_DIR, f"60-netclaw-coldmember-{_me()}.rules")
    calls, _ = _fake_run(monkeypatch)
    assert svc.cmd_coldstart(types.SimpleNamespace(action="remove")) == 0   # absent: rm -f
    assert calls == [["sudo", "-n", "rm", "-f", rule], ["sudo", "-n", "rm", "-f", unit],
                     ["sudo", "-n", "systemctl", "daemon-reload"]]      # rule first
    calls, _ = _fake_run(monkeypatch, fail=lambda argv: 1)
    assert svc.cmd_coldstart(types.SimpleNamespace(action="remove")) != 0
    out = capsys.readouterr().out
    assert f"  sudo rm -f {rule}\n  sudo rm -f {unit}\n  sudo systemctl daemon-reload" in out
    assert calls == [["sudo", "-n", "rm", "-f", rule]]


@pytest.mark.parametrize("present,probe_rc,expect", [(False, 0, 1), (True, 0, 0), (True, 1, 1)])
def test_status_reports_template_and_probe(monkeypatch, tmp_path, capsys, present, probe_rc, expect):
    svc = _services(monkeypatch, tmp_path)
    if present:
        open(os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-coldmember@.service"), "w").close()
    calls, _ = _fake_run(monkeypatch, probe_rc=probe_rc)
    assert svc.cmd_coldstart(types.SimpleNamespace(action="status")) == expect
    out = capsys.readouterr().out
    assert calls == ([PROBE] if present else [])                   # no sudo, no prompt
    if not present:
        assert "template: missing" in out and "coldstart install" in out
    elif probe_rc:
        assert "NOT authorized (exit 1): Access denied" in out
    else:
        assert "authorized (started netclaw-coldmember@probe.service)" in out


@pytest.mark.parametrize("action", ["install", "remove", "status"])
def test_coldstart_refused_as_root(monkeypatch, tmp_path, capsys, action):
    svc = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch)
    monkeypatch.setattr(svc.os, "geteuid", lambda: 0)
    monkeypatch.setattr(sys, "argv", ["in2n-services.py", "coldstart", action])
    assert svc.main() == 1
    assert calls == [] and "operator user" in capsys.readouterr().err


def test_coldstart_dispatch_as_operator(monkeypatch, tmp_path):
    svc = _services(monkeypatch, tmp_path)
    seen = []
    svc.cmd_coldstart = lambda args: seen.append(args.action) or 0
    monkeypatch.setattr(svc.os, "geteuid", lambda: 1000)
    for action in ("install", "remove", "status"):
        monkeypatch.setattr(sys, "argv", ["in2n-services.py", "coldstart", action])
        assert svc.main() == 0
    assert seen == ["install", "remove", "status"]
    monkeypatch.setattr(sys, "argv", ["in2n-services.py", "coldstart", "enable"])
    with pytest.raises(SystemExit):
        svc.main()


# ---- in2n-coldstart.py launcher -------------------------------------------

class _Exec(Exception):
    pass


@pytest.fixture
def launcher(monkeypatch, tmp_path):
    from bgp.federation.manager import FederationManager
    from bgp.federation.risk import RiskManager
    base = tmp_path / "n2n"
    mgr = FederationManager(base_dir=str(base))
    risk = RiskManager(mgr)
    risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    risk.add_member("viz", specialty=[{"name": "x"}], on_demand=True,
                    launch_cmd="bash /x/v.sh --flag 'two words' ;rm")
    risk.add_member("cml", specialty=[{"name": "x"}], launch_cmd="bash /x/c.sh")   # always-on
    risk.add_member("remote", specialty=[{"name": "x"}], on_demand=True)          # no launch_cmd
    risk.add_member("quar", specialty=[{"name": "x"}], on_demand=True, launch_cmd="bash /x/q.sh")
    risk.add_member("owned", specialty=[{"name": "x"}], on_demand=True, launch_cmd="bash /x/o.sh")
    risk.add_member("gone", specialty=[{"name": "x"}], on_demand=True, launch_cmd="bash /x/g.sh")
    mgr._conn.execute("UPDATE member SET state='quarantined' WHERE member_id='risk/quar'")
    mgr._conn.commit()
    risk.set_managed_by("risk/owned", "service", service_unit="netclaw-member-risk-owned.service")
    risk.remove_member("risk/gone") if hasattr(risk, "remove_member") else None
    mgr.close()
    monkeypatch.setenv("NETCLAW_COLDSTART_BASE_DIR", str(base))
    mod = _load("in2n_coldstart_166", "in2n-coldstart.py")
    execs = []
    def execvp(file, args):
        execs.append((file, list(args)))
        raise _Exec()
    monkeypatch.setattr(mod.os, "execvp", execvp)
    return mod, execs, base


def test_probe_is_a_no_op_without_registry_access(monkeypatch, tmp_path):
    missing = tmp_path / "never-created"
    monkeypatch.setenv("NETCLAW_COLDSTART_BASE_DIR", str(missing))
    mod = _load("in2n_coldstart_probe", "in2n-coldstart.py")
    mod._resolve = lambda instance: pytest.fail("probe must not open the registry")
    monkeypatch.setattr(mod.os, "execvp", lambda *a: pytest.fail("probe must not exec"))
    assert mod.main(["probe"]) == 0
    assert not missing.exists()


@pytest.mark.parametrize("instance", ["", "-x", ".x", "a/b", "a b", "../x", "a;b", "a$b",
                                      "x" * 129, "risk-viz\n"])
def test_invalid_instance_rejected_before_lookup(monkeypatch, instance):
    mod = _load("in2n_coldstart_bad", "in2n-coldstart.py")
    mod._resolve = lambda i: pytest.fail("must not resolve an invalid instance")
    monkeypatch.setattr(mod.os, "execvp", lambda *a: pytest.fail("must not exec"))
    assert mod.main([instance]) == 2
    assert mod.main([]) == 2 and mod.main(["a", "b"]) == 2


def test_valid_on_demand_member_execs_exact_argv(launcher, monkeypatch):
    mod, execs, _ = launcher
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/bash" if name == "bash" else None)
    with pytest.raises(_Exec):
        mod.main(["risk-viz"])
    # shlex argv, no shell: `;rm` is a literal argument, never a command
    assert execs == [("/usr/bin/bash", ["/usr/bin/bash", "/x/v.sh", "--flag", "two words", ";rm"])]
    assert "NETCLAW_COLDSTART_BASE_DIR" not in os.environ          # not leaked to the member


@pytest.mark.parametrize("instance", ["risk-nobody", "risk-cml", "risk-remote", "risk-quar",
                                      "risk-owned", "risk-gone", "probe2"])
def test_unknown_or_ineligible_member_refused(launcher, capsys, instance):
    mod, execs, _ = launcher
    assert mod.main([instance]) == 3
    assert execs == [] and "refusing" in capsys.readouterr().err


# ---- controls: system_coldstart_available + argv -------------------------

def _template(monkeypatch, tmp_path, present=True):
    sdir = tmp_path / "etc"
    sdir.mkdir(exist_ok=True)
    if present:
        (sdir / "netclaw-coldmember@.service").write_text("[Service]\n")
    monkeypatch.setattr(controls, "SYSTEM_UNIT_DIR", str(sdir))
    monkeypatch.setattr(controls.shutil, "which", lambda name: "/usr/bin/" + name)
    return sdir / "netclaw-coldmember@.service"


def _probe_results(monkeypatch, results):
    calls = []
    async def _run(cmd, timeout_s=12.0):
        calls.append(cmd)
        return results[min(len(calls), len(results)) - 1]
    monkeypatch.setattr(controls, "_run", _run)
    return calls


def test_system_coldstart_needs_template(monkeypatch, tmp_path):
    _template(monkeypatch, tmp_path, present=False)
    calls = _probe_results(monkeypatch, [(0, "")])
    assert asyncio.run(controls.system_coldstart_available()) is False and calls == []


def test_system_coldstart_success_cached_per_template(monkeypatch, tmp_path):
    unit = _template(monkeypatch, tmp_path)
    calls = _probe_results(monkeypatch, [(0, "")])
    assert asyncio.run(controls.system_coldstart_available()) is True
    assert asyncio.run(controls.system_coldstart_available()) is True
    assert calls == [PROBE]                                        # no sudo, no --user
    unit.write_text("[Service]\nType=simple\n")                    # reinstalled
    assert asyncio.run(controls.system_coldstart_available()) is True and len(calls) == 2
    unit.unlink()                                                  # removed
    assert asyncio.run(controls.system_coldstart_available()) is False and len(calls) == 2
    unit.write_text("[Service]\n")
    controls.invalidate_cache()
    assert asyncio.run(controls.system_coldstart_available()) is True and len(calls) == 3
    controls.forget_system_coldstart()
    assert asyncio.run(controls.system_coldstart_available()) is True and len(calls) == 4


def test_system_coldstart_denial_short_cache_and_errors_not_cached(monkeypatch, tmp_path):
    _template(monkeypatch, tmp_path)
    calls = _probe_results(monkeypatch, [(-1, "probe timed out"), (-1, "x"), (1, "denied"), (0, "")])
    assert asyncio.run(controls.system_coldstart_available()) is False
    assert asyncio.run(controls.system_coldstart_available()) is False
    assert len(calls) == 2                                         # errors are re-probed
    assert asyncio.run(controls.system_coldstart_available()) is False
    assert asyncio.run(controls.system_coldstart_available()) is False
    assert len(calls) == 3                                         # denial: ~3s TTL
    controls._cache["coldstart"] = (0, controls._cache["coldstart"][1])   # TTL elapsed
    assert asyncio.run(controls.system_coldstart_available()) is True and len(calls) == 4
    monkeypatch.setattr(controls.shutil, "which", lambda name: None)
    controls.invalidate_cache()
    assert asyncio.run(controls.system_coldstart_available()) is False and len(calls) == 4


def test_confined_cold_start_argv_selection(monkeypatch):
    monkeypatch.setattr(controls.shutil, "which", lambda name: "/usr/bin/" + name)
    assert controls.confined_cold_start("bash /x/v.sh", "risk/viz", system=True) == SYSTEM_ARGV
    user = controls.confined_cold_start("bash /x/v.sh", "risk/viz")
    assert user[:5] == ["systemd-run", "--user", "--collect", "--unit", "netclaw-coldmember-risk-viz"]
    assert user == controls.confined_cold_start("bash /x/v.sh", "risk/viz", system=False)
    with pytest.raises(ValueError):
        controls.confined_cold_start("x", "risk/a b", system=True)


# ---- sandbox_available matrix --------------------------------------------

def _posture(monkeypatch, tmp_path, *, runtime="openclaw", user=(), system=(), probe=False,
             cold=False):
    monkeypatch.setenv("HOME", str(tmp_path))
    udir = tmp_path / ".config" / "systemd" / "user"
    sdir = tmp_path / "etc"
    udir.mkdir(parents=True, exist_ok=True)
    sdir.mkdir(exist_ok=True)
    for d, names in ((udir, user), (sdir, system)):
        for n in names:
            (d / n).write_text("")
    monkeypatch.setattr(controls, "SYSTEM_UNIT_DIR", str(sdir))
    monkeypatch.setattr(controls.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(controls, "_runtime_kind", lambda: runtime)
    async def _run(cmd, timeout_s=12.0):
        return 0, ("NoNewPrivileges=yes\nProtectSystem=strict\n" if "show" in cmd else "")
    monkeypatch.setattr(controls, "_run", _run)
    async def _probe():
        return probe
    monkeypatch.setattr(controls, "user_scope_pidns_readable", _probe)
    colds = []
    async def _cold():
        colds.append(1)
        return cold
    monkeypatch.setattr(controls, "system_coldstart_available", _cold)
    return colds


_SYS = "netclaw-member-risk-cml.service"


@pytest.mark.parametrize("units,members,cold,expect_ok,needle", [
    ({"system": [_SYS]}, ["risk/viz"], True, True, "netclaw-coldmember@"),
    ({"system": [_SYS]}, ["risk/viz"], False, False, "coldstart install"),
    ({"system": [_SYS]}, [], True, True, "netclaw-coldmember@"),
    ({"system": [_SYS]}, [], False, True, "coldstart install"),       # spec 165: gap named
    ({}, ["risk/viz"], True, True, "netclaw-coldmember@"),
    ({}, [], True, True, "no member units yet"),
    ({}, ["risk/viz"], False, False, "coldstart install"),
    ({"user": [_SYS]}, ["risk/viz"], True, False, "generate --system"),  # user units still broken
])
def test_sandbox_available_with_system_coldstart(monkeypatch, tmp_path, units, members, cold,
                                                 expect_ok, needle):
    _posture(monkeypatch, tmp_path, cold=cold, **units)
    ok, detail = asyncio.run(controls.sandbox_available(on_demand_members=members))
    assert ok is expect_ok and needle in detail
    if cold and expect_ok:
        assert "cold-start as confined system instances" in detail
        assert "still use user-scope" not in detail


@pytest.mark.parametrize("runtime,probe", [("hermes", False), ("openclaw", True)])
def test_hermes_and_probe_success_never_consult_system_coldstart(monkeypatch, tmp_path, runtime, probe):
    colds = _posture(monkeypatch, tmp_path, runtime=runtime, probe=probe, cold=True, system=[_SYS])
    assert asyncio.run(controls.sandbox_available(on_demand_members=["risk/viz"])) == (True, "")
    assert colds == []


def test_compute_posture_enforced_with_system_coldstart(monkeypatch, tmp_path):
    from bgp.federation import posture
    _posture(monkeypatch, tmp_path, system=[_SYS], cold=True)
    async def _ok():
        return True, ""
    monkeypatch.setattr(controls, "defenseclaw_available", _ok)
    monkeypatch.setattr(controls, "gait_recording", lambda: (True, ""))
    monkeypatch.setattr(controls, "is_production", lambda: True)
    members = [{"member_id": "risk/viz", "launch_cmd": "bash /x/v.sh", "on_demand": 1,
                "managed_by": "cold", "state": "provisioned"}]
    fake = types.SimpleNamespace(risk=types.SimpleNamespace(list_members=lambda: members))
    p = asyncio.run(posture.compute_posture(fake))
    sandbox = next(c for c in p["controls"] if c["name"] == "sandbox")
    assert p["state"] == "enforced" and "netclaw-coldmember@" in sandbox["detail"]


# ---- service: production cold-start --------------------------------------

def _border(tmp_path):
    from bgp.federation.manager import FederationManager
    from bgp.federation.service import FederationService
    mgr = FederationManager(base_dir=str(tmp_path / "b"))
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=mgr)
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    svc.risk.add_member("viz", specialty=[{"name": "x"}], launch_cmd="bash /x/v.sh", on_demand=True)
    return svc


def _spawns(monkeypatch, svc, rc=0, dial=True):
    execs, shells = [], []
    async def _exec(*argv, **k):
        execs.append(list(argv))
        if dial and rc == 0:
            svc.member_channels["risk/viz"] = object()
        return types.SimpleNamespace(wait=lambda: asyncio.sleep(0, result=rc))
    async def _shell(cmd, **k):
        shells.append(cmd)
        svc.member_channels["risk/viz"] = object()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    monkeypatch.setattr(asyncio, "create_subprocess_shell", _shell)
    return execs, shells


def test_production_cold_start_uses_system_instance(monkeypatch, tmp_path):
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    colds = _posture(monkeypatch, tmp_path, system=[_SYS], cold=True)
    svc = _border(tmp_path)
    execs, shells = _spawns(monkeypatch, svc)
    try:
        assert asyncio.run(svc.ensure_member_up("risk/viz", wait_s=5)) is not None
        assert execs == [SYSTEM_ARGV] and shells == [] and colds
    finally:
        svc.manager.close()


def test_production_cold_start_system_start_refused_fails_fast(monkeypatch, tmp_path):
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    _posture(monkeypatch, tmp_path, system=[_SYS], cold=True)
    forgotten = []
    monkeypatch.setattr(controls, "forget_system_coldstart", lambda: forgotten.append(1))
    svc = _border(tmp_path)
    execs, _ = _spawns(monkeypatch, svc, rc=1)
    try:
        start = time.monotonic()
        assert asyncio.run(svc.ensure_member_up("risk/viz", wait_s=60)) is None
        assert time.monotonic() - start < 5 and execs == [SYSTEM_ARGV] and forgotten == [1]
        assert "risk/viz" not in svc._spawning
    finally:
        svc.manager.close()


@pytest.mark.parametrize("sandbox_ok", [False, True])
def test_production_cold_start_still_fails_fast_without_template(monkeypatch, tmp_path, sandbox_ok):
    # sandbox_ok=True: a stale posture verdict must not launch a user-scope unit that
    # cannot run OpenClaw on this host.
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    _posture(monkeypatch, tmp_path, system=[_SYS], cold=False)
    if sandbox_ok:
        async def _ok(on_demand_members=()):
            return True, ""
        monkeypatch.setattr(controls, "sandbox_available", _ok)
    svc = _border(tmp_path)
    execs, shells = _spawns(monkeypatch, svc)
    try:
        start = time.monotonic()
        assert asyncio.run(svc.ensure_member_up("risk/viz", wait_s=60)) is None
        assert time.monotonic() - start < 5 and execs == [] and shells == []
    finally:
        svc.manager.close()


def test_production_cold_start_user_scope_host_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    colds = _posture(monkeypatch, tmp_path, probe=True, cold=True)
    svc = _border(tmp_path)
    execs, _ = _spawns(monkeypatch, svc)
    try:
        assert asyncio.run(svc.ensure_member_up("risk/viz", wait_s=5)) is not None
        assert execs[0][:3] == ["systemd-run", "--user", "--collect"] and colds == []
    finally:
        svc.manager.close()


def test_testing_mode_cold_start_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("N2N_RISK_MODE", "testing")
    colds = _posture(monkeypatch, tmp_path, cold=True)
    svc = _border(tmp_path)
    execs, shells = _spawns(monkeypatch, svc)
    try:
        assert asyncio.run(svc.ensure_member_up("risk/viz", wait_s=5)) is not None
        assert shells == ["bash /x/v.sh"] and execs == [] and colds == []
    finally:
        svc.manager.close()


def test_launcher_reads_registry_without_writing(launcher, monkeypatch, tmp_path):
    # The confined launcher must never migrate or write the Border's registry.
    mod, execs, base = launcher
    db = base / "federation.db"
    before = db.read_bytes()
    db.chmod(0o400)
    try:
        assert mod._resolve("risk-unknown") == (None, "no registered member")
        with pytest.raises(_Exec):
            mod.main(["risk-viz"])
        assert execs and execs[0][1][1:] == ["/x/v.sh", "--flag", "two words", ";rm"]
    finally:
        db.chmod(0o600)
    assert db.read_bytes() == before
    monkeypatch.setenv("NETCLAW_COLDSTART_BASE_DIR", str(tmp_path / "absent"))
    assert mod._resolve("risk-viz") == (None, "no Risk registry")



@pytest.mark.parametrize("failing", ["template", "daemon-reload"])
def test_install_never_installs_rule_after_template_or_reload_failure(monkeypatch, tmp_path,
                                                                       capsys, failing):
    # Security: without the template a systemd 257+ host would let the rule
    # authorize a same-named transient unit (e.g. User=root).
    svc = _services(monkeypatch, tmp_path)
    fail = ((lambda a: 1 if a[2] == "install" and a[-1].endswith(".service") else 0)
            if failing == "template" else (lambda a: 1 if "daemon-reload" in a else 0))
    calls, _ = _fake_run(monkeypatch, fail=fail)
    assert svc.cmd_coldstart(types.SimpleNamespace(action="install")) != 0
    assert not any(c[2] == "install" and c[-1].endswith(".rules") for c in calls)
    assert calls[0][2:4] == ["rm", "-f"]                          # old rule dropped first
    assert "only after the template and daemon-reload succeed" in capsys.readouterr().out


def test_launcher_refuses_colliding_slugs(launcher):
    # 'risk/v-iz' and 'risk-v/iz' share the slug 'risk-v-iz': never guess.
    mod, execs, base = launcher
    import sqlite3
    conn = sqlite3.connect(str(base / "federation.db"))
    for new, cmd in (("risk/v-iz", "bash /x/a.sh"), ("risk-v/iz", "bash /x/b.sh")):
        conn.execute("INSERT INTO member (member_id, state, on_demand, launch_cmd, managed_by) "
                     "SELECT ?, state, 1, ?, managed_by FROM member WHERE member_id='risk/viz'",
                     (new, cmd))
    conn.commit(); conn.close()
    assert mod._resolve("risk-v-iz") == (None, "ambiguous: risk-v/iz, risk/v-iz")
    assert mod.main(["risk-v-iz"]) == 3 and execs == []


def test_reserved_probe_slug_is_never_cold_started():
    from bgp.federation import controls
    with pytest.raises(ValueError):
        controls.confined_cold_start("bash x", "probe", system=True)


def test_production_cold_start_hung_systemctl_is_killed_and_forgotten(monkeypatch, tmp_path):
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    _posture(monkeypatch, tmp_path, system=[_SYS], cold=True)
    forgotten, killed = [], []
    monkeypatch.setattr(controls, "forget_system_coldstart", lambda: forgotten.append(1))
    svc = _border(tmp_path)
    hung = asyncio.Event()

    class _Proc:
        async def wait(self):
            if not killed:
                await hung.wait()
            return -9

        def kill(self):
            killed.append(1)

    async def _exec(*argv, **k):
        return _Proc()

    async def _wait_for(aw, timeout):
        aw.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)
    monkeypatch.setattr(asyncio, "wait_for", _wait_for)
    try:
        assert asyncio.run(svc.ensure_member_up("risk/viz", wait_s=60)) is None
        assert killed == [1] and forgotten == [1] and "risk/viz" not in svc._spawning
    finally:
        svc.manager.close()
