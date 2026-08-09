#!/usr/bin/env python3
"""Verify that scripts/lib/catalog.sh has installer coverage for every MCP
integration NetClaw ships today.

Contract: specs/049-merge-modular-installer/contracts/catalog-entry-format.md
Data model: specs/049-merge-modular-installer/data-model.md

Two ground-truth sources are checked against the catalog:

1. config/openclaw.json's mcpServers keys -- structured, exact server ids.
   A registered key is "covered" if, after stripping a trailing -mcp/-mcp-
   server suffix, it equals a catalog id exactly, OR it matches an explicit
   prefix-group rule (GROUPED_CONFIG_PREFIXES) for catalog entries that
   intentionally bundle several servers under one selectable component
   (e.g. "checkpoint" covers every chkp-* server, "chrome-devtools" covers
   both the headless and Watch Mode registrations).

2. scripts/verify-inventory-counts.py's EXTERNAL_INTEGRATIONS list --
   human-readable names for integrations NetClaw supports that are NOT
   registered as static config/openclaw.json entries (installed on demand,
   remote/OAuth, or bundled into an existing skill's runtime). Matched
   against catalog entries via an explicit map for names this feature
   specifically added coverage for, falling back to a best-effort keyword
   match for the rest (this script's job is to prove *this feature's*
   closure and catch *future* drift, not to retroactively hand-verify
   coverage that already existed before this feature touched the catalog).

No third-party dependencies. Run from anywhere; paths resolve relative to
this file's location, not the caller's cwd.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_SH = os.path.join(REPO_ROOT, "scripts", "lib", "catalog.sh")
OPENCLAW_CONFIG = os.path.join(REPO_ROOT, "config", "openclaw.json")
VERIFY_INVENTORY = os.path.join(REPO_ROOT, "scripts", "verify-inventory-counts.py")

# Catalog ids that intentionally cover every registered config/openclaw.json
# key starting with the given prefix, rather than a single exact id match.
# Add an entry here whenever a new catalog component deliberately bundles
# more than one MCP server registration under one selectable component.
GROUPED_CONFIG_PREFIXES = {
    "chkp-": "checkpoint",
    "chrome-devtools": "chrome-devtools",
    "twilio": "twilio",
    "nautobot-mcp": "nautobot",  # bare "nautobot-mcp" (no golden-config/routing suffix)
    "cloudflare": "cloudflare",
    # Added by spec 075. Each of these catalog components already existed and
    # already installs every server under its prefix -- the components were
    # never missing, only these declarations were, so the checker could not
    # see coverage that was already present. See
    # specs/075-mcp-config-reconciliation/research.md R1.
    "aap-": "aap",  # aap-ansible-mcp, aap-docs-mcp, aap-eda-mcp, aap-lint-mcp
    "aws-": "aws",  # aws-{cloudtrail,cloudwatch,cost-explorer,diagram,iam,network}-mcp
    "gcp-": "gcp",  # gcp-{compute,logging,monitoring,resource-manager}-mcp
}

# Catalog ids that intentionally cover a config/openclaw.json key with no
# clean prefix/suffix relationship to the id itself (pre-existing naming
# conventions that predate this feature, plus this feature's own additions).
GROUPED_CONFIG_EXACT = {
    "sketchfab-mcp": "threejs-viz",
    "azure-network-mcp": "azure",
    "unreal-mcp": "ue5",
    "rag-mcp": "rag-mcp",
    # Added by spec 075 -- server keys whose catalog component exists but whose
    # name does not reduce to the catalog id by stripping "-mcp".
    "cisco-fmc-mcp": "fmc",              # strips to "cisco-fmc", catalog id is "fmc"
    "meraki-magic-mcp": "meraki",        # strips to "meraki-magic"
    "thousandeyes-mcp": "te-community",  # catalog uses the te-* naming convention
    "thousandeyes-official-mcp": "te-official",
    # The catalog id itself ends in "-mcp", so strip_mcp_suffix() reduces the
    # key to "memory" and the exact match fails. Same shape as the "rag-mcp"
    # entry above -- this is a suffix-stripping artefact, not a real gap.
    "memory-mcp": "memory-mcp",
    # Spec 096 (R12). Strips to "elasticsearch"; the catalog id is the shorter
    # "elastic", matching how the component is named for operators.
    "elasticsearch-mcp": "elastic",
}

# EXTERNAL_INTEGRATIONS names (from verify-inventory-counts.py) that this
# feature added catalog coverage for. Every future addition to that list
# that has no config/openclaw.json entry of its own MUST get an entry here
# in the same PR, or this script will silently miss it -- same discipline
# verify-inventory-counts.py already asks of EXTERNAL_INTEGRATIONS itself.
GROUPED_EXTERNAL_COVERAGE = {
    "memory-mcp": ["Memory MCP"],
    "ollama": ["Ollama"],
    "telemetry-receivers": ["IPFIX/NetFlow", "SNMP Trap Receiver", "Syslog Receiver"],
    # Pre-existing, already-correct mapping the length-3-minimum heuristic
    # can't find on its own ("f5" is 2 characters).
    "f5": ["F5 BIG-IP"],
    "computer-use": ["Computer Use"],
}


# Vendored mcp-servers/ directories whose state cannot be inferred by matching
# their directory name against a registered config key or an
# EXTERNAL_INTEGRATIONS entry. Every entry MUST carry a reason. Added by spec
# 075 (FR-014, FR-016, FR-017).
#
# This list is the deliberate inversion of the old failure mode: previously,
# forgetting to account for a vendored directory caused it to be silently
# undercounted forever. Now it causes a loud failure naming the directory, and
# the only way to silence it is to state why -- which is human knowledge that
# cannot be inferred from the source.
VENDORED_STATE_REASONS = {
    "gait_mcp": "registered as 'gait-mcp'; underscore/hyphen naming mismatch",
    "pyATS_MCP": "external — installed on demand via pip (EXTERNAL_INTEGRATIONS: pyATS)",
    "ISE_MCP": "external — installed on demand (EXTERNAL_INTEGRATIONS: Cisco ISE)",
    "ACI_MCP": "external — installed on demand (EXTERNAL_INTEGRATIONS: Cisco ACI)",
    "Wikipedia_MCP": "external — installed on demand (EXTERNAL_INTEGRATIONS: Wikipedia)",
    "markmap_mcp": "external — installed on demand (EXTERNAL_INTEGRATIONS: Markmap)",
    "mcp-nvd": "external — installed on demand (EXTERNAL_INTEGRATIONS: NVD CVE)",
    "mcp-nautobot": "external community alternative (EXTERNAL_INTEGRATIONS: Nautobot community)",
    "packet-buddy-mcp": "external — installed on demand (EXTERNAL_INTEGRATIONS: Packet Buddy)",
    "subnet-calculator-mcp": "external — bundled (EXTERNAL_INTEGRATIONS: Subnet Calculator)",
    "CiscoFMC-MCP-server-community": "community source for the 'fmc' component; registered as 'cisco-fmc-mcp'",
    "nautobot-mcp-v2": "backs the registered 'nautobot-mcp' entry (directory name differs from key)",
    "AAP-Enterprise-MCP-Server": "single source backing all four registered aap-* entries",
    "checkpoint-mcp-servers": "single source backing all fifteen registered chkp-* entries",
    "clab-mcp-server": "external — EXTERNAL_INTEGRATIONS 'ContainerLab', catalog id 'containerlab' (dir name abbreviates it)",
    "mcp-cvp-fun": "backs the registered 'arista-cvp-mcp' entry (EXTERNAL_INTEGRATIONS 'Arista CVP')",
    # OPEN FINDING, spec 075 -- recorded here so it is tracked, NOT suppressed.
    # EVE-NG is vendored and has five skills (eve-lab-topology-*, eve-ng-*), but
    # it appears in neither EXTERNAL_INTEGRATIONS nor scripts/lib/catalog.sh.
    # It is therefore absent from the integration count and cannot be installed
    # by the modular installer -- a Principle XI gap this check found. Resolving
    # it means adding an EXTERNAL_INTEGRATIONS entry (which raises the MCP count
    # to 150) plus a catalog entry and install function. That is a scope
    # decision for the maintainer, not something to absorb silently here.
    "eve-ng-mcp-server": "OPEN FINDING (spec 075): vendored with 5 skills but absent from "
                         "EXTERNAL_INTEGRATIONS and catalog.sh — needs a tracked follow-up",
}


def load_catalog_ids():
    """Parse the CATALOG array's "id|Category|Name|Description" lines."""
    with open(CATALOG_SH) as f:
        text = f.read()
    ids = []
    for match in re.finditer(r'"([a-z0-9-]+)\|[^"]*"', text):
        ids.append(match.group(1))
    return ids


