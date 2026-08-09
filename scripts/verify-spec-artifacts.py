#!/usr/bin/env python3
"""Verify every spec carries the SDD artifacts Constitution Principle XVI requires.

Principle XVI: "All new features, MCP servers, and skills MUST follow the SDD
workflow: specify -> plan -> task -> implement" and "Ad-hoc or undocumented
feature additions ('cowboy coding') are not permitted."

Nothing checked this, and it showed. An audit on 2026-08-05 found ten
CONSECUTIVE specs (087-096) shipped with spec.md alone. The drift began at 087
and was self-reinforcing: an author sampling the three most recent specs saw
spec.md alone and reasonably concluded that was the convention. It was not --
72 of 86 specs carried the full set.

A convention that is only in the constitution is a convention that erodes.

Two rules that keep this honest rather than merely green:

1. A combined plan+tasks document IS compliant. Spec 084 deliberately merged
   them with a stated rationale and carries 8 task phases. Demanding a separate
   file would push authors to split a good document, or to create a stub that
   satisfies a checker and informs nobody. So a "## Tasks" section inside
   plan.md counts.

2. The legacy exceptions are enumerated individually, never a date cutoff.
   A cutoff silently absolves whatever lands before it; a list has to be edited
   by a human who then owns the entry.

Usage:
    python3 scripts/verify-spec-artifacts.py [--warn-only] [--specs-dir DIR]

Exit 0 clean, 1 on findings (0 with --warn-only).
"""
import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Specs that predate the check and are accepted as-is. Each entry is a decision
# somebody made and owns -- NOT a date cutoff, which would silently absolve
# whatever lands next.
LEGACY_EXCEPTIONS = {
    "028-nautobot-golden-config-mcp": "predates the SDD workflow's consistent application",
    "030-nautobot-routing-mcp": "predates the SDD workflow's consistent application",
    "074-mobile-voice-playback": "small follow-on to 073; never had separate artifacts",
    # Not a gap in substance: the Phase 0 work is in plan.md's "## Key decisions"
    # section plus baseline.txt (the measured before-state) and checklists/.
    # Excepted rather than loosening the check to accept any decisions-shaped
    # heading, which would weaken it for new work.
    "077-dependency-pin-hazards": "research recorded as plan.md '## Key decisions' + baseline.txt",
}

# A spec dir must have spec.md, plus plan-and-tasks in some accepted form.
REQUIRED = ("spec.md",)
TASKS_SECTION = re.compile(r"^##+\s*(?:Phase \d+\s*[-—:]?\s*)?Tasks?\b", re.MULTILINE | re.IGNORECASE)


def has_tasks(spec_dir):
    """tasks.md, or a '## Tasks' section inside plan.md (the 084 form)."""
    if os.path.isfile(os.path.join(spec_dir, "tasks.md")):
        return True, "tasks.md"
    plan = os.path.join(spec_dir, "plan.md")
    if os.path.isfile(plan):
        try:
            with open(plan, encoding="utf-8") as f:
                if TASKS_SECTION.search(f.read()):
                    return True, "plan.md (combined)"
        except OSError:
            pass
    return False, None


def has_research(spec_dir):
    """research.md, or any research-*.md (084 uses research-phase0-notes.md)."""
    for name in os.listdir(spec_dir):
        if name == "research.md" or (name.startswith("research") and name.endswith(".md")):
            return True
    return False


def check(specs_dir):
    findings = []
    checked = 0
    if not os.path.isdir(specs_dir):
        return [(specs_dir, "specs directory not found")], 0

    for name in sorted(os.listdir(specs_dir)):
        spec_dir = os.path.join(specs_dir, name)
        if not os.path.isdir(spec_dir) or name.startswith("."):
            continue
        if name in LEGACY_EXCEPTIONS:
            continue
        checked += 1

        for required in REQUIRED:
            if not os.path.isfile(os.path.join(spec_dir, required)):
                findings.append((name, f"missing {required}"))

        if not os.path.isfile(os.path.join(spec_dir, "plan.md")):
            findings.append((name, "missing plan.md (Principle XVI: specify -> PLAN -> task)"))

        ok, _ = has_tasks(spec_dir)
        if not ok:
            findings.append(
                (name, "missing tasks.md, and plan.md has no '## Tasks' section "
                       "(Principle XVI: specify -> plan -> TASK)")
            )

        if not has_research(spec_dir):
            findings.append((name, "missing research.md (Phase 0 output)"))

    return findings, checked


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--warn-only", action="store_true",
                    help="report findings but exit 0")
    ap.add_argument("--specs-dir", default=os.path.join(REPO_ROOT, "specs"),
                    help="directory of spec folders (default: <repo>/specs)")
    args = ap.parse_args()

    findings, checked = check(args.specs_dir)

    if not findings:
        print(f"spec artifacts: PASS  ({checked} specs checked, "
              f"{len(LEGACY_EXCEPTIONS)} legacy exceptions)")
        return 0

    print(f"spec artifacts: {len(findings)} finding(s) across {checked} specs checked")
    for spec, problem in findings:
        print(f"  {spec}: {problem}")
    print("\nPrinciple XVI requires specify -> plan -> task -> implement.")
    print("A combined plan.md carrying a '## Tasks' section satisfies the task requirement.")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())
