#!/usr/bin/env python3
"""Contract tests for inventory sources, credentials and routing.

Spec 076 FR-017*, FR-018*, FR-019, FR-020, FR-021, FR-009..FR-011.
SC-006, SC-007, SC-007a. Run by tests/multivendor/run-tests.sh.

No device, no network, no framework. The generated-versus-operator distinction
gets the most attention here, because getting it wrong destroys operator work
silently — the worst failure mode in this feature.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp-servers" / "multivendor-cli-mcp"))

import credentials as creds  # noqa: E402
import routing  # noqa: E402
from inventory import sources as inv  # noqa: E402

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  ok   {label}"); PASS += 1
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else "")); FAIL += 1


def raises(fn, exc=inv.InventoryError):
    try:
        fn(); return None
    except exc as e:
        return str(e)
    except Exception as e:  # wrong exception type is still a failure
        return f"__WRONG_TYPE__{type(e).__name__}: {e}"


TMP = Path(tempfile.mkdtemp())

OPERATOR_YAML = """\
# operator-authored: hostnames and platforms only
edge-mt-01:
  hostname: 10.0.0.1
  platform: mikrotik_routeros
  groups: [edge, site-hq]
  credential_ref: default
fw-vyos-01:
  hostname: 10.0.0.2
  platform: vyos
  groups: [edge]
  credential_ref: edge-site
core-cisco-01:
  hostname: 10.0.0.3
  platform: cisco_xe
  groups: [core]