def load_registered_servers():
    with open(OPENCLAW_CONFIG) as f:
        config = json.load(f)
    return sorted(config.get("mcpServers", {}).keys())


def load_external_integrations():
    """Import verify-inventory-counts.py's EXTERNAL_INTEGRATIONS list directly,
    so the two scripts can never silently drift apart from each other."""
    spec = importlib.util.spec_from_file_location("verify_inventory_counts", VERIFY_INVENTORY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.EXTERNAL_INTEGRATIONS)


def strip_mcp_suffix(server_id):
    for suffix in ("-mcp-server", "-mcp"):
        if server_id.endswith(suffix):
            return server_id[: -len(suffix)]
    return server_id


def check_config_coverage(registered, catalog_ids):
    catalog_set = set(catalog_ids)
    gaps = []
    for server_id in registered:
        if server_id in GROUPED_CONFIG_EXACT:
            if GROUPED_CONFIG_EXACT[server_id] in catalog_set:
                continue
            gaps.append((server_id, f"expected catalog id '{GROUPED_CONFIG_EXACT[server_id]}' (exact grouping) not found"))
            continue

        grouped = False
        for prefix, catalog_id in GROUPED_CONFIG_PREFIXES.items():
            if server_id.startswith(prefix) and catalog_id in catalog_set:
                grouped = True
                break
        if grouped:
            continue

        if strip_mcp_suffix(server_id) in catalog_set:
            continue

        gaps.append((server_id, "no matching catalog id (direct, prefix-group, or exact-group)"))
    return gaps


