"""Spec 165: system-scope member units + honest sandbox posture on OpenClaw hosts
where mount-namespaced `systemd --user` units cannot stat /proc/self/ns/pid.
systemctl/sudo/systemd-run are stubbed — no root or systemd required."""

import asyncio
import grp
import importlib.util
import os
import pwd
import subprocess
import sys
import types

import pytest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(REPO, "mcp-servers", "protocol-mcp"))

from bgp.federation import controls


def _services(monkeypatch, tmp_path):
    monkeypatch.setenv("NETCLAW_RUNTIME", "openclaw")
    monkeypatch.setenv("OPENCLAW_HOME", str(tmp_path / "oc"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    spec = importlib.util.spec_from_file_location(
        "in2n_services_165", os.path.join(REPO, "scripts", "in2n-services.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.UNIT_DIR = str(tmp_path / "user")
    mod.SYSTEM_UNIT_DIR = str(tmp_path / "etc")
    os.makedirs(mod.SYSTEM_UNIT_DIR)
    mod._full_sandbox_cache = False
    mod._suffix = lambda: ""
    bound = []

    class _Risk:
        def list_members(self):
            return [{"member_id": "risk/cml", "launch_cmd": "bash /x/run.sh", "on_demand": False}]
        def set_managed_by(self, member_id, how, service_unit=None):
            bound.append((member_id, how, service_unit))
        def service_unit(self, member_id):
            return None
        def get_risk(self):
            return {"risk_name": "risk"}
    mod._risk = lambda: (types.SimpleNamespace(close=lambda: None), _Risk())
    mod._has_systemctl_user = lambda: True
    mod._defenseclaw_unit_text = lambda: None
    return mod, bound


def _fake_run(monkeypatch, sudo_rc=0, active_rc=1):
    calls = []
    staged = {}
    def run(argv, *a, **k):
        calls.append(list(argv))
        if argv[:3] == ["sudo", "-n", "install"]:
            with open(argv[-2]) as fh:
                staged[argv[-1]] = fh.read()
        if argv[0] == "sudo":
            return subprocess.CompletedProcess(argv, sudo_rc)
        if argv[1] in ("is-enabled", "is-active"):
            return subprocess.CompletedProcess(argv, active_rc, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="active\n", stderr="")
    monkeypatch.setattr(subprocess, "run", run)
    return calls, staged


def test_system_unit_text_has_identity_full_hardening_and_system_target(monkeypatch, tmp_path):
    svc, _ = _services(monkeypatch, tmp_path)
    user = pwd.getpwuid(os.getuid())
    text = svc._member_unit_text("risk/cml", "bash /x/run.sh", system=True)
    assert f"User={user.pw_name}\n" in text
    assert f"Group={grp.getgrgid(user.pw_gid).gr_name}\n" in text
    assert f'Environment="HOME={svc.HOME}"' in text
    for d in ("NoNewPrivileges=yes", "PrivateTmp=yes", "ProtectSystem=strict",
              "ProtectKernelModules=yes", "RestrictNamespaces=yes",
              "SystemCallFilter=@system-service", "InaccessiblePaths=-"):
        assert d in text
    # %h is /root in the system manager — the literal home must be pinned
    assert "%h" not in text and f'ReadWritePaths="{svc.HOME}"' in text
    assert "WantedBy=multi-user.target" in text and "default.target" not in text
    assert "After=network-online.target\n" in text and "netclaw-mesh" not in text
    # default (user-scope) text unchanged
    user_text = svc._member_unit_text("risk/cml", "bash /x/run.sh")
    assert "User=" not in user_text and "WantedBy=default.target" in user_text
    assert "Wants=netclaw-mesh" in user_text and "ReadWritePaths=%h" in user_text


def test_generate_system_installs_through_sudo_n(monkeypatch, tmp_path, capsys):
    svc, bound = _services(monkeypatch, tmp_path)
    calls, staged = _fake_run(monkeypatch)
    assert svc.cmd_generate(types.SimpleNamespace(system=True)) == 0
    target = os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-member-risk-cml.service")
    install = [c for c in calls if c[:3] == ["sudo", "-n", "install"]]
    assert install and install[0][3:5] == ["-m", "0644"] and install[0][-1] == target
    assert "User=" in staged[target] and "WantedBy=multi-user.target" in staged[target]
    assert ["sudo", "-n", "systemctl", "daemon-reload"] in calls
    assert not os.path.exists(os.path.dirname(install[0][-2]))   # staging removed
    assert not os.path.exists(os.path.join(svc.UNIT_DIR, "netclaw-member-risk-cml.service"))
    assert bound == []                                            # bind only on enable
    assert "enable --system" in capsys.readouterr().out


def test_generate_system_sudo_failure_prints_commands_and_writes_nothing(monkeypatch, tmp_path, capsys):
    svc, bound = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch, sudo_rc=1)
    assert svc.cmd_generate(types.SimpleNamespace(system=True)) != 0
    out = capsys.readouterr().out
    assert os.listdir(svc.SYSTEM_UNIT_DIR) == []
    assert "sudo install -m 0644 " in out and "sudo systemctl daemon-reload" in out
    staged = next(c for c in calls if c[:3] == ["sudo", "-n", "install"])[-2]
    assert os.path.exists(staged)                                 # kept for the printed command
    assert os.stat(os.path.dirname(staged)).st_mode & 0o077 == 0  # private staging
    assert all(c[:2] == ["sudo", "-n"] for c in calls)            # never interactive sudo
    assert bound == []


def test_enable_system_binds_only_after_sudo_success(monkeypatch, tmp_path, capsys):
    svc, bound = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch, sudo_rc=1)
    assert svc.cmd_enable(types.SimpleNamespace(system=True)) != 0
    assert bound == []
    assert "sudo systemctl enable --now netclaw-member-risk-cml.service" in capsys.readouterr().out
    assert ["systemctl", "--user", "enable", "--now", "netclaw-mesh.service"] in calls
    calls, _ = _fake_run(monkeypatch, sudo_rc=0)
    assert svc.cmd_enable(types.SimpleNamespace(system=True)) == 0
    assert ["sudo", "-n", "systemctl", "enable", "--now", "netclaw-member-risk-cml.service"] in calls
    assert bound == [("risk/cml", "service", "netclaw-member-risk-cml.service")]


def test_enable_system_binds_already_active_unit_without_sudo(monkeypatch, tmp_path):
    svc, bound = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch, sudo_rc=1, active_rc=0)
    assert svc.cmd_enable(types.SimpleNamespace(system=True)) == 0
    assert not any(c[0] == "sudo" for c in calls)
    assert bound == [("risk/cml", "service", "netclaw-member-risk-cml.service")]


def test_status_and_disable_system(monkeypatch, tmp_path, capsys):
    svc, bound = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch, sudo_rc=1)
    assert svc.cmd_status(types.SimpleNamespace(system=True)) == 0
    assert ["systemctl", "is-active", "netclaw-member-risk-cml.service"] in calls   # no sudo needed
    assert ["systemctl", "--user", "is-active", "netclaw-mesh.service"] in calls
    open(os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-member-risk-cml.service"), "w").close()
    assert svc.cmd_disable(types.SimpleNamespace(system=True, member="risk/cml")) != 0
    assert bound == []                                            # still service-owned
    assert "sudo systemctl disable --now netclaw-member-risk-cml.service" in capsys.readouterr().out
    calls, _ = _fake_run(monkeypatch, sudo_rc=0)
    assert svc.cmd_disable(types.SimpleNamespace(system=True, member="risk/cml")) == 0
    assert ["sudo", "-n", "rm", "-f", os.path.join(svc.SYSTEM_UNIT_DIR, "netclaw-member-risk-cml.service")] in calls
    assert bound == [("risk/cml", "cold", None)]


def test_default_generate_stays_user_scope(monkeypatch, tmp_path):
    svc, _ = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch)
    assert svc.cmd_generate(types.SimpleNamespace()) == 0
    assert os.path.exists(os.path.join(svc.UNIT_DIR, "netclaw-member-risk-cml.service"))
    assert os.listdir(svc.SYSTEM_UNIT_DIR) == [] and not any(c[0] == "sudo" for c in calls)


