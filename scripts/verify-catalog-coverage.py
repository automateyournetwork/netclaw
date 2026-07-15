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
}

# Catalog ids that intentionally cover a config/openclaw.json key with no
# clean prefix/suffix relationship to the id itself (pre-existing naming
# conventions that predate this feature, plus this feature's own additions).
GROUPED_CONFIG_EXACT = {
    "sketchfab-mcp": "threejs-viz",
    "azure-network-mcp": "azure",
    "unreal-mcp": "ue5",
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


def main():
    catalog_ids = load_catalog_ids()
    with open(CATALOG_SH) as f:
        catalog_text = f.read()

    registered = load_registered_servers()
    external_names = load_external_integrations()

    config_gaps = check_config_coverage(registered, catalog_ids)
    external_gaps = check_external_coverage(external_names, catalog_ids, catalog_text)

    print(f"Catalog entries: {len(catalog_ids)}")
    print(f"Registered config/openclaw.json servers: {len(registered)}")
    print(f"External (non-registered) integrations tracked: {len(external_names)}")
    print()

    if not config_gaps and not external_gaps:
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
    return 1


if __name__ == "__main__":
    sys.exit(main())
