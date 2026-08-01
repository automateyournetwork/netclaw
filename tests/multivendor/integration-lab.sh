#!/usr/bin/env bash
# Live-device integration test for spec 076 (R1). Verifies SC-001.
#
# Requires the R1 lab — see labs/multivendor-r1/README.md:
#   - Nokia SR Linux via containerlab (172.20.20.11/.12)   native NOS CLI
#   - FRR with sshd on port 2222                            shell-hosted NOS
#
# SKIPS cleanly when the lab is absent, so it is safe in CI. It is deliberately
# NOT part of run-tests.sh: that suite must pass with no devices at all.
#
# Two platform families on purpose. FRR is reached through netmiko's `linux`
# driver (a shell); SR Linux is a native network CLI with its own prompt
# handling. One of each is much stronger evidence than two of the same, because
# they exercise different halves of the driver abstraction.
#
# Exit codes are captured directly, never through a pipe.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PY="$REPO_ROOT/mcp-servers/multivendor-cli-mcp/.venv/bin/python"
PASS=0; FAIL=0; SKIP=0

reachable() { timeout 5 bash -c "echo > /dev/tcp/$1/$2" 2>/dev/null; }

[ -x "$VENV_PY" ] || { echo "SKIP: server venv missing"; exit 0; }

SRL_UP=0; FRR_UP=0
reachable 172.20.20.11 22 && SRL_UP=1
reachable 127.0.0.1 2222 && FRR_UP=1

if [ "$SRL_UP" -eq 0 ] && [ "$FRR_UP" -eq 0 ]; then
    echo "SKIP: no R1 lab devices reachable (see labs/multivendor-r1/README.md)"
    exit 0
fi
echo "lab: SR Linux=$SRL_UP  FRR=$FRR_UP"
echo

# The two credentials below are LAB FIXTURES for disposable containers, not
# secrets, and are deliberately committed so this test runs standalone:
#   NokiaSrl1!  — SR Linux container image's publicly documented default
#   netops123   — set by labs/multivendor-r1/frr-ssh/Dockerfile in this repo
# Real device credentials NEVER go here. They belong in a gitignored .env and are
# read via credential_ref (see credentials.py); the server rejects inventory
# records containing credential-shaped fields at all.
export MULTIVENDOR_INVENTORY_SOURCE=operator
export MULTIVENDOR_INVENTORY_PATH="$REPO_ROOT/labs/multivendor-r1/inventory.yaml"
export MULTIVENDOR_SRLINUX_USERNAME=admin
export MULTIVENDOR_SRLINUX_PASSWORD='NokiaSrl1!'
export MULTIVENDOR_FRRLAB_USERNAME=netops
export MULTIVENDOR_FRRLAB_PASSWORD=netops123
export MULTIVENDOR_FRR_LAB_01_PORT=2222
export SRL_UP FRR_UP

"$VENV_PY" - <<'PY'
import logging, os, sys
sys.path.insert(0, os.path.join(os.environ.get("REPO_ROOT", "."),
                                "mcp-servers", "multivendor-cli-mcp"))
sys.path.insert(0, "mcp-servers/multivendor-cli-mcp")
logging.disable(logging.INFO)
import server

P = F = 0
def check(label, cond, detail=""):
    global P, F
    if cond: print(f"  ok   {label}"); P += 1
    else:    print(f"  FAIL {label}" + (f" — {detail}" if detail else "")); F += 1

srl = os.environ.get("SRL_UP") == "1"
frr = os.environ.get("FRR_UP") == "1"
families = 0

print("=== inventory resolves and attributes ownership ===")
r = server.list_devices()
check("source is reported", r["source_used"] == "operator", r["source_used"])
owners = {d["name"]: d["owning_server"] for d in r["devices"]}
check("cisco device owned by pyats", owners.get("cml-r1") == "pyats", str(owners))
check("srl1 owned by this server", owners.get("srl1") == "multivendor-cli", str(owners))

if srl:
    print("\n=== SC-001: Nokia SR Linux — NATIVE network CLI ===")
    families += 1
    x = server.run_command("srl1", "show version")
    check("show version returns live output", x["status"] == "ok" and x.get("output"),
          f"{x['status']}: {str(x.get('error'))[:70]}")
    x = server.run_command("srl1", "show interface brief")
    check("show interface brief returns live output", x["status"] == "ok")
    x = server.check_reachability("srl1")
    check("check_reachability: tcp+auth ok", x["tcp"] and x["auth"], str(x.get("error"))[:70])
    check("  ...driver is nokia_srl", x["driver"] == "nokia_srl", str(x["driver"]))
    # SR Linux config destruction — the command the platform-key bug had missed
    x = server.run_command("srl1", "tools system configuration")
    check("'tools system configuration' DENIED", x["status"] == "denied",
          str(x.get("denied_reason"))[:70])
    x = server.run_command("srl1", "show version; reload")
    check("chaining DENIED before connecting", x["status"] == "denied"
          and "chaining" in (x.get("denied_reason") or ""))