# ---- posture: sandbox_available ------------------------------------------

def _posture(monkeypatch, tmp_path, *, runtime="openclaw", user=(), system=(), probe=False,
             confined=True):
    controls.invalidate_cache()
    monkeypatch.setenv("HOME", str(tmp_path))
    udir = tmp_path / ".config" / "systemd" / "user"
    sdir = tmp_path / "etc"
    udir.mkdir(parents=True)
    sdir.mkdir()
    for d, names in ((udir, user), (sdir, system)):
        for n in names:
            (d / n).write_text("")
    monkeypatch.setattr(controls, "SYSTEM_UNIT_DIR", str(sdir))
    monkeypatch.setattr(controls.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(controls, "_runtime_kind", lambda: runtime)
    shows = []
    async def _run(cmd, timeout_s=12.0):
        if "show" in cmd:
            shows.append(cmd)
            return 0, ("NoNewPrivileges=yes\nProtectSystem=strict\n" if confined
                       else "NoNewPrivileges=no\nProtectSystem=no\n")
        return 0, ""
    monkeypatch.setattr(controls, "_run", _run)
    probes = []
    async def _probe():
        probes.append(1)
        return probe
    monkeypatch.setattr(controls, "user_scope_pidns_readable", _probe)
    return asyncio.run(controls.sandbox_available()), shows, probes


def test_openclaw_user_units_unavailable_with_system_remediation(monkeypatch, tmp_path):
    (ok, detail), _, _ = _posture(monkeypatch, tmp_path, user=["netclaw-member-risk-cml.service"])
    assert ok is False
    assert "/proc/self/ns/pid" in detail and "generate --system" in detail
    assert "netclaw-member-risk-cml.service" in detail and "cold-start" in detail


def test_openclaw_fresh_border_not_told_user_confinement_works(monkeypatch, tmp_path):
    (ok, detail), _, _ = _posture(monkeypatch, tmp_path)
    assert ok is False and "generate --system" in detail and "cold-start" in detail


def test_system_units_accepted_with_cold_start_gap(monkeypatch, tmp_path):
    (ok, detail), shows, _ = _posture(monkeypatch, tmp_path, system=["netclaw-member-risk-cml.service"])
    assert ok is True and "cold-start" in detail
    assert shows == [["systemctl", "show", "netclaw-member-risk-cml.service",
                      "-p", "NoNewPrivileges,ProtectSystem"]]


def test_unconfined_system_unit_is_unavailable(monkeypatch, tmp_path):
    (ok, detail), _, _ = _posture(monkeypatch, tmp_path, system=["netclaw-member-risk-cml.service"],
                                  confined=False)
    assert ok is False and "generate --system" in detail


@pytest.mark.parametrize("runtime,probe", [("hermes", False), ("openclaw", True)])
def test_hermes_and_probe_success_unchanged(monkeypatch, tmp_path, runtime, probe):
    (ok, detail), shows, probes = _posture(monkeypatch, tmp_path, runtime=runtime, probe=probe,
                                           user=["netclaw-member-risk-cml.service"])
    assert (ok, detail) == (True, "")
    assert shows[0][:2] == ["systemctl", "--user"]
    assert probes == ([] if runtime == "hermes" else [1])
    controls.invalidate_cache()
    (tmp_path / "again").mkdir()
    (ok, detail), _, _ = _posture(monkeypatch, tmp_path / "again", runtime=runtime, probe=probe)
    assert (ok, detail) == (True, "systemd confinement available (no member units yet)")


def test_pidns_probe_command_result_and_cache(monkeypatch):
    controls.invalidate_cache()
    calls = []
    async def _run(cmd, timeout_s=12.0):
        calls.append((cmd, timeout_s))
        return 3, ""                                              # child: PermissionError
    monkeypatch.setattr(controls, "_run", _run)
    monkeypatch.setattr(controls.shutil, "which", lambda name: "/usr/bin/" + name)
    assert asyncio.run(controls.user_scope_pidns_readable()) is False
    assert asyncio.run(controls.user_scope_pidns_readable()) is False
    assert len(calls) == 1                                        # definitive: cached per process
    cmd, timeout = calls[0]
    assert cmd[:6] == ["systemd-run", "--user", "--wait", "--collect", "--pipe", "--quiet"]
    assert cmd[6:10] == ["-p", "PrivateTmp=yes", "-p", "ProtectSystem=strict"]
    assert cmd[10] == sys.executable
    assert "/proc/self/ns/pid" in cmd[-1] and "except PermissionError: sys.exit(3)" in cmd[-1]
    assert timeout > 0
    controls.invalidate_cache()
    monkeypatch.setattr(controls, "_run", lambda cmd, timeout_s=12.0: asyncio.sleep(0, (0, "")))
    assert asyncio.run(controls.user_scope_pidns_readable()) is True
    controls.invalidate_cache()
    monkeypatch.setattr(controls.shutil, "which", lambda name: None)
    assert asyncio.run(controls.user_scope_pidns_readable()) is False
    controls.invalidate_cache()


def test_border_queries_system_member_unit_without_starting_it(monkeypatch, tmp_path):
    from bgp.federation import service
    (tmp_path / "netclaw-member-r-m.service").write_text("[Service]\n")
    monkeypatch.setattr(controls, "SYSTEM_UNIT_DIR", str(tmp_path))
    calls = []

    async def fake_exec(*argv, **kwargs):
        calls.append(argv)
        return types.SimpleNamespace(wait=lambda: asyncio.sleep(0, result=3))

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    svc = object.__new__(service.FederationService)
    assert asyncio.run(svc._ensure_unit_active("netclaw-member-r-m.service")) is False
    assert calls == [("systemctl", "is-active", "--quiet", "netclaw-member-r-m.service")]


# ---- spec 165 T006: verifier advisories A-F ------------------------------

_UNIT = "netclaw-member-risk-cml.service"


def test_disable_system_unit_already_absent_needs_no_sudo(monkeypatch, tmp_path, capsys):
    # A: nothing left in the system manager -> no sudo at all, still reverts to cold.
    svc, bound = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch, sudo_rc=1, active_rc=3)
    assert svc.cmd_disable(types.SimpleNamespace(system=True, member="risk/cml")) == 0
    assert not any(c[0] == "sudo" for c in calls)
    assert ["systemctl", "is-active", "--quiet", _UNIT] in calls
    assert bound == [("risk/cml", "cold", None)]
    assert "already absent" in capsys.readouterr().out


