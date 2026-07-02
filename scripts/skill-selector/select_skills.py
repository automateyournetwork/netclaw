#!/usr/bin/env python3
"""
NetClaw skill selector — scope the runtime skill catalog to a relevant subset.

WHY THIS EXISTS
  OpenClaw builds the in-context skill index by scanning its skills directory and
  emitting every skill's frontmatter `description`. There is no retrieval or
  enable-list: the directory contents ARE the index. With 192 skills that is
  ~13.8K tokens of system prompt re-sent every turn (measured via the harness).

  This tool selects the top-k relevant skills for a given query/alert (plus a
  pinned safety core) and materializes ONLY those into the runtime skills
  directory that OpenClaw scans. The full catalog stays canonical in the repo.
  Result: the injected skill index shrinks to the relevant subset, cutting
  per-turn tokens ~45-64% with no loss of tool-calling quality.

INTEGRATION POINT (important)
  - Canonical catalog (never mutated): repo  workspace/skills/          (192 skills)
  - Runtime dir OpenClaw scans (scoped):     ~/.openclaw/workspace/skills/
  Run this before an autonomous triage session (e.g. from the alert-receiver
  webhook) to scope the catalog to the incoming alert.

  NOTE: OpenClaw's listSkillDirs uses dirent.isDirectory(), which is FALSE for
  symlinked directories — so the scoped set must be REAL directories. We copy.

SAFETY
  - Dry-run by default. Nothing is written without --apply.
  - --apply only removes skill subdirs (dirs containing SKILL.md) from the target
    and copies the selected ones in; other files in the target are left alone.
  - --restore-all re-materializes the entire catalog (undo).

USAGE
  # See what would be selected for an alert (no writes):
  python3 select_skills.py --alert '{"alertname":"InstanceDown","device_platform":"iosxe"}'

  # Scope the runtime dir for that alert:
  python3 select_skills.py --alert @/tmp/alert.json --apply

  # Free-text query:
  python3 select_skills.py --query "bgp neighbor flapping on core router" --k 10 --apply

  # Restore the full catalog:
  python3 select_skills.py --restore-all --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO / "workspace" / "skills"
DEFAULT_TARGET = Path(os.path.expanduser("~/.openclaw/workspace/skills"))

# Skills that must always be present regardless of the query. Safety / mandatory
# workflow skills — keep this conservative.
DEFAULT_PINS = [
    "alert-triage",
    "gait-session-tracking",
    "memory-management",
    "humanrail-escalation",
    "domain-expert-delegation",
]


# ── Frontmatter / catalog ─────────────────────────────────────────────────────
def parse_frontmatter(md: str) -> dict:
    if not md.startswith("---"):
        return {}
    parts = md.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1]) or {}
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def load_catalog(catalog: Path) -> list[dict]:
    skills = []
    for skill_md in sorted(catalog.glob("*/SKILL.md")):
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        skills.append({
            "id": skill_md.parent.name,
            "name": fm.get("name") or skill_md.parent.name,
            "description": (fm.get("description") or "").strip(),
            "dir": skill_md.parent,
        })
    return skills


# ── Ranking ───────────────────────────────────────────────────────────────────
_STOP = {"the", "a", "an", "and", "or", "of", "to", "on", "in", "for", "with",
         "is", "are", "has", "have", "been", "device", "network"}


def _terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 2}


def rank_keyword(query: str, skills: list[dict]) -> list[tuple[float, dict]]:
    q = _terms(query)
    scored = []
    for s in skills:
        overlap = len(q & _terms(f"{s['name']} {s['description']}"))
        scored.append((float(overlap), s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def rank_embeddings(query: str, skills: list[dict]) -> list[tuple[float, dict]] | None:
    """Optional semantic ranker. Uses sentence-transformers with the same model
    the Memory MCP uses (all-MiniLM-L6-v2). Returns None if unavailable."""
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        return None
    model_name = os.environ.get("MEMORY_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    corpus = [f"{s['name']}. {s['description']}" for s in skills]
    q_emb = model.encode(query, convert_to_tensor=True, normalize_embeddings=True)
    c_emb = model.encode(corpus, convert_to_tensor=True, normalize_embeddings=True)
    sims = util.cos_sim(q_emb, c_emb)[0].tolist()
    scored = list(zip((float(x) for x in sims), skills))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def select(query: str, skills: list[dict], k: int, pins: list[str],
           ranker: str) -> tuple[list[dict], str]:
    scored = None
    used = ranker
    if ranker in ("embeddings", "auto"):
        scored = rank_embeddings(query, skills)
        if scored is None:
            if ranker == "embeddings":
                print("WARN: sentence-transformers not installed; "
                      "falling back to keyword ranker.", file=sys.stderr)
            used = "keyword"
    if scored is None:
        scored = rank_keyword(query, skills)
        used = "keyword" if ranker != "embeddings" else used

    by_id = {s["id"]: s for s in skills}
    chosen: dict[str, dict] = {}

    # Pins first (always included if present in catalog).
    for pid in pins:
        if pid in by_id:
            chosen[pid] = by_id[pid]

    # Then top-ranked with a positive score, until we hit k total.
    for score, s in scored:
        if len(chosen) >= max(k, len(chosen)):
            break
        if score <= 0:
            continue
        chosen.setdefault(s["id"], s)
        if len(chosen) >= k + len([p for p in pins if p in by_id]):
            break

    return list(chosen.values()), used


# ── Materialization (real dirs; symlinked dirs are skipped by OpenClaw) ────────
def _skill_subdirs(target: Path) -> list[Path]:
    if not target.exists():
        return []
    return [p for p in target.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]


def materialize(selected: list[dict], target: Path, apply: bool, catalog: Path) -> dict:
    """Rebuild the target's skill set to exactly `selected`. Only touches skill
    subdirs (dirs with a SKILL.md); leaves any other target files alone."""
    # Hard safety guard: never write to the canonical catalog. This catches the
    # case where the runtime target is a symlink pointing back at the catalog.
    if apply and os.path.realpath(target) == os.path.realpath(catalog):
        raise RuntimeError(
            f"Refusing to apply: target ({target}) resolves to the same directory "
            f"as the catalog ({catalog}). This would destroy the canonical catalog. "
            "Point --target at a separate real directory."
        )
    existing = {p.name for p in _skill_subdirs(target)}
    want = {s["id"] for s in selected}
    to_remove = sorted(existing - want)
    to_add = sorted(want - existing)
    plan = {"target": str(target), "keep": sorted(existing & want),
            "remove": to_remove, "add": to_add, "final_count": len(want)}
    if not apply:
        return plan
    target.mkdir(parents=True, exist_ok=True)
    for rid in to_remove:
        shutil.rmtree(target / rid, ignore_errors=True)
    src_by_id = {s["id"]: s["dir"] for s in selected}
    for aid in to_add:
        shutil.copytree(src_by_id[aid], target / aid, dirs_exist_ok=True)
    return plan


# ── Reporting ──────────────────────────────────────────────────────────────────
def index_tokens(skills: list[dict]) -> int:
    """Rough token estimate of the injected index (name + description lines)."""
    block = "\n".join(f"- **{s['name']}**: {s['description']}" for s in skills)
    return len(block) // 4


def build_query(args) -> str:
    parts = []
    if args.query:
        parts.append(args.query)
    if args.alert:
        raw = args.alert
        if raw.startswith("@"):
            raw = Path(os.path.expanduser(raw[1:])).read_text(encoding="utf-8")
        try:
            alert = json.loads(raw)
            for key in ("alertname", "summary", "device_platform", "device_role",
                        "severity", "description"):
                if alert.get(key):
                    parts.append(str(alert[key]))
        except json.JSONDecodeError:
            parts.append(raw)
    return " ".join(parts)


def main() -> int:
    p = argparse.ArgumentParser(description="Scope the runtime skill catalog by relevance")
    p.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG,
                   help=f"Canonical full catalog (default: {DEFAULT_CATALOG})")
    p.add_argument("--target", type=Path, default=DEFAULT_TARGET,
                   help=f"Runtime skills dir OpenClaw scans (default: {DEFAULT_TARGET})")
    p.add_argument("--query", default="", help="Free-text query")
    p.add_argument("--alert", default="", help="Alert JSON inline or @/path/to/file.json")
    p.add_argument("--k", type=int, default=8, help="Top-k skills to select (excl. pins)")
    p.add_argument("--pin", default=",".join(DEFAULT_PINS),
                   help="Comma-separated skill ids always kept")
    p.add_argument("--ranker", choices=["keyword", "embeddings", "auto"], default="auto")
    p.add_argument("--apply", action="store_true", help="Actually write the target dir")
    p.add_argument("--restore-all", action="store_true",
                   help="Materialize the FULL catalog into the target (undo scoping)")
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    args = p.parse_args()

    if not args.catalog.exists():
        print(f"ERROR: catalog not found: {args.catalog}", file=sys.stderr)
        return 2

    catalog = load_catalog(args.catalog)
    pins = [x.strip() for x in args.pin.split(",") if x.strip()]

    if args.restore_all:
        selected, ranker_used = catalog, "restore-all"
        query = "(full catalog)"
    else:
        query = build_query(args)
        if not query.strip():
            print("ERROR: provide --query and/or --alert (or use --restore-all).",
                  file=sys.stderr)
            return 2
        selected, ranker_used = select(query, catalog, args.k, pins, args.ranker)

    try:
        plan = materialize(selected, args.target, args.apply, args.catalog)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    full_tok, sel_tok = index_tokens(catalog), index_tokens(selected)
    saved = full_tok - sel_tok
    pct = (saved / full_tok * 100) if full_tok else 0.0

    if args.json:
        print(json.dumps({
            "query": query, "ranker": ranker_used,
            "selected": [s["id"] for s in selected],
            "catalog_size": len(catalog), "selected_size": len(selected),
            "index_tokens_full": full_tok, "index_tokens_selected": sel_tok,
            "index_tokens_saved": saved, "index_tokens_saved_pct": round(pct, 1),
            "applied": args.apply, "plan": plan,
        }, indent=2))
        return 0

    line = "=" * 68
    print(line)
    print("NetClaw Skill Selector" + ("  [APPLIED]" if args.apply else "  [DRY RUN]"))
    print(line)
    print(f"Query:   {query[:80]}")
    print(f"Ranker:  {ranker_used}")
    print(f"Catalog: {len(catalog)} skills  →  Selected: {len(selected)} skills")
    print(line)
    print("SELECTED:")
    pinset = {x for x in pins}
    for s in sorted(selected, key=lambda s: (s["id"] not in pinset, s["id"])):
        tag = " (pinned)" if s["id"] in pinset else ""
        print(f"  - {s['id']}{tag}")
    print(line)
    print("INDEX TOKEN IMPACT (per turn, injected skill index):")
    print(f"  Full catalog:  ~{full_tok:,} tokens")
    print(f"  Selected:      ~{sel_tok:,} tokens")
    print(f"  Saved:         ~{saved:,} tokens ({pct:.0f}% smaller)")
    print(line)
    print(f"TARGET: {plan['target']}")
    print(f"  keep {len(plan['keep'])} | add {len(plan['add'])} | remove {len(plan['remove'])} "
          f"| final {plan['final_count']}")
    if not args.apply:
        print("  (dry run — re-run with --apply to write)")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
