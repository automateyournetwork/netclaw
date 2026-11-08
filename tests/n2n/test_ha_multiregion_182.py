"""Spec 182 infra scripts: plan/apply/teardown guards, cost, DNS, RTT. No network, no gcloud."""
import importlib.util
import io
import json
import os

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, "scripts", fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gcp = load("ha_gcp", "ha-gcp-multiregion.py")
cost = load("ha_cost", "ha-cost-estimate.py")
dns = load("ha_dns", "ha-dns-godaddy.py")
rtt = load("ha_rtt", "ha-rtt-estimate.py")


class Runner:
    def __init__(self, existing=(), outputs=None):
        self.calls, self.existing, self.outputs = [], set(existing), outputs or {}

    def __call__(self, argv):
        self.calls.append(list(argv))
        if "describe" in argv:
            name = argv[argv.index("describe") + 1]
            if name in self.existing:
                return 0, self.outputs.get(name, name)
            return 1, ""
        return 0, self.outputs.get(" ".join(argv), "")


MUTATING = ("create", "delete", "update", "add-", "remove-", "set-")


def mutating(calls):
    return [c for c in calls if any(w in c for w in ("create", "delete", "update", "start", "stop", "reset"))]


# ---- plan
def test_plan_has_three_borders_in_three_regions():
    plan = gcp.build_plan()
    inst = [p for p in plan if p["kind"] == "instance"]
    assert {i["region"] for i in inst} == {"northamerica-northeast1", "europe-west1", "asia-southeast1"}
    assert len(inst) == 3 and all(i["machine_type"] == "e2-medium" for i in inst)


def test_every_resource_labelled_or_prefixed():
    for p in gcp.build_plan():
        assert p["name"].startswith("nc182-"), p
        if p["labelable"]:
            assert "netclaw-spec=182" in p["labels"], p


def test_no_world_open_ssh_or_rdp():
    for p in gcp.build_plan():
        if p["kind"] != "firewall":
            continue
        if "0.0.0.0/0" in p["source_ranges"]:
            assert all(a in ("tcp:443", f"tcp:{gcp.IN2N_PORT}") for a in p["allow"])
    iap = [p for p in gcp.build_plan() if p["name"].endswith("allow-iap-ssh")][0]
    assert iap["source_ranges"] == [gcp.IAP_RANGE]


def test_plan_mode_is_read_only():
    r = Runner()
    out = []
    assert gcp.cmd_plan(r, out=out.append) == 0
    assert r.calls and mutating(r.calls) == []
    assert any("[create]" in line for line in out)


def test_plan_never_touches_old_environment():
    names = " ".join(p["name"] for p in gcp.build_plan())
    for banned in ("netclaw-r01", "equinix", "pyats-mcp", "gateway5", "drawio"):
        assert banned not in names


# ---- apply guards
def test_apply_refuses_without_confirm_cost(tmp_path):
    r = Runner(); out = []
    assert gcp.cmd_apply(r, False, out=out.append) == 2
    assert r.calls == []


def test_apply_refuses_without_g1_file(tmp_path):
    r = Runner(); out = []
    assert gcp.cmd_apply(r, True, g1_path=str(tmp_path / "missing.md"), out=out.append) == 2
    assert mutating(r.calls) == []


def test_apply_creates_in_order_with_g1(tmp_path):
    g1 = tmp_path / "g1.md"; g1.write_text("Gate: G1\nApproved by: owner\n")
    r = Runner(outputs={n: "34.1.1.%d" % i for i, n in enumerate(["nc182-ip-nne1", "nc182-ip-ew1", "nc182-ip-ase1"], 1)})
    # addresses must resolve for the mesh firewall rule; Runner describe says missing until created, so mark as existing after creation
    created = []

    def runner(argv):
        if "describe" in argv:
            name = argv[argv.index("describe") + 1]
            if name.startswith("nc182-ip-") and name in created:
                return 0, "34.1.1.%d" % (len(name))
            return (0, name) if name in created else (1, "")
        if "create" in argv:
            created.append(argv[argv.index("create") + 1])
            return 0, ""
        return 0, ""
    out = []
    assert gcp.cmd_apply(runner, True, g1_path=str(g1), out=out.append) == 0
    assert created[0] == "nc182-r09" and created[-3:] == ["nc182-border-nne1", "nc182-border-ew1", "nc182-border-ase1"]
    assert "nc182-allow-mesh" in created


def test_apply_stops_on_failure(tmp_path):
    g1 = tmp_path / "g1.md"; g1.write_text("Gate: G1\nApproved by: owner\n")
    calls = []

    def runner(argv):
        calls.append(argv)
        if "describe" in argv:
            return 1, ""
        return 1, ""
    assert gcp.cmd_apply(runner, True, g1_path=str(g1), out=lambda *_: None) == 1
    assert len([c for c in calls if "create" in c]) == 1


# ---- teardown
def owned_runner():
    outs = {
        "gcloud --project netclaw-506315 compute instances list --filter labels.netclaw-spec=182 --format value(name,zone.basename())": "nc182-border-nne1 northamerica-northeast1-a\n",
        "gcloud --project netclaw-506315 compute addresses list --filter labels.netclaw-spec=182 --format value(name,region.basename())": "nc182-ip-nne1 northamerica-northeast1\n",
        "gcloud --project netclaw-506315 compute firewall-rules list --filter name~^nc182- --format value(name)": "nc182-allow-public\n",
        "gcloud --project netclaw-506315 compute networks subnets list --filter name~^nc182- --format value(name,region.basename())": "nc182-sub-nne1 northamerica-northeast1\n",
        "gcloud --project netclaw-506315 compute networks list --filter name~^nc182- --format value(name)": "nc182-r09\n",
    }
    return Runner(outputs=outs)