def test_disable_system_absent_file_cleans_leftovers_then_reloads(monkeypatch, tmp_path):
    # A: file gone but the unit still runs and the enablement link dangles.
    svc, bound = _services(monkeypatch, tmp_path)
    wants = os.path.join(svc.SYSTEM_UNIT_DIR, "multi-user.target.wants")
    os.makedirs(wants)
    os.symlink(os.path.join(svc.SYSTEM_UNIT_DIR, _UNIT), os.path.join(wants, _UNIT))
    calls, _ = _fake_run(monkeypatch, sudo_rc=0, active_rc=0)
    assert svc.cmd_disable(types.SimpleNamespace(system=True, member="risk/cml")) == 0
    sudo = [c for c in calls if c[0] == "sudo"]
    assert sudo == [["sudo", "-n", "systemctl", "stop", _UNIT],
                    ["sudo", "-n", "rm", "-f", os.path.join(wants, _UNIT)],
                    ["sudo", "-n", "systemctl", "daemon-reload"]]
    assert bound == [("risk/cml", "cold", None)]
    calls, _ = _fake_run(monkeypatch, sudo_rc=1, active_rc=0)
    bound.clear()
    assert svc.cmd_disable(types.SimpleNamespace(system=True, member="risk/cml")) != 0
    assert bound == []                                            # still service-owned


