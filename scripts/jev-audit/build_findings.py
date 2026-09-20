"""Aggregate sweep1/2/3 raw JSON into docs/jev-audit/findings.md."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_PATH = REPO_ROOT / "docs" / "jev-audit" / "findings.md"

QUESTION_LABELS = {
    "ambiguous_trigger": "Ambiguous trigger",
    "unspecified_failure_behavior": "No failure behavior specified",
    "stale_assumptions": "Stale machine/path assumptions",
    "injection_smell": "Prompt-injection-like content",
}

COLLISION_THRESHOLD = 0.60
COVERAGE_THRESHOLD = 0.40


def effective(val: float, stability: dict, key: str) -> tuple[float, bool, bool]:
    """Returns (effective_value, was_rechecked, is_stable). Unstable rechecks are
    excluded by the caller rather than trusted at face value."""
    stab = stability.get(key)
    if stab is None:
        return val, False, True
    return stab["mean"], True, stab["stable"]


def build_sweep1_section() -> str:
    data = json.loads((DATA_DIR / "sweep1_raw.json").read_text())
    rows = []
    for entry in data:
        if "error" in entry and "answers" not in entry:
            continue
        skill = entry["skill"]
        answers = entry.get("answers", {})
        stability = entry.get("stability", {})
        tool_check = entry.get("tool_check", {})
        score = 0.0
        flags = []
        for qkey, val in answers.items():
            eff, rechecked, stable = effective(val, stability, qkey)
            if rechecked and not stable:
                continue  # unstable mid-band answer, don't trust either direction
            confidence = abs(eff - 0.5) * 2
            contribution = eff * confidence
            score += contribution
            if eff >= 0.5:
                flags.append((QUESTION_LABELS.get(qkey, qkey), eff, confidence, rechecked))
        undefined_env = tool_check.get("undefined_env_vars", [])
        rows.append((score, skill, flags, undefined_env))

    rows.sort(key=lambda r: r[0], reverse=True)

    lines = [
        "## Sweep 1 — Skill health",
        "",
        f"227 skills checked, one Jev call per skill (full `SKILL.md` as state), a 4-question noul "
        "battery per call (ambiguous trigger, no failure behavior, stale machine/path assumptions, "
        "prompt-injection smell). Tool/MCP-reference existence is checked deterministically in code "
        "(env-var references in the skill text cross-checked against `.env` and `openclaw.json`), "
        "not asked to Jev — it has no ground truth for that and stuffing a 227-server registry into "
        "every call would violate the \"one unit of analysis per call\" rule.",
        "",
        "Ranked by confidence x impact (sum of `noul x |noul-0.5|x2` over flagged questions; "
        "mid-confidence answers were re-run 5x for self-consistency and dropped if unstable rather "
        "than trusted at face value).",
        "",
        "| Rank | Skill | Score | Flags | Undefined env refs |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i, (score, skill, flags, undefined_env) in enumerate(rows[:40], 1):
        if score == 0 and not undefined_env:
            continue
        flag_str = "; ".join(f"{label} ({val:.2f}{'*' if rechecked else ''})" for label, val, conf, rechecked in flags) or "—"
        env_str = ", ".join(undefined_env) if undefined_env else "—"
        lines.append(f"| {i} | `{skill}` | {score:.2f} | {flag_str} | {env_str} |")
    lines.append("")
    lines.append("`*` = confirmed via 5x self-consistency recheck (was in the 0.30-0.70 mid-band on the first pass).")
    lines.append("")

    total_undefined = [(r[1], r[3]) for r in rows if r[3]]
    if total_undefined:
        lines.append(f"**{len(total_undefined)} skills reference an env var not found in `.env` or `openclaw.json`** (may be intentionally operator-supplied — worth a manual look, not an automatic bug):")
        lines.append("")
        for skill, envs in total_undefined:
            lines.append(f"- `{skill}`: {', '.join(envs)}")
        lines.append("")

    return "\n".join(lines)


def build_sweep2_section() -> str:
    data = json.loads((DATA_DIR / "sweep2_raw.json").read_text())
    collisions = []
    for anchor_entry in data:
        name_i = anchor_entry["anchor"]
        pairs = anchor_entry.get("pairs", {})
        stability = anchor_entry.get("stability", {})
        for name_j, val in pairs.items():
            eff, rechecked, stable = effective(val, stability, name_j)
            if rechecked and not stable:
                continue
            if eff >= COLLISION_THRESHOLD:
                collisions.append((eff, name_i, name_j, rechecked))
    collisions.sort(reverse=True)

    lines = [
        "## Sweep 2 — Overlap matrix",
        "",
        f"All C(227,2) = 25,651 pairs covered. Descriptions only, batched by anchor skill "
        "(one skill's description as state, one short noul question per later skill in the "
        "sorted list) rather than one call per pair — same coverage, 630 calls instead of "
        "25,651, per Jev's own \"batch questions, not calls\" guidance.",
        "",
        f"**{len(collisions)} pairs at noul >= {COLLISION_THRESHOLD}** (genuine trigger-territory overlap, "
        "not just shared keywords; unstable mid-confidence pairs excluded rather than trusted):",
        "",
        "| Noul | Skill A | Skill B |",
        "| --- | --- | --- |",
    ]
    for eff, name_i, name_j, rechecked in collisions[:50]:
        mark = "*" if rechecked else ""
        lines.append(f"| {eff:.2f}{mark} | `{name_i}` | `{name_j}` |")
    lines.append("")
    lines.append(f"({len(collisions) - 50} more below the top 50 not shown here — see `data/sweep2_raw.json`.)" if len(collisions) > 50 else "")
    lines.append("")
    lines.append("`*` = confirmed via 5x self-consistency recheck.")
    lines.append("")
    return "\n".join(lines)


def build_sweep3_section() -> str:
    data = json.loads((DATA_DIR / "sweep3_raw.json").read_text())
    confirmed_gaps = []
    borderline = []
    covered = []
    for entry in data:
        cand = entry["candidate"]
        desc = entry["description"]
        kind = entry["kind"]
        coverage = entry.get("coverage", {})
        stability = entry.get("stability", {})
        max_eff = 0.0
        max_skill = None
        for existing_name, val in coverage.items():
            eff, rechecked, stable = effective(val, stability, existing_name)
            if rechecked and not stable:
                continue
            if eff > max_eff:
                max_eff = eff
                max_skill = existing_name
        if max_eff < COVERAGE_THRESHOLD:
            confirmed_gaps.append((cand, desc, kind, max_eff, max_skill))
        elif max_eff < 0.55:
            borderline.append((cand, desc, kind, max_eff, max_skill))
        else:
            covered.append((cand, desc, kind, max_eff, max_skill))

    lines = [
        "## Sweep 3 — Coverage gaps",
        "",
        "60 candidates (40 skills + 20 MCP servers a CCIE-level network agent should plausibly "
        f"have, see `candidates.py`) checked against all 227 existing skill descriptions. "
        f"Confirmed gap = every existing-skill coverage check stays below {COVERAGE_THRESHOLD} "
        "(no existing skill's real scope already covers it).",
        "",
        f"### Confirmed gaps ({len(confirmed_gaps)}/60)",
        "",
        "| Candidate | Kind | Description | Closest existing skill (noul) |",
        "| --- | --- | --- | --- |",
    ]
    for cand, desc, kind, max_eff, max_skill in sorted(confirmed_gaps, key=lambda r: r[3]):
        closest = f"`{max_skill}` ({max_eff:.2f})" if max_skill else "—"
        lines.append(f"| `{cand}` | {kind} | {desc} | {closest} |")
    lines.append("")

    if borderline:
        lines.append(f"### Borderline ({len(borderline)}/60) — partially covered, worth a second look")
        lines.append("")
        lines.append("| Candidate | Kind | Closest existing skill (noul) |")
        lines.append("| --- | --- | --- |")
        for cand, desc, kind, max_eff, max_skill in sorted(borderline, key=lambda r: r[3]):
            lines.append(f"| `{cand}` | {kind} | `{max_skill}` ({max_eff:.2f}) |")
        lines.append("")

    lines.append(f"### Already covered ({len(covered)}/60) — Jev found an existing skill that already does this")
    lines.append("")
    lines.append("| Candidate | Kind | Existing skill (noul) |")
    lines.append("| --- | --- | --- |")
    for cand, desc, kind, max_eff, max_skill in sorted(covered, key=lambda r: -r[3]):
        lines.append(f"| `{cand}` | {kind} | `{max_skill}` ({max_eff:.2f}) |")
    lines.append("")
    return "\n".join(lines)


def build_deterministic_bonus() -> str:
    """MCP servers that already exist in mcp-servers/ with no matching workspace/skills/
    entry — a code-verifiable gap, not Jev-scored, found while researching sweep3 candidates."""
    lines = [
        "## Bonus: deterministic cross-check (not Jev-scored)",
        "",
        "While picking sweep 3 candidates, an initial name-prefix grep suggested several vendored "
        "`mcp-servers/` entries had no skill wiring them up. Checking actual skill *content* (not "
        "just directory names) disproved most of those guesses — `te-network-monitoring`/`te-path-analysis` "
        "turned out to already be the ThousandEyes skills (`te` = ThousandEyes), `sdwan-ops` already "
        "wraps `cisco-sdwan-mcp`, and `hardware-health-check` already wraps `redfish-mcp`. Worth "
        "recording as a caution about this exact kind of check: name-matching alone gives false "
        "positives, and only actually reading the file content confirms a real gap. What survived "
        "that check:",
        "",
        "- `mcp-servers/ollama-mcp/` — no skill references it anywhere in `workspace/skills/`.",
        "- `mcp-servers/nautobot-golden-config-mcp/` (the Nautobot Golden Config plugin, drift/compliance "
        "against a Nautobot-sourced intended config) has no dedicated skill — `itential-automation`'s "
        "\"golden config\" is Itential's own separate feature, not this plugin.",
        "",
        "Confirmed real (also independently surfaced by sweep 2, `catalyst-center-readonly` <-> "
        "`catc-inventory` at 0.93): two separately vendored MCP servers for the same product, "
        "`mcp-servers/catc-mcp/` and `mcp-servers/catalyst-center-mcp/`, backing four different "
        "skills between them — worth checking whether both implementations are still needed.",
        "",
    ]
    return "\n".join(lines)


def build_fixes_applied_section() -> str:
    return """## Fixes applied on this branch

