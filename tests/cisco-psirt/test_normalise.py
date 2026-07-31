#!/usr/bin/env python3
"""Offline contract tests for the PSIRT version normaliser.

Spec 078 T018. No network — these must never consume the 30/min rate budget.

The cases below are not invented. Every accepted/rejected form was measured against
the live API, and two of these tests exist because they caught real bugs:

  * `banner_with_paren` — an unanchored `re.sub` deleted the whole banner, so valid
    input normalised to nothing.
  * `paren_token_not_truncated` — a trailing `\\b` could not match after `)`, so
    `17.3(1)` silently became `17.3`. The truncated version queried *successfully*
    and returned a plausible count, which is the quiet wrongness FR-009a targets.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "mcp-servers", "cisco-psirt-mcp"))

from normalise import (  # noqa: E402
    OSTYPE_FORMAT,
    SUPPORTED_OSTYPES,
    VERIFIED_OSTYPES,
    collection_note,
    is_supported,
    is_verified,
    normalise,
    unsupported_reason,
)

PASS = FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        print(f"  ok   {label}")
        PASS += 1
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1


print("### Per-family version formats (every row a measured live 200) ###")
# ostype, input, expected normalised output
ACCEPTED = [
    # iosxe: dotted. 17.3(1) is REJECTED by the API, so it must be converted.
    ("iosxe", "17.3.1", "17.3.1"),
    ("iosxe", "17.03.01", "17.03.01"),
    ("iosxe", "17.3(1)", "17.3.1"),
    ("iosxe", "17.3.1a", "17.3.1a"),
    # ios: parenthesised, letter suffix OUTSIDE. 15.2.4E is rejected by the API.
    ("ios", "15.2(4)E", "15.2(4)E"),
    ("ios", "15.2.4E", "15.2(4)E"),
    ("ios", "15.2(4)E10", "15.2(4)E10"),
    # nxos: parenthesised. 9.3.5 is rejected by the API.
    ("nxos", "9.3(5)", "9.3(5)"),
    ("nxos", "9.3.5", "9.3(5)"),
    # asa: dotted. 9.16(1) is rejected by the API.
    ("asa", "9.16.1", "9.16.1"),
    ("asa", "9.16(1)", "9.16.1"),
    # ftd / fmc: dotted.
    ("ftd", "7.0.1", "7.0.1"),
    ("fmc", "7.0.1", "7.0.1"),
    # aci: parenthesised with the letter INSIDE. 15.2(3)e is rejected by the API.
    ("aci", "15.2(3e)", "15.2(3e)"),
    ("aci", "15.2.3e", "15.2(3e)"),
]
for ostype, raw, expected in ACCEPTED:
    got = normalise(ostype, raw)
    check(f"{ostype} {raw!r} -> {expected!r}",
          got.ok and got.value == expected,
          f"got ok={got.ok} value={got.value!r}")

print("\n### Banner extraction — real `show version` output ###")
banners = [
    ("iosxe", "Cisco IOS XE Software, Version 17.03.01", "17.03.01"),
    ("iosxe", "Cisco IOS Software [Amsterdam], Version 17.3(1), RELEASE SOFTWARE (fc2)",
     "17.3.1"),
    ("ios", "Cisco IOS Software, Version 15.2(4)E10, RELEASE SOFTWARE (fc2)",
     "15.2(4)E10"),
]
for ostype, banner, expected in banners:
    got = normalise(ostype, banner)
    check(f"{ostype} banner -> {expected!r}", got.ok and got.value == expected,
          f"got {got.value!r}")

# Regression: the parenthesised build must survive tokenisation intact. A trailing
# `\b` silently dropped it, producing a version that queries fine and answers the
# wrong question.
got = normalise("nxos", "9.3(5)")
check("paren_token_not_truncated (9.3(5) does not become 9.3)",
      got.value == "9.3(5)", f"got {got.value!r}")

print("\n### FR-009a: a parse failure is NEVER an empty advisory list ###")
for bad in ["garbage", "", None, "   ", "no digits here", "Version unknown"]:
    got = normalise("iosxe", bad)
    check(f"{bad!r} -> normalisation_failed", got.failed and got.value is None,
          f"got ok={got.ok} value={got.value!r}")
    check(f"{bad!r} explains why", bool(got.reason and len(got.reason) > 20))

print("\n### FR-004: iosxr is refused, not attempted ###")
check("iosxr unsupported", not is_supported("iosxr"))
check("iosxr reason mentions 404", "404" in unsupported_reason("iosxr"))
check("iosxr reason offers check_cve", "check_cve" in unsupported_reason("iosxr"))
# Each near-miss spelling must name the thing to use instead, not just say "no".
for alias, expected_hint in [("ios-xr", "iosxr"), ("nx-os", "nxos"),
                             ("ios-xe", "iosxe"), ("apic", "aci")]:
    check(f"{alias} points at {expected_hint!r}",
          alias not in SUPPORTED_OSTYPES
          and expected_hint in unsupported_reason(alias),
          f"got {unsupported_reason(alias)!r}")

print("\n### FR-004a: the support and verification tables ###")
check("exactly seven supported OSTypes", len(SUPPORTED_OSTYPES) == 7,
      f"got {SUPPORTED_OSTYPES}")
check("iosxr absent from the supported set", "iosxr" not in SUPPORTED_OSTYPES)
check("every supported family has a format rule",
      set(OSTYPE_FORMAT) == set(SUPPORTED_OSTYPES))
check("every verified family is supported",
      VERIFIED_OSTYPES <= set(SUPPORTED_OSTYPES))
check("iosxe is verified", is_verified("iosxe"))
check("aci carries a collection note (switch vs APIC version)",
      bool(collection_note("aci")) and "APIC" in collection_note("aci"))

print("\n### Case and whitespace tolerance ###")
check("uppercase ostype accepted", is_supported("IOSXE"))
check("padded ostype accepted", is_supported("  iosxe  "))
got = normalise("iosxe", "  17.3.1  ")
check("padded version normalises", got.ok and got.value == "17.3.1")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
