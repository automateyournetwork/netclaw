#!/usr/bin/env python3
"""Verify NetClaw's documented skill/MCP counts against the live codebase.

Contract: specs/047-docs-inventory-reconciliation/contracts/verify-inventory-counts-cli.md
Data model: specs/047-docs-inventory-reconciliation/data-model.md

Computes the true skill count (workspace/skills/ directories containing a
SKILL.md) and the true MCP integration count (config/openclaw.json entries,
which are already individually registered with no bundling to expand --
e.g. Check Point's 15 chkp-* servers are 15 separate top-level entries, not
one bundle -- plus a maintained list of externally-installed integrations
that are documented in README.md's MCP Servers table or exist as vendored
mcp-servers/ directories but are not registered in config/openclaw.json at
all, typically because they're installed on demand via pip/npm/Docker).

Then best-effort scans README.md and SOUL.md for numeric "N skills" / "N MCP"
claims and reports any that disagree with the computed totals.

No third-party dependencies. Run from anywhere; paths resolve relative to
this file's location, not the caller's cwd.
"""

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "workspace", "skills")
OPENCLAW_CONFIG = os.path.join(REPO_ROOT, "config", "openclaw.json")
README = os.path.join(REPO_ROOT, "README.md")
SOUL = os.path.join(REPO_ROOT, "SOUL.md")

# Integrations that are part of NetClaw's supported set but are NOT present
# as top-level entries in config/openclaw.json (usually because they are
# installed on demand via pip/npm/Docker rather than pre-registered, or are
# optional community alternatives). This list is maintained by hand -- when
# you add a new integration of this kind, add its name here in the SAME PR,
# or this script will silently undercount it forever, repeating the exact
# drift this script exists to catch. Verified against README.md's MCP
# Servers table and mcp-servers/ vendored directories as of 2026-07-07.
EXTERNAL_INTEGRATIONS = [
    "pyATS",
    "F5 BIG-IP",
    "Catalyst Center",
    "Cisco ACI",
    "Cisco ISE",
    "NetBox",
    "Nautobot (community, aiopnet/mcp-nautobot)",
    "Itential IAP",
    "ServiceNow",
    "Microsoft Graph",
    "GitHub",
    "Packet Buddy",
    "Cisco CML",
    "Cisco NSO",
    "Cisco FMC",
    "Cisco Meraki",
    "ThousandEyes (community)",
    "ThousandEyes (official)",
    "Cisco RADKit",
    "AWS Network",
    "AWS CloudWatch",
    "AWS IAM",
    "AWS CloudTrail",
    "AWS Cost Explorer",
    "AWS Diagram",
    "GCP Compute Engine",
    "GCP Cloud Monitoring",
    "GCP Cloud Logging",
    "GCP Resource Manager",
    "NVD CVE",
    "Subnet Calculator",
    "GAIT",
    "Wikipedia",
    "Markmap",
    "Draw.io",
    "RFC Lookup",
    "Juniper JunOS",
    "Arista CVP",
    "UML MCP",
    "Protocol MCP",
    "ContainerLab",
    "Cisco SD-WAN",
    "Grafana",
    "Prometheus",
    "Kubeshark",
    "nmap",
    "gtrace",
    "AAP Controller",
    "AAP EDA",
    "AAP Lint",
    "Red Hat Docs",
    "fwrule",
    "HumanRail",
    # Vendored under mcp-servers/ but, as of 2026-07-07, undocumented in
    # README.md's MCP Servers table entirely -- see spec 047 User Story 2.
    "IPFIX/NetFlow",
    "Ollama",
    "Memory MCP",
    "SNMP Trap Receiver",
    "Syslog Receiver",
    "Text-to-Speech (TTS)",
]


def count_skills():
    """Count workspace/skills/ directories that contain a SKILL.md file."""
    if not os.path.isdir(SKILLS_DIR):
        return None
    count = 0
    for entry in os.listdir(SKILLS_DIR):
        full_path = os.path.join(SKILLS_DIR, entry)
        if os.path.isdir(full_path) and os.path.isfile(os.path.join(full_path, "SKILL.md")):
            count += 1
    return count


def count_mcp_integrations():
    """Count MCP integrations: config/openclaw.json entries + external list.

    config/openclaw.json's mcpServers entries are already fully individually
    registered (Check Point's 15 chkp-* servers are 15 separate keys, not
    one bundle needing expansion), so no bundle math is required here.
    """
    if not os.path.isfile(OPENCLAW_CONFIG):
        return None, {}
    with open(OPENCLAW_CONFIG) as f:
        config = json.load(f)
    config_entries = len(config.get("mcpServers", {}))
    external_documented = len(EXTERNAL_INTEGRATIONS)
    total = config_entries + external_documented
    breakdown = {
        "config_entries": config_entries,
        "external_documented": external_documented,
    }
    return total, breakdown