Per operator direction, findings above were acted on (not left purely as a to-review list):

- **123 skills** got a tailored `## Failure Behavior` section (generated per-skill from its own
  referenced env vars and read-only-vs-write-capable tool set, not one paragraph pasted 123 times) —
  `scripts/jev-audit/fix_failure_behavior.py`.
- **3 genuine stale-machine assumptions fixed**: a Cisco DevNet sandbox hostname hardcoded in
  `pyats-network`, the operator's own name baked into federation-member paths in `comfyui-topology-viz`,
  and a hardcoded Twitter handle in `twitter-respond`. 5 other flagged skills were checked and correctly
  left alone as false positives (already using env vars / generic examples).
- **21 of the 26 highest-confidence (>=0.85) overlapping pairs disambiguated** via targeted description
  edits (narrowing scope, cross-referencing the sibling skill, or correcting an inaccurate "only tool for
  X" claim). One of these — `memory` vs `mempalace` — turned out to have a real root cause: `memory/SKILL.md`
  had no YAML frontmatter at all, so Jev's (and presumably any other) description extractor saw nothing;
  fixed by adding proper frontmatter. 5 pairs were reviewed and correctly left as intentional design
  (e.g. the `eve-lab-topology-*` discovery -> design -> validation pipeline).
- **Not attempted**: the 310 lower-confidence (0.60-0.85) overlapping pairs, and the 47 confirmed
  sweep-3 coverage gaps. The gaps are net-new skill/MCP integrations against real vendor APIs (Sentinel,
  ClearPass, Consul, etc.) — fabricating those without actual credentials/testing would produce untested
  code presented as working, which is a quality and trust problem no budget number fixes. Treat each as
  a candidate for its own spec, following `docs/ADDING-AN-MCP.md`, if picked up.

"""


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = """# Jev audit findings

Branch: `jev-audit`. Disposable analysis harness in `scripts/jev-audit/`, throwaway tooling —
not integrated into NetClaw. Uses TypeSafe's Jev (System One model) to gut-check the 227 skills
in `workspace/skills/` for health, overlap, and coverage gaps. All findings below are Jev's
probabilistic judgments, not certainties — treat as a prioritized list to investigate, not a
verdict.

## Methodology summary

| Sweep | Design | Calls | Real cost |
| --- | --- | --- | --- |
| 1: skill health | 1 call/skill, 4-question noul battery | 462 (227 primary + 235 self-consistency) | $0.0541 |
| 2: overlap matrix | anchor-batched, 25,651 pairs in 630 calls | 10,900 (630 primary + 10,270 self-consistency) | $0.3569 |
| 3: coverage gaps | 60 candidates x 227 existing skills, chunked | 530 (300 primary + 230 self-consistency) | $0.0702 |
| **Total** | | **11,892** | **$0.4812** |

All three sweeps stayed far under the $1.50-per-sweep stop threshold (of a $5 total budget).

**Bugs hit and fixed live**, in case this harness is ever resurrected:
1. A naive one-call-per-pair design for sweep 2 would have been 25,651 calls; batched by anchor
   skill instead (one call, many questions) per Jev's own "batch questions, not calls" guidance —
   227 calls for the same coverage.
2. The first batched version repeated a long boilerplate paragraph in every question's
   `instructions`; the largest anchor's request hit ~58k tokens, right at Jev's 64k context
   ceiling, and stalled outbound (TCP send queue never drained, no exception, no timeout firing).
   Fixed by stating the rubric once in `state` and hard-chunking to 50 comparisons/call.
3. Self-consistency reruns were originally run synchronously inside each batched call's worker
   thread — a chunk with many mid-confidence answers could serialize up to 250 sequential calls,
   which starved the progress counter identically to a real stall. Fixed by splitting into two
   independently-parallelized phases (primary answers, then a separate concurrent pass over only
   the mid-band questions), and by firing each question's 5 self-consistency reruns concurrently
   instead of in a sequential loop.
4. Added a hard wall-clock guard (`common.py`) around every HTTP call, independent of `requests`'
   own timeout, after observing a stall that `timeout=` never caught.

---

"""
    sections = [
        build_fixes_applied_section(),
        build_sweep1_section(),
        build_sweep2_section(),
        build_sweep3_section(),
        build_deterministic_bonus(),
    ]
    OUT_PATH.write_text(header + "\n\n".join(sections), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
