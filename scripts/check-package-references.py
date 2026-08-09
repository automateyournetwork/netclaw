#!/usr/bin/env python3
"""Verify that every npm/PyPI package a skill invokes actually exists.

Why this exists
---------------
Three skills -- msgraph-files, msgraph-teams, msgraph-visio -- invoked
`npx -y @anthropic-ai/microsoft-graph-mcp`, which **404s on the npm registry**. Between them
they documented 17 invocations across 14 `graph_*` tool names that could never run.

Nothing caught it. `verify-inventory-counts.py` checks that counts agree, `check-server-startup.py`
launches *registered* servers -- and an on-demand `npx` invocation inside a skill is neither
counted nor registered. It is the same meta-pattern as spec 088 and 089: a check that compares
declarations to each other cannot detect a declaration that is uniformly wrong.

Offline by default, and that is deliberate
------------------------------------------
The reconcile gate has **no network access by design** (spec 075 SC-013: "no dependencies, no
network access, no credentials, and no installed NetClaw agent"). Spec 090 learned the hard way
what happens when a surface ignores that -- CI failed on a healthy tree.

So this compares skill text against a **vendored manifest** of previously verified references
(`specs/093-package-reference-check/contracts/verified-packages.json`), exactly the shape spec
089 used for Meraki capability IDs. `--refresh` is the separate, network-using mode that
re-queries the registries and rewrites the manifest; a human runs it, CI never does.

A reference absent from the manifest is a finding, not a pass: an unverified package is
indistinguishable from a fictional one, and defaulting to "probably fine" is how the msgraph
404 survived.

Exit codes: 0 clean, 1 findings, 2 cannot run.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO_ROOT, "specs", "093-package-reference-check", "contracts",
                        "verified-packages.json")
SKILL_GLOB = os.path.join(REPO_ROOT, "workspace", "skills", "*", "SKILL.md")

# `npx <pkg>` / `uvx <pkg>`, allowing the usual flags in between.
_NPX = re.compile(r"\bnpx\s+((?:-[a-zA-Z-]+\s+)*)([@\w./-]+)")
_UVX = re.compile(r"\buvx\s+((?:--?[a-zA-Z-]+\s+\S*\s*)*)([\w.\[\]-]+)")

# A package reference must be scoped (@scope/name) or contain a hyphen or a dot.
#
# This is the rule that keeps prose out of the manifest. Skills contain sentences like
# "npx with Azure AD credentials:" and commands like "npx skills add opsmill/…", where the
# token after npx is an English word or a subcommand, not a package. Every real MCP package
# passes: chrome-devtools-mcp, mcp-remote, @drawio/mcp, awslabs.aws-diagram-mcp-server.
# Bare single words are skipped rather than reported -- a check that cries wolf about prose
# trains people to ignore it, which is worse than the gap it closes.
_LOOKS_LIKE_PACKAGE = re.compile(r"^(@[a-z0-9~.-]+/[a-z0-9~._-]+|[a-z0-9][a-z0-9._-]*[.-][a-z0-9._-]*)$")


# A skill SHOULD be able to say "this used to invoke X, which does not exist" -- that history
# is why the skill changed, and deleting it invites someone to reintroduce the bug. So a
# reference on a line marked as broken/replaced is not counted as an invocation. Same
# allowance, and the same reasoning, as spec 089's meraki-ids check: flagging the teaching
# example pushes authors toward vaguer documentation than the problem being solved.
_MARKED_BROKEN = ("404", "does not exist", "did not exist", "no longer", "replaced",
                  "previously", "until spec", "fictional", "exists in no server")


def extract() -> dict[tuple[str, str], set[str]]:
    """{(registry, package): {skills that invoke it}}"""
    found: dict[tuple[str, str], set[str]] = {}
    for path in sorted(glob.glob(SKILL_GLOB)):
        skill = os.path.basename(os.path.dirname(path))
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        # Line-indexed so a reference can be judged in the context it appears in.
        lines = text.splitlines()
        offsets = []
        pos = 0
        for ln in lines:
            offsets.append((pos, pos + len(ln), ln))
            pos += len(ln) + 1

        def marked(idx: int) -> bool:
            for start, end, ln in offsets:
                if start <= idx <= end:
                    return any(mk in ln.lower() for mk in _MARKED_BROKEN)
            return False

        for rx, registry in ((_NPX, "npm"), (_UVX, "pypi")):
            for m in rx.finditer(text):
                if marked(m.start()):
                    continue
                name = m.group(2).strip()
                # Strip a version/tag suffix. Both runners accept pkg@version, and npm scoped
                # names start with @ -- so split on the LAST @ only when it is not position 0.
                # Missing this dropped chrome-devtools-mcp@latest from the manifest entirely,
                # which is the quiet failure mode this whole check exists to prevent.
                at = name.rfind("@")
                if at > 0:
                    name = name[:at]
                if registry == "pypi":
                    name = name.split("[")[0]
                name = name.rstrip(".,;:")
                if not _LOOKS_LIKE_PACKAGE.match(name):
                    continue
                found.setdefault((registry, name), set()).add(skill)
    return found


def load_manifest() -> dict:
    if not os.path.isfile(MANIFEST):
        return {}
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh).get("packages", {})


def _key(registry: str, name: str) -> str:
    return f"{registry}:{name}"


def probe(registry: str, name: str, timeout: int = 20) -> tuple[bool, int]:
    """Ask the registry whether the package exists. Network-using; --refresh only."""
    if registry == "npm":
        url = "https://registry.npmjs.org/" + urllib.parse.quote(name, safe="")
    else:
        url = f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "netclaw-package-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, resp.status
    except urllib.error.HTTPError as exc:
        return False, exc.code
    except Exception:
        return False, 0


def refresh() -> int:
    """Re-query every referenced package and rewrite the manifest. Needs network."""
    refs = extract()
    packages: dict[str, dict] = {}
    unreachable = 0
    for (registry, name), skills in sorted(refs.items()):
        exists, status = probe(registry, name)
        if status == 0:
            print(f"  registry unreachable for {registry}:{name} — leaving prior verdict",
                  file=sys.stderr)
            prior = load_manifest().get(_key(registry, name))
            if prior:
                packages[_key(registry, name)] = prior
                continue
            unreachable += 1
            continue
        packages[_key(registry, name)] = {
            "registry": registry, "name": name, "exists": exists,
            "http_status": status, "referenced_by": sorted(skills),
        }
        print(f"  {'ok     ' if exists else 'MISSING'} {registry:<5} {name}  ({status})")

    import datetime
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump({
            "_why": ("Ground truth for scripts/check-package-references.py. Skills invoke "
                     "packages on demand via npx/uvx; those references are neither counted by "
                     "verify-inventory-counts.py nor launched by check-server-startup.py, so "
                     "nothing verified they exist. @anthropic-ai/microsoft-graph-mcp did not, "
                     "and three skills documented 14 tool names against it."),
            "_refresh": "python3 scripts/check-package-references.py --refresh  (needs network)",
            "_verified_at": datetime.datetime.now(datetime.timezone.utc)
                                    .replace(microsecond=0).isoformat(),
            "packages": dict(sorted(packages.items())),
        }, fh, indent=1)
        fh.write("\n")
    print(f"\nWrote {len(packages)} verified references to {os.path.relpath(MANIFEST, REPO_ROOT)}")
    return 2 if unreachable else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warn-only", action="store_true", help="report findings but exit 0")
    ap.add_argument("--refresh", action="store_true",
                    help="re-query the registries and rewrite the manifest (needs network)")
    args = ap.parse_args()

    if args.refresh:
        return refresh()

    manifest = load_manifest()
    if not manifest:
        print(f"packages: manifest missing or empty at {MANIFEST}", file=sys.stderr)
        print("  Remedy: python3 scripts/check-package-references.py --refresh", file=sys.stderr)
        return 2

    refs = extract()
    findings: list[str] = []
    for (registry, name), skills in sorted(refs.items()):
        entry = manifest.get(_key(registry, name))
        users = ", ".join(sorted(skills))
        if entry is None:
            findings.append(
                f"packages: {registry}:{name} is referenced by {users} but has never been "
                f"verified — run --refresh. An unverified package is indistinguishable from a "
                f"fictional one")
        elif not entry.get("exists"):
            findings.append(
                f"packages: {registry}:{name} DOES NOT EXIST "
                f"(HTTP {entry.get('http_status')}) but is invoked by {users} — every "
                f"documented call against it fails")

    print(f"Package references scanned: {len(refs)} across "
          f"{len({s for v in refs.values() for s in v})} skills")
    if not findings:
        print("\nPackage-reference check: PASS")
        return 0
    print(f"\nPackage-reference check: FAIL ({len(findings)})")
    for f in findings:
        print(f"  {f}")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())
