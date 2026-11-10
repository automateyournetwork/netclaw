"""Spec 183 (R09A): negative-suite logic and the deploy driver's guards. No cloud, no OpenShell, no network."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from labs.ha import r09a_negative as neg  # noqa: E402

DEPLOY = REPO / "scripts/ha-r09a-deploy.sh"
BOOTSTRAP = REPO / "scripts/ha-r09a-vm-bootstrap.sh"


# ---------------------------------------------------------------- negative suite


class FakeRunner:
    def __init__(self, per_case=None, default=(1, "", "denied"), logs=""):
        self.per_case, self.default, self._logs = per_case or {}, default, logs
        self.commands = []

    def argv(self, command):
        return ["openshell", "sandbox", "exec", "node", "--", "sh", "-c", command]

    def run(self, command):
        self.commands.append(command)
        for case in neg.cases():
            if case["command"] == command and case["id"] in self.per_case:
                return self.per_case[case["id"]]
        return self.default

    def logs(self):
        return self._logs


def test_cases_cover_every_fr013_item():
    ids = {c["id"] for c in neg.cases()}
    assert {"file-read-outside-policy", "write-frozen-source", "metadata-server", "unapproved-egress",
            "provider-credential-read", "member-to-member", "docker-socket"} <= ids
    assert len(ids) == len(neg.cases())


@pytest.mark.parametrize("case", neg.cases(), ids=lambda c: c["id"])
def test_every_probe_is_valid_shell_and_prints_a_marker_only_on_success(case):
    assert subprocess.run(["sh", "-n", "-c", case["command"]], capture_output=True).returncode == 0
    for marker in neg.markers(case):
        assert marker and "echo" not in marker


def test_all_refused_exits_zero_and_report_shape():
    report = neg.run_suite(FakeRunner(), set(), "198.51.100.7:7444")
    assert report["summary"] == {"total": len(neg.cases()), "refused": len(neg.cases()), "unexpected_success": 0, "error": 0}
    assert neg.exit_code(report) == 0 and report["schema_version"] == 1


@pytest.mark.parametrize("case_id,marker", [("write-frozen-source", "WROTE:/app/server.py"), ("metadata-server", "CONNECTED"),
                                            ("provider-credential-read", "FOUND:env"), ("docker-socket", "FOUND:socket:/var/run/docker.sock"),
                                            ("ptrace-other-process", "ATTACHED")])
def test_a_success_marker_is_an_unexpected_success_and_fails_the_suite(case_id, marker):
    report = neg.run_suite(FakeRunner({case_id: (0, marker + "\n", "")}), set(), "198.51.100.7:7444")
    assert report["summary"]["unexpected_success"] == 1
    assert [c["outcome"] for c in report["cases"] if c["id"] == case_id] == ["UNEXPECTED_SUCCESS"]
    assert neg.exit_code(report) == 1


def test_a_probe_that_could_not_run_is_an_error_not_a_pass():
    report = neg.run_suite(FakeRunner({"metadata-server": (127, "", "openshell not found")}), set(), "198.51.100.7:7444")
    assert report["summary"]["error"] == 1 and neg.exit_code(report) == 1
    report = neg.run_suite(FakeRunner({"unapproved-egress": (97, "NOPYTHON\n", "")}), set(), "198.51.100.7:7444")
    assert report["summary"]["error"] == 1


def test_empty_selection_is_not_a_pass():
    assert neg.exit_code(neg.run_suite(FakeRunner(), {"does-not-exist"}, "198.51.100.7:7444")) == 1


def test_only_filter_and_dry_run_do_not_execute_probes():
    fake = FakeRunner()
    report = neg.run_suite(fake, {"metadata-server"}, "198.51.100.7:7444")
    assert [c["id"] for c in report["cases"]] == ["metadata-server"] and len(fake.commands) == 1
    fake = FakeRunner()
    dry = neg.run_suite(fake, set(), "198.51.100.7:7444", dry_run=True)
    assert fake.commands == [] and all(c["outcome"] == "dry-run" for c in dry["cases"])


def test_real_runner_builds_the_exec_argv():
    argv = neg.OpenShellRunner("netclaw-node").argv("true")
    assert argv == ["openshell", "sandbox", "exec", "netclaw-node", "--", "sh", "-c", "true"]


def test_member_address_is_used_for_the_member_case():
    case = next(c for c in neg.cases("203.0.113.9:9999") if c["id"] == "member-to-member")
    assert "203.0.113.9" in case["command"] and "9999" in case["command"]


def test_credential_probe_lists_locations_never_values():
    case = next(c for c in neg.cases() if c["id"] == "provider-credential-read")
    assert "grep -rIl" in case["command"] and " -o" not in case["command"] and "cat " not in case["command"].replace("2>/dev/null", "")
    secret = "sk-ant-" + "A" * 40
    report = neg.run_suite(FakeRunner({"provider-credential-read": (0, "FOUND:file:/tmp/x\n", "")}), set(), "198.51.100.7:7444")
    assert secret not in json.dumps(report)


def test_log_evidence_keeps_only_policy_relevant_lines_and_is_bounded():
    text = "\n".join(["noise"] * 50 + ["[1] [sandbox] [OCSF ] [ocsf] NET:FAIL [LOW] 169.254.169.254:80", "[2] ssh relay open", "[3] ... Landlock denied write"])
    lines = neg.evidence_lines(text, limit=12)
    assert lines == ["[1] [sandbox] [OCSF ] [ocsf] NET:FAIL [LOW] 169.254.169.254:80", "[3] ... Landlock denied write"]
    report = neg.run_suite(FakeRunner(logs=text), {"metadata-server"}, "198.51.100.7:7444")
    assert isinstance(report["cases"][0]["log_evidence"], list)


def test_main_writes_a_private_report_and_returns_the_suite_status(tmp_path, monkeypatch):
    monkeypatch.setattr(neg, "OpenShellRunner", lambda sandbox, openshell="openshell": FakeRunner())
    out = tmp_path / "ev"
    assert neg.main(["run", "--sandbox", "node", "--out", str(out), "--only", "metadata-server"]) == 0
    assert json.loads((out / "negative-report.json").read_text())["summary"]["refused"] == 1
    assert (out.stat().st_mode & 0o777) == 0o700
    monkeypatch.setattr(neg, "OpenShellRunner", lambda sandbox, openshell="openshell": FakeRunner({"metadata-server": (0, "CONNECTED\n", "")}))
    assert neg.main(["run", "--sandbox", "node", "--out", str(tmp_path / "ev2"), "--only", "metadata-server"]) == 1


# ---------------------------------------------------------------- deploy driver guards (stubbed gcloud)

STUB = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
case "$*" in
  *" describe "*) exit 1 ;;
  *"instances list"*) printf '%s' "${STUB_INSTANCES:-}" ;;
  *"addresses list"*) printf '%s' "${STUB_ADDRESSES:-}" ;;
  *"firewall-rules list"*) printf '%s' "${STUB_FIREWALLS:-}" ;;
  *"subnets list"*) printf '%s' "${STUB_SUBNETS:-}" ;;
  *"networks list"*) printf '%s' "${STUB_NETWORKS:-}" ;;
esac
exit 0
"""