def test_disable_system_present_unit_disables_removes_and_reloads(monkeypatch, tmp_path):
    svc, bound = _services(monkeypatch, tmp_path)
    path = os.path.join(svc.SYSTEM_UNIT_DIR, _UNIT)
    open(path, "w").close()
    calls, _ = _fake_run(monkeypatch, sudo_rc=0)
    assert svc.cmd_disable(types.SimpleNamespace(system=True, member="risk/cml")) == 0
    assert [c for c in calls if c[0] == "sudo"] == [
        ["sudo", "-n", "systemctl", "disable", "--now", _UNIT],
        ["sudo", "-n", "rm", "-f", path], ["sudo", "-n", "systemctl", "daemon-reload"]]
    assert bound == [("risk/cml", "cold", None)]


@pytest.mark.parametrize("user_copy", [False, True])
def test_user_disable_refuses_system_bound_member(monkeypatch, tmp_path, capsys, user_copy):
    # B: a user-scope disable must not revert a system-unit member to cold.
    svc, bound = _services(monkeypatch, tmp_path)
    open(os.path.join(svc.SYSTEM_UNIT_DIR, _UNIT), "w").close()
    if user_copy:
        os.makedirs(svc.UNIT_DIR)
        open(os.path.join(svc.UNIT_DIR, _UNIT), "w").close()
    calls, _ = _fake_run(monkeypatch)
    assert svc.cmd_disable(types.SimpleNamespace(system=False, member="cml")) != 0
    assert "disable --system cml" in capsys.readouterr().out
    assert bound == [] and calls == []
    assert os.path.exists(os.path.join(svc.SYSTEM_UNIT_DIR, _UNIT))
    assert os.path.exists(os.path.join(svc.UNIT_DIR, _UNIT)) is user_copy


