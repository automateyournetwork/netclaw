"""
Sweep 3 — coverage gaps.

60 candidates (40 skills + 20 MCP servers, see candidates.py) checked against
all 227 existing skill descriptions to confirm each candidate is genuinely
uncovered, not just superficially different.

Same two-phase, fully-parallelized pattern proven in sweep2:
- Phase A: for each candidate, chunk the 227 existing skills into batches of
  CHUNK_SIZE and ask one terse noul per existing skill ("is candidate X
  already covered by existing skill Y?"), rubric stated once in state.
- Phase B: self-consistency reruns (concurrent fan-out) for mid-band answers.

A candidate is a "confirmed gap" only if every existing-skill coverage check
(after resolving mid-band via its stable self-consistency mean) stays below
COVERAGE_THRESHOLD — i.e. Jev found no existing skill that already covers it.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import common
from candidates import CANDIDATE_MCPS, CANDIDATE_SKILLS

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "workspace" / "skills"
OUT_PATH = Path(__file__).resolve().parent / "data" / "sweep3_raw.json"

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.S)
CHUNK_SIZE = 50
MAX_CALL_TOKENS = 20_000
COVERAGE_THRESHOLD = 0.40  # below this on every existing skill => confirmed gap

COVERAGE_DEFINITION = (
    "A candidate capability is 'already covered' by an existing skill when an agent "
    "that needed the candidate's capability could just use the existing skill instead, "
    "because the existing skill's real scope (not just shared keywords) already includes it. "
    "Superficial keyword overlap (e.g. both mention 'network') without real functional "
    "coverage does not count as covered."
)


def extract_description(content: str) -> str:
    fm_match = FRONTMATTER_PATTERN.match(content)
    if not fm_match:
        return ""
    fm = fm_match.group(1)
    lines = fm.splitlines()
    in_desc = False
    base_indent = None
    desc_lines: list[str] = []
    for line in lines:
        if not in_desc:
            m = re.match(r"^description:\s*(.*)$", line)
            if m:
                in_desc = True
                rest = m.group(1).strip()
                if rest and rest not in (">", "|", ">-", "|-", ">+", "|+"):
                    return rest.strip("\"'")
                continue
        else:
            if line.strip() == "":
                continue
            indent = len(line) - len(line.lstrip())
            if base_indent is None:
                base_indent = indent
            if indent < base_indent:
                break
            desc_lines.append(line.strip())
    desc = " ".join(desc_lines).strip()
    if desc:
        return desc
    body = content[fm_match.end():].strip()
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line
    return ""


def load_existing_skills() -> list[tuple[str, str]]:
    items = []
    for d in sorted(SKILLS_DIR.iterdir()):
        skill_file = d / "SKILL.md"
        if d.is_dir() and skill_file.is_file():
            content = skill_file.read_text(encoding="utf-8", errors="replace")
            items.append((d.name, extract_description(content)))
    return items


def load_candidates() -> list[tuple[str, str, str]]:
    out = [(name, desc, "skill") for name, desc in CANDIDATE_SKILLS]
    out += [(name, desc, "mcp") for name, desc in CANDIDATE_MCPS]
    return out


def make_state(cand_name: str, cand_desc: str, kind: str) -> dict:
    return {
        "candidate_name": cand_name,
        "candidate_description": cand_desc,
        "candidate_kind": kind,
        "coverage_definition": COVERAGE_DEFINITION,
    }


def make_question(existing_name: str, existing_desc: str) -> dict:
    return {
        "type": "noul",
        "instructions": f"Per coverage_definition in state: is the candidate already covered by existing skill '{existing_name}' ({existing_desc})?",
        "criteria": {"true": "existing skill already covers it", "false": "existing skill does not cover it"},
    }


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _checkpoint(results_by_candidate: dict) -> None:
    OUT_PATH.write_text(
        json.dumps(sorted(results_by_candidate.values(), key=lambda r: r["candidate"]), indent=2),
        encoding="utf-8",
    )


def estimate() -> tuple[float, int]:
    candidates = load_candidates()
    existing = load_existing_skills()
    total_tokens = 0
    num_calls = 0
    for cand_name, cand_desc, kind in candidates:
        state = make_state(cand_name, cand_desc, kind)
        state_tokens = common.est_tokens(state)
        for batch in chunks(existing, CHUNK_SIZE):
            q_tokens = sum(common.est_tokens(make_question(n, d)) for n, d in batch)
            total_tokens += state_tokens + q_tokens
            num_calls += 1
    return total_tokens / 1_000_000 * common.PRICE_PER_MTOK_INPUT, num_calls


def run(max_workers: int = 12, recheck_workers: int = 32) -> list[dict]:
    candidates = load_candidates()
    existing = load_existing_skills()
    jobs = []  # (cand_name, cand_desc, kind, batch)
    for cand_name, cand_desc, kind in candidates:
        for batch in chunks(existing, CHUNK_SIZE):
            jobs.append((cand_name, cand_desc, kind, batch))

    def primary_work(job):
        cand_name, cand_desc, kind, batch = job
        state = make_state(cand_name, cand_desc, kind)
        questions = {existing_name: make_question(existing_name, existing_desc) for existing_name, existing_desc in batch}
        state_tok = common.est_tokens(state)
        q_tok = sum(common.est_tokens(q) for q in questions.values())
        assert state_tok + q_tok < MAX_CALL_TOKENS, f"batch too large for {cand_name}: ~{state_tok + q_tok} tokens"
        data = common.call(state, questions)
        answers = {qid: ans["noul"] for qid, ans in data["answers"].items()}
        return cand_name, cand_desc, kind, state, questions, answers

    results_by_candidate: dict[str, dict] = {}
    mid_band_targets = []  # (cand_name, state, existing_name, question)

    print(f"[sweep3] phase A: {len(jobs)} primary calls", flush=True)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(primary_work, job): job[0] for job in jobs}
        done, total = 0, len(futures)
        for fut in as_completed(futures):
            name = futures[fut]
            done += 1
            try:
                cand_name, cand_desc, kind, state, questions, answers = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"[sweep3] phase A ERROR candidate={name}: {e}", flush=True)
                continue
            acc = results_by_candidate.setdefault(
                cand_name, {"candidate": cand_name, "description": cand_desc, "kind": kind, "coverage": {}, "stability": {}}
            )
            acc["coverage"].update(answers)
            for existing_name, val in answers.items():
                if common.is_mid_band(val):
                    mid_band_targets.append((cand_name, state, existing_name, questions[existing_name]))
            if done % 25 == 0 or done == total:
                print(f"[sweep3] phase A progress {done}/{total}, cost so far ${common.cost_so_far():.4f}", flush=True)
                _checkpoint(results_by_candidate)

    print(f"[sweep3] phase A done. {len(mid_band_targets)} mid-band checks need self-consistency reruns.", flush=True)

    def recheck_work(target):
        cand_name, state, existing_name, question = target
        result = common.self_consistency_recheck(state, question)
        return cand_name, existing_name, result

    if mid_band_targets:
        print(f"[sweep3] phase B: {len(mid_band_targets)} targets, {recheck_workers} workers", flush=True)
        with ThreadPoolExecutor(max_workers=recheck_workers) as ex:
            futures = {ex.submit(recheck_work, t): t for t in mid_band_targets}
            done, total = 0, len(futures)
            for fut in as_completed(futures):
                done += 1
                cand_name = futures[fut][0]
                try:
                    cand_name, existing_name, result = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"[sweep3] phase B ERROR candidate={cand_name}: {e}", flush=True)
                    continue
                results_by_candidate[cand_name]["stability"][existing_name] = result
                if done % 25 == 0 or done == total:
                    print(f"[sweep3] phase B progress {done}/{total}, cost so far ${common.cost_so_far():.4f}", flush=True)
                    _checkpoint(results_by_candidate)

    return sorted(results_by_candidate.values(), key=lambda r: r["candidate"])


if __name__ == "__main__":
    est_usd, num_calls = estimate()
    print(f"[sweep3] candidates: {len(CANDIDATE_SKILLS) + len(CANDIDATE_MCPS)}, calls: {num_calls}")
    common.enforce_budget("sweep3", est_usd)
    results = run()
    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    snap = common.usage_snapshot()
    print(f"[sweep3] done. {len(results)} candidates. actual cost so far: ${common.cost_so_far():.4f}  usage={snap}")