@pytest.fixture
def stub(tmp_path):
    exe = tmp_path / "gcloud"
    exe.write_text(STUB)
    exe.chmod(0o755)
    log = tmp_path / "calls.log"
    log.write_text("")
    env = dict(os.environ, GCLOUD=str(exe), STUB_LOG=str(log))

    def run(*args, **extra):
        e = dict(env, **extra)
        p = subprocess.run(["bash", str(DEPLOY), *args], capture_output=True, text=True, env=e, timeout=60)
        return p, log.read_text().splitlines()
    return run


def mutating(calls):
    return [c for c in calls if re.search(r" (create|delete) ", c)]


def test_plan_is_read_only_and_names_only_owned_resources(stub):
    p, calls = stub("plan")
    assert p.returncode == 0 and calls == []
    names = re.findall(r"^(nc183-[a-z0-9-]+|nc183-r09a)\s", p.stdout, re.M)
    assert {"nc183-border-a", "nc183-border-b", "nc183-witness", "nc183-ip-a", "nc183-ip-b", "nc183-allow-mesh"} <= set(names)
    assert "default" not in p.stdout.replace("default network", "")


def test_apply_is_refused_without_the_confirm_flag_or_the_approval_file(stub, tmp_path):
    for args in (["apply"], ["apply", "--confirm-cost"], ["apply", "--g1-file", str(tmp_path / "g1.txt")],
                 ["apply", "--confirm-cost", "--g1-file", str(tmp_path / "missing.txt")]):
        p, calls = stub(*args)
        assert p.returncode != 0 and mutating(calls) == [] and "refused" in p.stderr, args
    bad = tmp_path / "bad.txt"
    bad.write_text("G1: pending\n")
    p, calls = stub("apply", "--confirm-cost", "--g1-file", str(bad))
    assert p.returncode != 0 and mutating(calls) == []
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    p, calls = stub("apply", "--confirm-cost", "--g1-file", str(empty))
    assert p.returncode != 0 and mutating(calls) == []