def _two_members(svc):
    class _Risk:
        def list_members(self):
            return [{"member_id": "risk/a", "launch_cmd": "bash /x/a.sh", "on_demand": False},
                    {"member_id": "risk/b", "launch_cmd": "bash /x/b.sh", "on_demand": False}]
    svc._risk = lambda: (types.SimpleNamespace(close=lambda: None), _Risk())


def test_generate_system_partial_install_reloads_and_reports(monkeypatch, tmp_path, capsys):
    # D: unit a installs, unit b does not -> reload what was installed, report both.
    svc, _ = _services(monkeypatch, tmp_path)
    _two_members(svc)
    calls = []
    def run(argv, *a, **k):
        calls.append(list(argv))
        rc = 1 if argv[:3] == ["sudo", "-n", "install"] and argv[-1].endswith("risk-b.service") else 0
        return subprocess.CompletedProcess(argv, rc)
    monkeypatch.setattr(subprocess, "run", run)
    assert svc.cmd_generate(types.SimpleNamespace(system=True)) != 0
    a, b = (os.path.join(svc.SYSTEM_UNIT_DIR, f"netclaw-member-risk-{m}.service") for m in "ab")
    assert [c[-1] for c in calls if c[:3] == ["sudo", "-n", "install"]] == [a, b]
    assert calls[-1] == ["sudo", "-n", "systemctl", "daemon-reload"]
    out = capsys.readouterr().out
    assert "Installed in %s: netclaw-member-risk-a.service\n" % svc.SYSTEM_UNIT_DIR in out
    assert "NOT installed: netclaw-member-risk-b.service\n" in out
    assert "daemon-reload of the installed units: done" in out
    manual = [line for line in out.splitlines() if line.startswith("  sudo ")]
    staged_b = next(c for c in calls if c[-1] == b)[-2]
    assert manual == [f"  sudo install -m 0644 {staged_b} {b}", "  sudo systemctl daemon-reload"]
    assert os.path.exists(staged_b)                               # kept for the printed command
    assert all(c[:2] == ["sudo", "-n"] for c in calls)


