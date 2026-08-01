#!/usr/bin/env python3
"""Contract tests for the multivendor command filter.

Spec 076 FR-022/FR-023/FR-029, SC-008. Run by tests/multivendor/run-tests.sh.

No device, no network, no framework — pure functions over inputs, asserted with
plain Python so this runs in a bare CI container under the server's own venv.

The test that matters most is ORDERING: `show version; write erase` begins with
an allowlisted verb, so an implementation that checks the allowlist before
checking for chaining would permit it. That case is not hypothetical — it is the
single most likely way this filter gets broken by a later refactor.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mcp-servers" / "multivendor-cli-mcp"))

from policy.filter import DenyRule, Mode, evaluate  # noqa: E402
from policy.platform_deny import deny_tokens_for, is_modelled  # noqa: E402

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ok   {label}")
        PASS += 1
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1


def denied(cmd, platform=None, mode=Mode.READ_ONLY):
    return evaluate(cmd, platform, mode)


print("=== Ordering: chaining is rejected BEFORE the allowlist (contract) ===")
# The critical case. First token is allowlisted; the payload is catastrophic.
v = denied("show version; write erase", "cisco_ios")
check("'show version; write erase' is DENIED", not v.allowed)
check("  ...and denied for CHAINING, not denylist", v.rule is DenyRule.CHAINING,
      f"got rule={v.rule}")
for payload, label in [
    ("show version && reload", "shell AND"),
    ("show version || reload", "shell OR"),
    ("show run > /tmp/x", "redirection"),
    ("show run < /tmp/x", "input redirection"),
    ("show version `reload`", "backtick"),
    ("show version $(reload)", "substitution"),
    ("show version\nreload", "embedded newline"),
    ("show version & reload", "background"),
]:
    v = denied(payload, "cisco_ios")
    check(f"chaining via {label} denied", not v.allowed and v.rule is DenyRule.CHAINING,
          f"got allowed={v.allowed} rule={v.rule}")

print("\n=== A single pipe is a display filter, not a bypass ===")
v = denied("show running-config | include bgp", "cisco_ios")
check("'show run | include bgp' is ALLOWED", v.allowed,
      f"denied_reason={v.denied_reason}")

print("\n=== Read-only mode blocks non-allowlisted verbs (FR-022) ===")
for cmd in ("configure terminal", "set interfaces ge-0/0/0 disable", "commit"):
    v = denied(cmd, "cisco_ios")
    check(f"{cmd!r} denied in read-only", not v.allowed)
v = denied("show version", "cisco_ios")
check("'show version' allowed in read-only", v.allowed, v.denied_reason or "")

print("\n=== Denylist fires per platform, not just Cisco (FR-023, SC-008) ===")
cases = [
    ("cisco_ios", "write erase"),
    ("cisco_ios", "reload"),
    ("juniper_junos", "request system zeroize"),
    ("vyos", "delete interfaces eth0"),
    ("mikrotik_routeros", "/system reset-configuration"),
    ("nokia_srlinux", "tools system configuration"),
    ("dell_sonic", "config erase"),
    ("extreme_exos", "unconfigure switch"),
    ("huawei_vrp", "reset saved-configuration"),
    ("ubiquiti_edge", "format"),
    ("linux", "rm -rf /"),
]
for platform, cmd in cases:
    v = denied(cmd, platform, Mode.WRITE_ENABLED)  # write mode: only denylist can stop it
    check(f"[{platform}] {cmd!r} denied even in WRITE mode",
          not v.allowed and v.rule is DenyRule.DENYLIST,
          f"allowed={v.allowed} rule={v.rule}")

print("\n=== Substring false positives are NOT blocked ===")
# 'show reload-reason' contains 'reload' but the verb is 'show'.
v = denied("show reload-reason", "cisco_ios")
check("'show reload-reason' allowed (contains 'reload' but verb is 'show')", v.allowed,
      v.denied_reason or "")
v = denied("show system uptime", "vyos")
check("'show system uptime' allowed on vyos (contains 'system')", v.allowed,
      v.denied_reason or "")

print("\n=== Unmodelled platforms still get the universal baseline ===")
v = denied("reload", "some_unknown_vendor_os", Mode.WRITE_ENABLED)
check("'reload' denied on an unmodelled platform", not v.allowed and v.rule is DenyRule.DENYLIST)
check("  ...and reported as unmodelled", not v.platform_modelled)
check("universal deny is non-empty for unknown platform", len(deny_tokens_for("nope")) > 0)
check("is_modelled('cisco_ios') is True", is_modelled("cisco_ios"))
check("is_modelled(None) is False", not is_modelled(None))

print("\n=== Shell escape is denied everywhere ===")
for cmd in ("bash", "sh", "shell", "start-shell", "run bash"):
    v = denied(cmd, "cisco_ios", Mode.WRITE_ENABLED)
    check(f"{cmd!r} denied", not v.allowed, f"rule={v.rule}")

print("\n=== Case and whitespace cannot evade the denylist ===")
for cmd in ("RELOAD", "  reload  ", "ReLoAd", "WRITE   ERASE"):
    v = denied(cmd, "cisco_ios", Mode.WRITE_ENABLED)
    check(f"{cmd!r} denied", not v.allowed, f"rule={v.rule}")

print("\n=== Degenerate input ===")
check("empty command denied", not denied("", "cisco_ios").allowed)
check("whitespace-only denied", not denied("   ", "cisco_ios").allowed)
check("over-long command denied", not denied("show " + "x" * 600, "cisco_ios").allowed)

print("\n=== Default mode is read-only when unspecified (FR-022) ===")
v = evaluate("configure terminal", "cisco_ios")  # no mode argument
check("omitting mode yields read-only behaviour", not v.allowed and v.rule is DenyRule.NOT_READ_ONLY)

print(f"\n  passed: {PASS}\n  failed: {FAIL}")
sys.exit(1 if FAIL else 0)