def check_external_coverage(external_names, catalog_ids, catalog_text):
    catalog_set = set(catalog_ids)
    covered_names = set()
    for catalog_id, names in GROUPED_EXTERNAL_COVERAGE.items():
        if catalog_id in catalog_set:
            covered_names.update(names)

    gaps = []
    text_lower = catalog_text.lower()
    for name in external_names:
        if name in covered_names:
            continue
        # Best-effort heuristic for names this feature did not specifically
        # add: does the name's first significant word appear anywhere in the
        # catalog file's text at all? This intentionally does not prove
        # *which* catalog entry covers it -- only that this script isn't
        # confidently reporting a false gap for something that was already
        # fine before this feature touched the catalog. First-word matching
        # (rather than the full phrase) is deliberate: catalog descriptions
        # paraphrase rather than repeat external names verbatim (e.g. "AWS
        # Network" is covered by an entry whose description never says
        # "network" but does say "aws").
        first_word = re.split(r"[\s/,(]", name.strip())[0].strip().lower()
        if first_word and len(first_word) >= 3 and first_word in text_lower:
            continue
        gaps.append((name, "not in GROUPED_EXTERNAL_COVERAGE and no keyword match in catalog.sh"))
    return gaps


def _norm(name):
    """Reduce a name to comparable letters/digits, dropping mcp/server noise."""
    s = re.sub(r"[^a-z0-9]", "", name.lower())
    for noise in ("mcpserver", "mcp", "server", "community", "v2"):
        s = s.replace(noise, "")
    return s


