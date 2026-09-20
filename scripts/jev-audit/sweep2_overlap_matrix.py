"""
Sweep 2 — overlap matrix (descriptions only).

Spec asked for a pairwise comparison across all 227 skills, which is
C(227,2) = 25,651 pairs. Issuing 25,651 separate calls would ignore Jev's own
guidance ("batch questions, not calls; adding questions to a call is nearly
free"), so instead: sort skills by name, and for each anchor skill i, issue
one or more calls whose state is the anchor's description plus the shared
overlap rubric (stated once, not repeated per question) and whose questions
are a short per-skill overlap check for every later skill j>i.

v2 fix: the first version repeated a long boilerplate paragraph inside every
single question's `instructions`. For the first anchor (226 later skills)
that produced a ~232KB / ~58k-token request — right at Jev's 64k total
context ceiling — which stalled outbound (TCP send queue never drained,
process CPU time frozen for minutes; killed and diagnosed live). Fix: state
the rubric once in `state`, keep each question to one short sentence, and
hard-chunk each anchor's later-skills into batches of CHUNK_SIZE so no call
gets anywhere near the limit.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import common

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "workspace" / "skills"
OUT_PATH = Path(__file__).resolve().parent / "data" / "sweep2_raw.json"

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.S)
CHUNK_SIZE = 50
MAX_CALL_TOKENS = 20_000  # hard safety margin, well under the documented 64k ceiling

OVERLAP_DEFINITION = (
    "Two skills 'overlap in trigger territory' when an agent choosing which skill to "
    "invoke for a given task would plausibly be unsure whether to pick the anchor skill "
    "or the compared skill, because they claim genuinely similar situations, keywords, or "
    "scope. Superficial similarity (e.g. both mention 'network') without real scope overlap "
    "does not count."
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


def load_descriptions() -> list[tuple[str, str]]:
    items = []
    for d in sorted(SKILLS_DIR.iterdir()):
        skill_file = d / "SKILL.md"
        if d.is_dir() and skill_file.is_file():
            content = skill_file.read_text(encoding="utf-8", errors="replace")
            items.append((d.name, extract_description(content)))
    return items


def make_state(name_i: str, desc_i: str) -> dict:
    return {"anchor_skill": name_i, "anchor_description": desc_i, "overlap_definition": OVERLAP_DEFINITION}


def make_question(name_j: str, desc_j: str) -> dict:
    return {
        "type": "noul",
        "instructions": f"Per the overlap_definition in state: does skill '{name_j}' ({desc_j}) overlap with the anchor skill?",
        "criteria": {"true": "genuine trigger-territory overlap", "false": "clearly different scope"},
    }


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def estimate() -> tuple[float, int, int]:
    items = load_descriptions()
    n = len(items)
    total_tokens = 0
    num_pairs = 0
    num_calls = 0
    for i in range(n):
        name_i, desc_i = items[i]
        later = items[i + 1 :]
        state = make_state(name_i, desc_i)
        state_tokens = common.est_tokens(state)
        for batch in chunks(later, CHUNK_SIZE):
            q_tokens = sum(common.est_tokens(make_question(nj, dj)) for nj, dj in batch)
            total_tokens += state_tokens + q_tokens
            num_pairs += len(batch)
            num_calls += 1
    return total_tokens / 1_000_000 * common.PRICE_PER_MTOK_INPUT, num_pairs, num_calls


def _checkpoint(results_by_anchor: dict) -> None:
    OUT_PATH.write_text(
        json.dumps(sorted(results_by_anchor.values(), key=lambda r: r["anchor"]), indent=2),
        encoding="utf-8",
    )


def run(max_workers: int = 12, recheck_workers: int = 48) -> list[dict]:
    """Two decoupled phases, each independently parallelized:
    Phase A gets the primary noul for every pair (fast, small calls).
    Phase B reruns only the mid-band pairs for self-consistency.
    Doing self-consistency inline per-chunk (v1 bug) let one chunk with many
    mid-band answers hog its worker thread for up to 50*5=250 sequential
    calls, starving the progress counter — indistinguishable from a stall."""
    items = load_descriptions()
    n = len(items)
    jobs = []  # (anchor_name, anchor_desc, batch)
    for i in range(n):
        name_i, desc_i = items[i]
        later = items[i + 1 :]
        for batch in chunks(later, CHUNK_SIZE):
            jobs.append((name_i, desc_i, batch))

    def primary_work(job):
        name_i, desc_i, batch = job
        state = make_state(name_i, desc_i)
        questions = {name_j: make_question(name_j, desc_j) for name_j, desc_j in batch}
        state_tok = common.est_tokens(state)
        q_tok = sum(common.est_tokens(q) for q in questions.values())
        assert state_tok + q_tok < MAX_CALL_TOKENS, f"batch too large for {name_i}: ~{state_tok + q_tok} tokens"
        data = common.call(state, questions)
        pairs = {qid: ans["noul"] for qid, ans in data["answers"].items()}
        return name_i, state, questions, pairs

    results_by_anchor: dict[str, dict] = {}
    mid_band_targets = []  # (anchor_name, state, question_key, question)

    print(f"[sweep2] phase A: {len(jobs)} primary calls", flush=True)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(primary_work, job): job[0] for job in jobs}
        done, total = 0, len(futures)
        for fut in as_completed(futures):
            name = futures[fut]
            done += 1
            try:
                name_i, state, questions, pairs = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"[sweep2] phase A ERROR anchor={name}: {e}", flush=True)
                continue
            acc = results_by_anchor.setdefault(name_i, {"anchor": name_i, "pairs": {}, "stability": {}})
            acc["pairs"].update(pairs)
            for name_j, val in pairs.items():
                if common.is_mid_band(val):
                    mid_band_targets.append((name_i, state, name_j, questions[name_j]))
            if done % 25 == 0 or done == total:
                print(f"[sweep2] phase A progress {done}/{total}, cost so far ${common.cost_so_far():.4f}", flush=True)
                _checkpoint(results_by_anchor)

    print(f"[sweep2] phase A done. {len(mid_band_targets)} mid-band pairs need self-consistency reruns.", flush=True)

    def recheck_work(target):
        name_i, state, name_j, question = target
        result = common.self_consistency_recheck(state, question)
        return name_i, name_j, result

    print(f"[sweep2] phase B: {len(mid_band_targets)} targets x 5 sequential calls each, {recheck_workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=recheck_workers) as ex:
        futures = {ex.submit(recheck_work, t): t for t in mid_band_targets}
        done, total = 0, len(futures)
        for fut in as_completed(futures):
            done += 1
            name_i = futures[fut][0]
            try:
                name_i, name_j, result = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"[sweep2] phase B ERROR anchor={name_i}: {e}", flush=True)
                continue
            results_by_anchor[name_i]["stability"][name_j] = result
            if done % 25 == 0 or done == total or total == 0:
                print(f"[sweep2] phase B progress {done}/{total}, cost so far ${common.cost_so_far():.4f}", flush=True)
                _checkpoint(results_by_anchor)

    return sorted(results_by_anchor.values(), key=lambda r: r["anchor"])


if __name__ == "__main__":
    est_usd, num_pairs, num_calls = estimate()
    print(f"[sweep2] pairs covered: {num_pairs}, calls: {num_calls}")
    common.enforce_budget("sweep2", est_usd)
    results = run()
    OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    snap = common.usage_snapshot()
    print(f"[sweep2] done. {len(results)} anchors. actual cost so far: ${common.cost_so_far():.4f}  usage={snap}")