def test_teardown_list_is_read_only():
    r = owned_runner(); out = []
    assert gcp.cmd_teardown(r, True, False, "", out=out.append) == 0
    assert mutating([c for c in r.calls]) == []
    assert any("nc182-border-nne1" in line for line in out)


def test_teardown_delete_needs_matching_digest():
    r = owned_runner(); out = []
    assert gcp.cmd_teardown(r, False, True, "wrong", out=out.append) == 2
    assert not [c for c in r.calls if "delete" in c]


def test_teardown_delete_with_digest_deletes_only_owned_in_order():
    r = owned_runner()
    found = gcp.owned(r)
    digest = gcp.list_digest(found)
    r2 = owned_runner(); out = []
    assert gcp.cmd_teardown(r2, False, True, digest, out=out.append) == 0
    dels = [c for c in r2.calls if "delete" in c]
    assert [c[c.index("delete") - 1] for c in dels] == ["instances", "addresses", "firewall-rules", "subnets", "networks"]
    assert all(c[c.index("delete") + 1].startswith("nc182-") for c in dels)


# ---- cost
def test_cost_total_and_warning_not_failure(capsys):
    items = cost.lines()
    t = cost.total(items)
    assert 90 < t < 200
    assert cost.main([]) == 0
    assert cost.main(["--fail-above", "10"]) == 1


def test_cost_warns_above_300(monkeypatch, capsys):
    monkeypatch.setattr(cost, "EGRESS_PER_BORDER", 500.0)
    assert cost.main([]) == 0
    assert "WARNING" in capsys.readouterr().out


# ---- DNS
IDS = ["nne1=3fa9c2", "ew1=b71d04", "ase1=9c2e55"]
IPS = ["nne1=34.1.1.1", "ew1=34.2.2.2", "ase1=34.3.3.3"]


class FakeClient:
    def __init__(self, existing=None):
        self.existing, self.puts = existing or {}, []

    def a_records(self):
        return dict(self.existing)

    def put_a(self, label, ip):
        self.puts.append((label, ip)); return 200


def args(*extra):
    out = []
    for i in IDS: out += ["--id6", i]
    for i in IPS: out += ["--ip", i]
    return out + list(extra)


def test_dns_names_pattern_and_refusal():
    assert dns.wanted(dns.parse_id6(IDS), dns.parse_ips(IPS))[0][1] == "nne1-3fa9c2.automateyournetwork.com"
    for bad in ("nne1=ZZZZZZ", "xx1=3fa9c2", "nne1=3FA9C2", "nne1=3fa9c"):
        with pytest.raises(ValueError):
            dns.parse_id6([bad])


def test_dns_plan_is_get_only():
    c = FakeClient(); out = []
    assert dns.main(["plan"] + args(), client=c, out=out.append) == 0
    assert c.puts == [] and any("[create" in l for l in out)


def test_dns_apply_requires_flag():
    c = FakeClient()
    assert dns.main(["apply"] + args(), client=c, out=lambda *_: None) == 2
    assert c.puts == []
    assert dns.main(["apply", "--apply"] + args(), client=c, out=lambda *_: None) == 0
    assert len(c.puts) == 3


def test_dns_conflict_refused_and_noop_skipped():
    c = FakeClient({"nne1-3fa9c2": "9.9.9.9"})
    assert dns.main(["apply", "--apply"] + args(), client=c, out=lambda *_: None) == 2
    assert c.puts == []
    c2 = FakeClient({"nne1-3fa9c2": "34.1.1.1"})
    assert dns.main(["apply", "--apply"] + args(), client=c2, out=lambda *_: None) == 0
    assert [p[0] for p in c2.puts] == ["ew1-b71d04", "ase1-9c2e55"]


def test_dns_never_prints_secret(capsys):
    secret = "gd_pat_SUPERSECRETVALUE"
    env = {"GODADDY_PAT": secret}

    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"[]"
    seen = {}

    def opener(req, timeout=0):
        seen["auth"] = req.get_header("Authorization")
        return Resp()
    out = []
    rc = dns.main(["plan"] + args(), client=dns.Client(dns.auth_header(env), opener), out=out.append)
    assert rc == 0 and seen["auth"] == "Bearer " + secret
    assert secret not in "\n".join(out) and secret not in capsys.readouterr().out


def test_dns_auth_precedence_and_missing(tmp_path):
    assert dns.auth_header({"GODADDY_API_KEY": "k", "GODADDY_API_SECRET": "s"}) == "sso-key k:s"
    assert dns.auth_header({"GODADDY_PAT": "p", "GODADDY_API_KEY": "k", "GODADDY_API_SECRET": "s"}) == "Bearer p"
    assert dns.auth_header({}) is None


def test_dns_missing_credential_returns_3(monkeypatch):
    monkeypatch.setattr(dns, "load_env", lambda path=None: {})
    out = []
    assert dns.main(["plan"] + args(), out=out.append) == 3


# ---- RTT
def test_rtt_estimates_marked_and_bounded():
    t = rtt.table()
    assert all(p["source"] == "estimate" for p in t["pairs"])
    assert 100 <= t["recommended_admission_ms_if_estimates_hold"] <= 10000
    assert rtt.leader_budget("ase1")["admission_estimate_ms"] > rtt.leader_budget("nne1")["admission_estimate_ms"]
    assert rtt.main(["--json"]) == 0
