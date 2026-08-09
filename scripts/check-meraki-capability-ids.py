#!/usr/bin/env python3
"""Validate every Meraki capability ID cited in a skill against Cisco's own OpenAPI spec.

Why this exists
---------------
The five Meraki skills cited **80** method names. Measured against the Meraki Dashboard API
1.70.0 spec bundled in Cisco's official MCP server:

    14 were real, reachable GET capabilities
    12 were real but mutating -- unreachable, the catalogue contains only GETs
    54 DID NOT EXIST IN THE API AT ALL

85% of the documented calls were fiction. They would have failed against any server, and
nothing in the repository noticed, because `verify-inventory-counts.py` checks that counts
agree -- it never checks whether a documented call is real. This is the same lesson as spec
088's startup surface: a check that compares declarations to each other cannot detect a
declaration that is uniformly wrong.

So this validates skill text against **vendored ground truth** rather than against other
prose: specs/089-meraki-official/contracts/meraki-capability-ids.json, extracted from the
spec Cisco ships inside their own server.

Negative examples are legitimate
--------------------------------
A skill SHOULD name mutating verbs when teaching that they are unreachable -- the shared
section says `updateNetwork`, `rebootDevice` and `blinkDeviceLeds` return
`Capability not found`, and `getOrganizationDevicesStatuses` is cited as the deprecated
case. Flagging those would push authors toward vaguer documentation, which is worse. A
mutating or deprecated ID is therefore only a finding when the surrounding line does not
mark it as unreachable.

Exit codes: 0 clean, 1 findings, 2 cannot run.
"""

import argparse
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRUTH = os.path.join(REPO_ROOT, "specs", "089-meraki-official", "contracts",
                     "meraki-capability-ids.json")
SKILL_GLOB = os.path.join(REPO_ROOT, "workspace", "skills", "meraki-*", "SKILL.md")

# An ID in backticks. Anchored on the Meraki verb prefixes so ordinary prose is not scanned.
ID_RE = re.compile(
    r"`((?:get|update|create|delete|remove|claim|blink|reboot|cycle|swap|bind|unbind|"
    r"split|combine|provision|assign|release|move|clone|defer|generate|restore|"
    r"lookup|publish|revoke|renew|reset|sync|trigger|validate|vmxNetwork)[A-Za-z0-9]+)`"
)

# A line that marks an ID as unreachable. Kept explicit rather than clever: a broad
# "mentions the word not" test would silently excuse real mistakes.
UNREACHABLE_MARKERS = (
    "capability not found",
    "not found",
    "unreachable",
    "do not exist",
    "does not exist",
    "deprecated",
    "absent",
    "impossible",
    "invalid parameters",
    "no writes",
    "does not have",
)


def load_truth():
    with open(TRUTH, encoding="utf-8") as fh:
        d = json.load(fh)
    return set(d["reachable_get"]), set(d["deprecated_get"]), set(d["mutating"])


def scan(path, reachable, deprecated, mutating):
    """Return a list of finding strings for one skill file."""
    findings = []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    rel = os.path.relpath(path, REPO_ROOT)
    for n, line in enumerate(lines, 1):
        marked = any(m in line.lower() for m in UNREACHABLE_MARKERS)
        for cid in ID_RE.findall(line):
            if cid in reachable:
                continue
            if cid in mutating:
                if not marked:
                    findings.append(
                        f"meraki-ids: {rel}:{n}: cites mutating `{cid}`, which is absent "
                        f"from the read-only catalogue, without marking it unreachable")
            elif cid in deprecated:
                if not marked:
                    findings.append(
                        f"meraki-ids: {rel}:{n}: cites deprecated `{cid}`, filtered out "
                        f"upstream, without marking it unreachable")
            else:
                # The 54-name failure mode. Never excusable: a nonexistent ID cannot be
                # taught as a negative example, because the reason it fails is unknowable.
                findings.append(
                    f"meraki-ids: {rel}:{n}: `{cid}` DOES NOT EXIST in Meraki Dashboard "
                    f"API 1.70.0 — it cannot succeed against any server")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warn-only", action="store_true", help="report findings but exit 0")
    args = ap.parse_args()

    if not os.path.isfile(TRUTH):
        print(f"meraki-ids: ground truth missing at {TRUTH}", file=sys.stderr)
        return 2

    reachable, deprecated, mutating = load_truth()
    files = sorted(glob.glob(SKILL_GLOB))
    if not files:
        print("meraki-ids: no meraki-* skills found", file=sys.stderr)
        return 2

    findings = []
    for f in files:
        findings.extend(scan(f, reachable, deprecated, mutating))

    print(f"Meraki skills scanned: {len(files)}")
    print(f"  ground truth: {len(reachable)} reachable, {len(deprecated)} deprecated, "
          f"{len(mutating)} mutating (Dashboard API 1.70.0)")

    if not findings:
        print("\nMeraki capability-ID check: PASS")
        return 0

    print(f"\nMeraki capability-ID check: FAIL ({len(findings)})")
    for f in findings:
        print(f"  {f}")
    print("\nUse semantic_search to find a real capability ID rather than recalling one. "
          "The catalogue contains only non-deprecated GETs.")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())