"""

print("=== Operator inventory loads, and reports its source (FR-017c) ===")
op = TMP / "inventory.yaml"
op.write_text(OPERATOR_YAML)
devices = inv.load_operator(op)
check("3 devices parsed", len(devices) == 3, f"got {len(devices)}")
check("all report source=operator", all(d.source is inv.Source.OPERATOR for d in devices))
mt = [d for d in devices if d.name == "edge-mt-01"][0]
check("hostname parsed", mt.hostname == "10.0.0.1", mt.hostname)
check("platform parsed", mt.platform == "mikrotik_routeros", str(mt.platform))
check("groups parsed as a list", mt.groups == ["edge", "site-hq"], str(mt.groups))
check("per-device credential_ref honoured (FR-020)",
      [d for d in devices if d.name == "fw-vyos-01"][0].credential_ref == "edge-site")

print("\n=== owning_server is computed per device (FR-009/FR-011) ===")
check("mikrotik owned by this server", mt.owning_server == "multivendor-cli", mt.owning_server)
cisco = [d for d in devices if d.name == "core-cisco-01"][0]
check("cisco_xe owned by pyats", cisco.owning_server == "pyats", cisco.owning_server)

print("\n=== Credentials are REJECTED in any inventory source (FR-017d, SC-006) ===")
for field in ("password", "enable_secret", "api_key", "private_key", "token"):
    bad = TMP / f"bad-{field}.yaml"
    bad.write_text(f"d1:\n  hostname: 1.1.1.1\n  platform: vyos\n  {field}: hunter2\n")
    msg = raises(lambda p=bad: inv.load_operator(p))
    check(f"{field!r} in inventory is rejected", bool(msg) and "credential" in (msg or "").lower(),
          str(msg)[:70])
check("'credential_ref' itself is NOT treated as a secret",
      not creds.looks_like_secret_field("credential_ref"))
check("'password' is treated as a secret", creds.looks_like_secret_field("password"))

print("\n=== Generated vs operator files are never confused (FR-017a/b) ===")
gen = TMP / "inventory.generated.yaml"
gen.write_text(f"{inv.GENERATED_MARKER}: true\nd1:\n  hostname: 2.2.2.2\n  platform: vyos\n")
check("generated file is detected as generated", inv.is_generated(gen))
check("operator file is NOT detected as generated", not inv.is_generated(op))
msg = raises(lambda: inv.load_operator(gen))
check("loading a GENERATED file as operator is refused", bool(msg) and "cache" in (msg or "").lower(),
      str(msg)[:80])
msg = raises(lambda: inv.load_generated(op))
check("loading an OPERATOR file as generated is refused",
      bool(msg) and "operator-authored" in (msg or "").lower(), str(msg)[:80])
gd = inv.load_generated(gen)
check("generated devices report source=generated",
      all(d.source is inv.Source.GENERATED for d in gd) and len(gd) == 1)
check("the marker key is not parsed as a device", all(d.name != inv.GENERATED_MARKER for d in gd))

print("\n=== Absent devices are reported, never guessed (FR-021) ===")
msg = raises(lambda: inv.find(devices, "does-not-exist"))
check("missing device raises, naming it", bool(msg) and "does-not-exist" in (msg or ""))
check("present device is found", inv.find(devices, "edge-mt-01").name == "edge-mt-01")

print("\n=== Malformed inventory fails loudly ===")
for content, label in (
    ("d1:\n  platform: vyos\n", "no hostname"),
    ("just-a-string\n", "not key: value"),
):
    bad = TMP / f"malformed-{label.replace(' ','-')}.yaml"
    bad.write_text(content)
    check(f"{label} rejected", bool(raises(lambda p=bad: inv.load_operator(p))))

print("\n=== Routing: writes single-pathed, normalized reads permitted (FR-008/009/010) ===")
R, Op = routing.route, routing.Operation
d = R("cisco_xe", Op.WRITE)
check("WRITE to cisco_xe refused", d.refused)
check("  ...naming pyats as owner", d.owning_server == "pyats", d.owning_server)
check("  ...with a reason mentioning one write path",
      "one write path" in (d.reason or ""), (d.reason or "")[:70])
check("NORMALIZED_READ on cisco_xe PERMITTED (the exception)",
      R("cisco_xe", Op.NORMALIZED_READ).permitted)
check("RAW_READ on cisco_xe refused", R("cisco_xe", Op.RAW_READ).refused)
check("WRITE to juniper_junos refused naming junos-mcp",
      R("juniper_junos", Op.WRITE).refused and R("juniper_junos", Op.WRITE).owning_server == "junos-mcp")
for p in ("mikrotik_routeros", "vyos", "sonic", "nokia_srlinux", None):
    dd = R(p, Op.WRITE)
    check(f"WRITE to {p!r} permitted (unowned)", dd.permitted, dd.reason or "")
payload = routing.refusal_payload("core-01", "cisco_xe", R("cisco_xe", Op.WRITE))
check("refusal payload has status=refused", payload["status"] == "refused")
check("refusal payload names owning_server", payload["owning_server"] == "pyats")

print("\n=== Credentials: env fallback works without Vault (FR-018, SC-007a) ===")
for k in list(os.environ):
    if k.startswith("MULTIVENDOR_") or k == "VAULT_ADDR":
        del os.environ[k]
msg = raises(lambda: creds.resolve("default"), creds.CredentialError)
check("no credential configured -> clear error", bool(msg) and "MULTIVENDOR_USERNAME" in (msg or ""))
check("  ...error says secrets must not be in inventory",
      "never be placed in an inventory" in (msg or ""), (msg or "")[:60])

os.environ["MULTIVENDOR_USERNAME"] = "netops"
os.environ["MULTIVENDOR_PASSWORD"] = "s3cret"
c = creds.resolve("default")
check("env credential resolves with NO Vault configured", c.username == "netops")
check("  ...and reports path=environment (FR-018a)", c.path is creds.CredentialPath.ENVIRONMENT)
check("posture() exposes no secret",
      "s3cret" not in str(c.posture()) and c.posture()["has_password"] is True)
check("repr() redacts secrets", "s3cret" not in repr(c), repr(c))
check("str() redacts secrets", "s3cret" not in str(c))

os.environ["MULTIVENDOR_EDGE_SITE_USERNAME"] = "siteadmin"
os.environ["MULTIVENDOR_EDGE_SITE_PASSWORD"] = "other"
c2 = creds.resolve("edge-site")
check("reference-scoped credential overrides the generic one (FR-020)",
      c2.username == "siteadmin", c2.username)
check("generic reference still resolves generically", creds.resolve("default").username == "netops")

print(f"\n  passed: {PASS}\n  failed: {FAIL}")
sys.exit(1 if FAIL else 0)