def test_generate_system_reload_failure_after_full_install_is_reported(monkeypatch, tmp_path, capsys):
    svc, _ = _services(monkeypatch, tmp_path)
    def run(argv, *a, **k):
        return subprocess.CompletedProcess(argv, 1 if argv[2:] == ["systemctl", "daemon-reload"] else 0)
    monkeypatch.setattr(subprocess, "run", run)
    assert svc.cmd_generate(types.SimpleNamespace(system=True)) != 0
    out = capsys.readouterr().out
    assert "NOT installed: none" in out and "daemon-reload of the installed units: FAILED" in out
    assert [line for line in out.splitlines() if line.startswith("  sudo ")] == ["  sudo systemctl daemon-reload"]


@pytest.mark.parametrize("cmd", [["generate", "--system"], ["enable", "--system"],
                                 ["status", "--system"], ["disable", "--system", "cml"]])
def test_system_refused_as_root(monkeypatch, tmp_path, capsys, cmd):
    # E: root would resolve User=/HOME to root; the script uses sudo -n itself.
    svc, bound = _services(monkeypatch, tmp_path)
    calls, _ = _fake_run(monkeypatch)
    monkeypatch.setattr(svc.os, "geteuid", lambda: 0)
    monkeypatch.setattr(sys, "argv", ["in2n-services.py", *cmd])
    svc._risk = lambda: pytest.fail("must refuse before touching the risk")
    assert svc.main() == 1
    assert calls == [] and bound == []
    assert "operator user" in capsys.readouterr().err


def test_root_without_system_and_operator_with_system_dispatch(monkeypatch, tmp_path):
    svc, _ = _services(monkeypatch, tmp_path)
    seen = []
    svc.cmd_status = lambda args: seen.append(args.system) or 0
    for euid, argv in ((0, ["status"]), (1000, ["status", "--system"])):
        monkeypatch.setattr(svc.os, "geteuid", lambda euid=euid: euid)
        monkeypatch.setattr(sys, "argv", ["in2n-services.py", *argv])
        assert svc.main() == 0
    assert seen == [False, True]


def test_pidns_probe_timeout_is_retried_not_cached(monkeypatch):
    # F1: a timeout/launch error is not a host property.
    controls.invalidate_cache()
    results = [(-1, "probe timed out"), (-1, "probe error: x"), (1, "systemd-run failed"), (0, ""), (3, "")]
    calls = []
    async def _run(cmd, timeout_s=12.0):
        calls.append(cmd)
        return results[len(calls) - 1]
    monkeypatch.setattr(controls, "_run", _run)
    monkeypatch.setattr(controls.shutil, "which", lambda name: "/usr/bin/" + name)
    assert asyncio.run(controls.user_scope_pidns_readable()) is False
    assert asyncio.run(controls.user_scope_pidns_readable()) is False
    assert asyncio.run(controls.user_scope_pidns_readable()) is False   # L1: not the stat refusal
    assert asyncio.run(controls.user_scope_pidns_readable()) is True
    assert asyncio.run(controls.user_scope_pidns_readable()) is True
    assert len(calls) == 4                                        # success cached after retries
    controls.invalidate_cache()


def test_member_path_line_quoted_in_both_scopes(monkeypatch, tmp_path):
    # F3: homes with spaces or % must survive systemd's Environment= parsing.
    svc, _ = _services(monkeypatch, tmp_path)
    svc.HOME = "/home/op er%x"
    expected = 'Environment="PATH=' + svc._member_path().replace("%", "%%") + '"\n'
    assert "/home/op er%%x/.local/bin" in expected
    for system in (False, True):
        text = svc._member_unit_text("risk/cml", "bash /x/run.sh", system=system)
        assert expected in text
        assert "Environment=PATH=" not in text