def _tracked_dirs(servers_dir):
    """Names under mcp-servers/ that git actually tracks content for.

    A directory with no tracked files is not a vendored server -- it is a build
    artifact. The common case is a gitignored virtualenv or __pycache__ left
    behind after switching branches: the directory still exists on disk, git
    cannot see it, but a filesystem scan can. Flagging those produced a spurious
    failure on `main` immediately after spec 075 merged, because a feature
    branch's .venv (9,300+ ignored files) survived the checkout.

    CI never hit this -- a fresh clone has no leftovers -- which is precisely why
    it needed catching here rather than there.

    Returns None when git is unavailable, so callers fall back to scanning
    everything rather than silently checking nothing.
    """
    try:
        out = subprocess.run(
            ["git", "-C", REPO_ROOT, "ls-files", "--", "mcp-servers"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    names = set()
    for line in out.stdout.splitlines():
        parts = line.split("/", 2)
        if len(parts) >= 3 and parts[0] == "mcp-servers":
            names.add(parts[1])
    return names


def check_vendored_state(registered, external_names):
    """Every mcp-servers/ directory must resolve to exactly one state:
    registered, external, or explained (which covers dropped). Added by spec
    075 -- FR-014, FR-017."""
    servers_dir = os.path.join(REPO_ROOT, "mcp-servers")
    if not os.path.isdir(servers_dir):
        return []

    tracked = _tracked_dirs(servers_dir)

    reg_norm = {_norm(k) for k in registered}
    ext_norm = {_norm(n) for n in external_names}

    gaps = []
    for entry in sorted(os.listdir(servers_dir)):
        if not os.path.isdir(os.path.join(servers_dir, entry)):
            continue
        # Untracked directory => build artifact, not a vendored server.
        if tracked is not None and entry not in tracked:
            continue
        if entry in VENDORED_STATE_REASONS:
            continue
        n = _norm(entry)
        if not n:
            continue
        if n in reg_norm or n in ext_norm:
            continue
        if any(n and (n in r or r in n) for r in reg_norm if len(r) >= 4):
            continue
        if any(n and (n in e or e in n) for e in ext_norm if len(e) >= 4):
            continue
        gaps.append((
            f"mcp-servers/{entry}",
            "no recorded state (expected registered, external, or a "
            "VENDORED_STATE_REASONS entry giving the reason)",
        ))
    return gaps


def main():
    catalog_ids = load_catalog_ids()
    with open(CATALOG_SH) as f:
        catalog_text = f.read()

    registered = load_registered_servers()
    external_names = load_external_integrations()

    config_gaps = check_config_coverage(registered, catalog_ids)
    external_gaps = check_external_coverage(external_names, catalog_ids, catalog_text)
    vendored_gaps = check_vendored_state(registered, external_names)

    print(f"Catalog entries: {len(catalog_ids)}")
    print(f"Registered config/openclaw.json servers: {len(registered)}")
    print(f"External (non-registered) integrations tracked: {len(external_names)}")
    print()

    if not config_gaps and not external_gaps and not vendored_gaps:
        print("Catalog coverage check: PASS (zero unexplained gaps)")
        return 0

    print("Catalog coverage check: FAIL")
    if config_gaps:
        print(f"\n  Registered servers with no catalog coverage ({len(config_gaps)}):")
        for server_id, reason in config_gaps:
            print(f"    - {server_id}: {reason}")
    if external_gaps:
        print(f"\n  External integrations with no catalog coverage ({len(external_gaps)}):")
        for name, reason in external_gaps:
            print(f"    - {name}: {reason}")
    if vendored_gaps:
        print(f"\n  Vendored directories with no recorded state ({len(vendored_gaps)}):")
        for name, reason in vendored_gaps:
            print(f"    - {name}: {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