if frr:
    print("\n=== SC-001: FRR — SHELL-HOSTED NOS via the linux driver ===")
    families += 1
    x = server.run_command("frr-lab-01", 'vtysh -c "show ip route"')
    check("vtysh read returns live routing table", x["status"] == "ok" and x.get("output"),
          f"{x['status']}: {str(x.get('error'))[:70]}")
    x = server.run_command("frr-lab-01", 'vtysh -c "configure terminal"')
    check("wrapped config command DENIED (wrapper unwrapped)", x["status"] == "denied",
          str(x.get("denied_reason"))[:70])
    x = server.run_command("frr-lab-01", 'vtysh -c "reload"')
    check("wrapped destructive command DENIED", x["status"] == "denied")
    x = server.run_command("frr-lab-01", "rm -rf /")
    check("'rm -rf /' DENIED", x["status"] == "denied")

print("\n=== Phase 5: NAPALM normalized facts (FR-006/007/008) ===")
x = server.get_facts("cml-r1", ["get_facts", "get_interfaces"])
check("normalized read on Cisco PERMITTED (FR-008 exception)", x["status"] == "ok",
      f"{x['status']}: {str(x.get('error'))[:60]}")
check("  ...via the napalm ios driver", x.get("napalm_driver") == "ios", str(x.get("napalm_driver")))
gf = next((f for f in x.get("facts", []) if f["getter"] == "get_facts"), {})
check("  ...returning real data with provenance=napalm",
      gf.get("available") and gf.get("provenance") == "napalm" and gf.get("data", {}).get("hostname"))
if srl:
    y = server.get_facts("srl1", ["get_facts", "get_bgp_neighbors"])
    check("SR Linux gap REPORTED not omitted (FR-007)",
          len(y.get("facts", [])) == 2 and all(not f["available"] for f in y["facts"]),
          str(len(y.get("facts", []))))
    check("  ...every gap carries a reason", all(f["gap_reason"] for f in y["facts"]))
    check("  ...and provenance is never faked as napalm",
          all(f["provenance"] is None for f in y["facts"]))
    keys_cisco = set(gf.keys()); keys_srl = set(y["facts"][0].keys())
    check("cross-vendor rows share ONE shape (FR-006)", keys_cisco == keys_srl,
          f"{keys_cisco ^ keys_srl}")

print("\n=== Phase 6: fleet fan-out (FR-013/014/015) ===")
fl = server.run_fleet("cml", getters=["get_facts"])
check("every targeted device appears in results (FR-014)",
      fl["requested"] == fl["returned"], f"{fl['requested']} vs {fl['returned']}")
check("  ...an unreachable device is isolated, not fatal",
      fl["summary"].get("ok", 0) >= 1 and fl["summary"].get("unreachable", 0) >= 1,
      str(fl["summary"]))

print("\n=== Phase 8: change gates (FR-024/025/025a/025c, Principle III) ===")
import tools.change as chg
os.environ["MULTIVENDOR_WRITE_ENABLED"] = "true"
r = chg.apply_config("cml-r1", "hostname NEW", approved_by="tester")
check("write to Cisco REFUSED by routing", r["status"] == "refused", r["status"])
r = chg.apply_config("prod-srl-01", "set / system information location x", approved_by="tester")
check("production + human approval but NO CR -> blocked (Principle III)",
      r["status"] == "cr_not_approved", r["status"])
check("  ...classified production", r.get("classification") == "production", str(r.get("classification")))
r = chg.apply_config("prod-srl-01", "set / system information location x",
                     change_request="CHG9999999", approved_by="tester")
check("bogus CR rejected by a real ServiceNow lookup",
      r["status"] == "cr_not_approved" and "not found" in (r.get("cr_reason") or ""),
      str(r.get("cr_reason"))[:60])
if srl:
    r = chg.apply_config("srl1", "set / system information location lab")
    check("lab device is CR-exempt but still needs human approval",
          r["status"] == "awaiting_approval" and r.get("classification") == "lab", r["status"])
    r = chg.apply_config("srl1", "set / system information location lab", approved_by="tester")
    # SR Linux uses a candidate datastore needing an explicit commit, which this
    # verifier does not issue — so the honest outcome is INCONCLUSIVE with a
    # rollback, not "verified". Reporting it as applied would be a false claim.
    check("lab + approval -> gates pass, baseline captured, outcome honest",
          r.get("baseline_ref") and r["status"] in ("verified", "verification_inconclusive"),
          f"{r['status']}: {str(r.get('error'))[:70]}")
    check("  ...and a commit-required platform is labelled inconclusive, not failed",
          r["status"] != "verification_failed", r["status"])
    check("  ...with rollback attempted (FR-027)", r.get("rollback") in
          ("rolled_back", "rollback_failed", "not_needed"), str(r.get("rollback")))
r = chg.apply_config("srl1", "reload", approved_by="tester")
check("destructive config DENIED even with approval", r["status"] == "denied", r["status"])
del os.environ["MULTIVENDOR_WRITE_ENABLED"]

print("\n=== routing: writes single-pathed (FR-010) ===")
x = server.run_command("cml-r1", "show version")
check("raw read on cisco_xe REFUSED", x["status"] == "refused", x["status"])
check("  ...naming pyats", x.get("owning_server") == "pyats", str(x.get("owning_server")))

print(f"\n  platform families verified live: {families}")
print(f"  passed: {P}\n  failed: {F}")
sys.exit(1 if F else 0)
PY
rc=$?
echo
[ "$rc" -eq 0 ] && echo "integration: PASS" || echo "integration: FAIL"
exit $rc