def check_doc_claims(skill_count, mcp_count):
    """Best-effort scan of README.md/SOUL.md for numeric skill/MCP claims.

    Deliberately scoped to the specific "headline" claim locations spec 047
    identified (top prose, HUD prose, section headings, SOUL.md identity
    line) rather than every "\\d+ skills"/"\\d+ MCP" occurrence in the
    document -- a document-wide scan produces false positives against
    subsection counts that are legitimately different numbers (e.g.
    "Microsoft 365 Skills (3)" matches "365 Skills", "GNS3 Skills (5)" is a
    real subsection total, not a drifted headline claim). Historical
    mission-log entries (e.g. "MISSION02... 78 skills") are intentionally
    NOT matched -- they are dated past-state records, not current claims.
    """
    discrepancies = []
    notes = []

    # (file, description, compiled pattern, [(kind, capture group index), ...])
    headline_patterns = [
        (README, "top prose (skills + MCP)",
         re.compile(r"Claude,\s*(\d+)\s*skills,\s*and\s*(\d+)\s*MCP integrations"),
         [("skill", 1), ("MCP", 2)]),
        (README, "installer prose (skills)",
         re.compile(r"deploys\s*(\d+)\s*skills"),
         [("skill", 1)]),
        (README, "installer prose (MCP)",
         re.compile(r"for\s*(\d+)\s*MCP integrations"),
         [("MCP", 1)]),
        (README, "Visual HUD prose",
         re.compile(r"currently\s*(\d+)\s*MCP integrations and\s*(\d+)\s*skills"),
         [("MCP", 1), ("skill", 2)]),
        (README, "MCP Servers section heading",
         re.compile(r"^## MCP Servers \((\d+)\)", re.MULTILINE),
         [("MCP", 1)]),
        (README, "Skills section heading",
         re.compile(r"^## Skills \((\d+)\)", re.MULTILINE),
         [("skill", 1)]),
        (SOUL, "identity line (skills + MCP)",
         re.compile(r"\*\*(\d+) skills\*\* backed by (\d+) MCP servers"),
         [("skill", 1), ("MCP", 2)]),
        (SOUL, "SOUL-SKILLS cross-reference",
         re.compile(r"best practices for all (\d+) skills"),
         [("skill", 1)]),
    ]

    doc_cache = {}
    for doc_path, description, pattern, kinds in headline_patterns:
        doc_name = os.path.basename(doc_path)
        if doc_path not in doc_cache:
            if not os.path.isfile(doc_path):
                notes.append(f"{doc_name} not found, skipped")
                doc_cache[doc_path] = None
            else:
                with open(doc_path) as f:
                    doc_cache[doc_path] = f.read()
        text = doc_cache[doc_path]
        if text is None:
            continue

        match = pattern.search(text)
        if match is None:
            notes.append(f"{doc_name}: could not locate '{description}' (phrasing may have changed)")
            continue

        line_no = text.count("\n", 0, match.start()) + 1
        for kind, group_idx in kinds:
            claimed = int(match.group(group_idx))
            expected = skill_count if kind == "skill" else mcp_count
            if claimed != expected:
                discrepancies.append({
                    "file": doc_name,
                    "location": f"line {line_no} ({description})",
                    "matched_text": match.group(0),
                    "claimed_value": claimed,
                    "computed_value": expected,
                    "kind": kind,
                })

    return discrepancies, notes


def main():
    skill_count = count_skills()
    if skill_count is None:
        print(f"ERROR: could not read {SKILLS_DIR}", file=sys.stderr)
        return 2

    mcp_count, breakdown = count_mcp_integrations()
    if mcp_count is None:
        print(f"ERROR: could not read {OPENCLAW_CONFIG}", file=sys.stderr)
        return 2

    discrepancies, notes = check_doc_claims(skill_count, mcp_count)

    print(f"Skill count: {skill_count}")
    print(f"  workspace/skills/ directories with SKILL.md: {skill_count}")
    print()
    print(f"MCP integration count: {mcp_count}")
    print(f"  config/openclaw.json top-level entries: {breakdown['config_entries']}")
    print(f"  + externally-installed (documented, not in config): {breakdown['external_documented']}")
    print()

    if discrepancies:
        print("Documentation check: FAIL")
        for d in discrepancies:
            print(
                f"  {d['file']}:{d['location']} claims \"{d['matched_text']}\" "
                f"({d['kind']}), computed {d['computed_value']}"
            )
    else:
        print("Documentation check: PASS")

    for note in notes:
        print(f"  note: {note}")

    return 1 if discrepancies else 0


if __name__ == "__main__":
    sys.exit(main())