def test_apply_with_approval_creates_only_owned_labeled_resources(stub, tmp_path):
    ok = tmp_path / "g1.txt"
    ok.write_text("G1: APPROVED\n")
    p, calls = stub("apply", "--confirm-cost", "--g1-file", str(ok))
    assert p.returncode == 0, p.stderr
    creates = [c for c in calls if " create " in c]
    assert len(creates) == 10  # network, subnet, 3 firewalls, 2 addresses, 3 instances
    for c in creates:
        name = c.split(" create ")[1].split()[0]
        assert name.startswith("nc183-"), c
        assert "--project=netclaw-506315" in c
    instances = [c for c in creates if "instances create" in c]
    assert len(instances) == 3 and all("netclaw-spec=183" in c and "ubuntu-2404-lts-amd64" in c for c in instances)
    assert all("--region" not in c for c in instances)
    assert not any(re.search(r"\b(default|netclaw-r01)", c) for c in creates)
    mesh = next(c for c in creates if "nc183-allow-mesh" in c)
    assert "10.183.2.0/24" in mesh and "0.0.0.0/0" not in mesh
    ssh = next(c for c in creates if "nc183-allow-iap-ssh" in c)
    assert "35.235.240.0/20" in ssh and "0.0.0.0/0" not in ssh


def test_teardown_lists_first_and_deletes_nothing_without_confirm(stub):
    env = {"STUB_INSTANCES": "nc183-border-a\tnortheast-b\n", "STUB_FIREWALLS": "nc183-allow-mesh\n"}
    p, calls = stub("teardown", **env)
    assert p.returncode != 0 and mutating(calls) == [] and "nc183-border-a" in p.stdout and "Re-run with --confirm" in p.stderr


def test_teardown_deletes_only_owned_even_if_gcloud_returns_foreign_names(stub):
    env = {"STUB_INSTANCES": "nc183-border-a\tnorthamerica-northeast1-b\nnetclaw-r01-20261101\tnorthamerica-northeast1-a\n",
           "STUB_ADDRESSES": "nc183-ip-a\tnorthamerica-northeast1\nnetclaw-r01-20261101-primary\tnorthamerica-northeast1\n",
           "STUB_FIREWALLS": "nc183-allow-mesh\ndefault-allow-ssh\nnetclaw-r01-20261101-iap\n",
           "STUB_SUBNETS": "nc183-sub\tnorthamerica-northeast1\ndefault\tus-central1\n",
           "STUB_NETWORKS": "nc183-r09a\ndefault\n"}
    p, calls = stub("teardown", "--confirm", **env)
    assert p.returncode == 0, p.stderr
    deletes = [c for c in calls if " delete " in c]
    assert deletes, calls
    for c in deletes:
        assert " delete nc183-" in c, c
    joined = " ".join(deletes)
    assert "netclaw-r01" not in joined and "default" not in joined
    assert len(deletes) == 5


def test_ssh_refuses_non_owned_instances(stub):
    p, calls = stub("ssh", "netclaw-r01-20261101", "id")
    assert p.returncode != 0 and calls == [] and "not an owned" in p.stderr


def test_scripts_parse():
    for script in (DEPLOY, BOOTSTRAP):
        assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0


def test_bootstrap_encodes_the_verified_install_facts():
    text = BOOTSTRAP.read_text()
    for needle in ("OPENSHELL_COMPUTE_DRIVER=docker", "loginctl enable-linger", "gateway add", "--local --name node", "doctor check",
                   "usermod -aG docker", "user@${OP_UID}.service", "sha256sum -c", "DEFENSECLAW_VERSION", "--mode action",
                   "169.254.169.254", "--dport 53", "ID:-}\" = ubuntu", "Landlock ABI", "netclaw.spec=183"):
        assert needle in text, needle
    assert "REJECT" in text and "DOCKER-USER" in text
    assert "ANTHROPIC" not in text and "sk-ant" not in text


def test_teardown_with_empty_lists_still_deletes_what_exists(stub):
    env = {"STUB_INSTANCES": "", "STUB_ADDRESSES": "", "STUB_FIREWALLS": "", "STUB_SUBNETS": "nc183-sub\tnorthamerica-northeast1\n", "STUB_NETWORKS": "nc183-r09a\n"}
    p, calls = stub("teardown", "--confirm", **env)
    assert p.returncode == 0, p.stderr
    deletes = [c for c in calls if " delete " in c]
    assert len(deletes) == 2 and all(" delete nc183-" in c for c in deletes)