# ---- C: on-demand OpenClaw members where user-scope confinement fails ----

@pytest.mark.parametrize("runtime,probe,expect_ok", [
    ("openclaw", False, False), ("openclaw", True, True), ("hermes", False, True)])
def test_on_demand_members_degrade_system_only_sandbox(monkeypatch, tmp_path, runtime, probe, expect_ok):
    _posture(monkeypatch, tmp_path, runtime=runtime, probe=probe, system=[_UNIT])
    ok, detail = asyncio.run(controls.sandbox_available(on_demand_members=["risk/viz"]))
    assert ok is expect_ok
    if not expect_ok:
        assert "risk/viz" in detail and "cold-start" in detail and "/proc/self/ns/pid" in detail
        assert "generate --system" in detail and "on_demand=false" in detail
    controls.invalidate_cache()


def test_compute_posture_passes_spawnable_on_demand_members(monkeypatch, tmp_path):
    from bgp.federation import posture
    _posture(monkeypatch, tmp_path, system=[_UNIT])
    async def _ok():
        return True, ""
    monkeypatch.setattr(controls, "defenseclaw_available", _ok)
    monkeypatch.setattr(controls, "gait_recording", lambda: (True, ""))
    monkeypatch.setattr(controls, "is_production", lambda: True)
    members = [{"member_id": "risk/cml", "launch_cmd": "bash /x/run.sh", "on_demand": 0,
                "managed_by": "service", "state": "active"},
               {"member_id": "risk/odsvc", "launch_cmd": "bash /x/s.sh", "on_demand": 1,
                "managed_by": "service", "state": "active"},
               {"member_id": "risk/remote", "launch_cmd": None, "on_demand": 1, "managed_by": "cold",
                "state": "provisioned"},
               {"member_id": "risk/quar", "launch_cmd": "bash /x/q.sh", "on_demand": 1,
                "managed_by": "cold", "state": "quarantined"}]                # L2: not routable
    fake = types.SimpleNamespace(risk=types.SimpleNamespace(list_members=lambda: members))
    controls.invalidate_cache()
    p = asyncio.run(posture.compute_posture(fake))
    assert p["state"] == "enforced"                               # system-only, nothing spawnable
    members.append({"member_id": "risk/viz", "launch_cmd": "bash /x/v.sh", "on_demand": 1,
                    "managed_by": "cold", "state": "provisioned"})
    controls.invalidate_cache()
    p = asyncio.run(posture.compute_posture(fake))
    sandbox = next(c for c in p["controls"] if c["name"] == "sandbox")
    assert p["state"] == "degraded" and p["missing"] == ["sandbox"]
    assert "(risk/viz)" in sandbox["detail"]
    controls.invalidate_cache()


def test_production_cold_start_fails_fast_when_openclaw_cannot_run(monkeypatch, tmp_path):
    import time
    from bgp.federation.manager import FederationManager
    from bgp.federation.service import FederationService
    monkeypatch.setenv("N2N_RISK_MODE", "production")
    _posture(monkeypatch, tmp_path, system=[_UNIT])
    mgr = FederationManager(base_dir=str(tmp_path / "b"))
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=mgr)
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    svc.risk.add_member("viz", specialty=[{"name": "x"}], launch_cmd="bash /x/v.sh", on_demand=True)
    spawned = []
    async def _spawn(*a, **k):
        spawned.append(a)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _spawn)
    monkeypatch.setattr(asyncio, "create_subprocess_shell", _spawn)
    try:
        controls.invalidate_cache()
        start = time.monotonic()
        assert asyncio.run(svc.ensure_member_up("risk/viz", wait_s=60)) is None
        assert time.monotonic() - start < 5 and spawned == []     # refused, no 90s wait
    finally:
        mgr.close()
        controls.invalidate_cache()
