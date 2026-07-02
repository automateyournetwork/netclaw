#!/usr/bin/env python3
"""
NetClaw model harness — exercise real skills against an Ollama model and
measure tool-calling behavior + token burn per triage run.

Purpose:
  Answer two questions before committing to a model/plan:
    1. Does tool-calling hold up in a real NetClaw MCP-style loop?
    2. How many tokens does a typical triage run burn? (quota planning)

Design:
  - Builds the same system prompt NetClaw uses: SOUL.md + AGENTS.md + TOOLS.md
    + a skill index (name/description of every skill) + the active skill body.
  - Registers MOCK tools that mirror the alert-triage skill (Prometheus, pyATS,
    Loki, Alertmanager, Discord) and returns canned data, so the loop runs with
    no live infrastructure.
  - Runs the agentic loop against Ollama's native /api/chat endpoint (works for
    both local and cloud; cloud just needs OLLAMA_API_KEY).
  - Reports per-turn + total token usage and every tool call it made.

Usage:
  # Inspect the prompt + token estimate WITHOUT calling any model:
  python3 triage_harness.py --dry-run

  # Run against Ollama Cloud DeepSeek V4-Pro (set key + model first):
  export OLLAMA_API_KEY=sk-...            # from your Ollama Pro account
  python3 triage_harness.py \
      --url https://ollama.com \
      --model deepseek-v4-pro:cloud \
      --scenario instance_down

  # Compare front-load cost: full skill index vs retrieved subset vs none
  python3 triage_harness.py --dry-run --skill-index full
  python3 triage_harness.py --dry-run --skill-index retrieved
  python3 triage_harness.py --dry-run --skill-index none

No dependencies beyond the repo's existing httpx + PyYAML.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
import yaml

# ── Paths ────────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parents[2]
WS = REPO / "workspace"
SKILLS_DIR = WS / "skills"

# Load repo .env so OLLAMA_BASE_URL (local proxy) and friends are available.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")
except ImportError:
    pass


# ── Workspace / prompt assembly ───────────────────────────────────────────────
def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def parse_frontmatter(md: str) -> dict:
    """Extract the leading YAML frontmatter block from a SKILL.md file."""
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


def load_skill_index(skills_dir: Path = SKILLS_DIR) -> list[dict]:
    """Return [{name, description, path, body}] for every skill with a SKILL.md."""
    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        md = read_text(skill_md)
        fm = parse_frontmatter(md)
        name = fm.get("name") or skill_md.parent.name
        desc = (fm.get("description") or "").strip()
        skills.append(
            {"name": name, "description": desc, "path": skill_md, "body": md}
        )
    return skills


def select_skills(skills: list[dict], query: str, k: int = 8) -> list[dict]:
    """Cheap keyword-overlap ranker — stand-in for the ChromaDB retrieval you'd
    use in production. Good enough to demonstrate the token delta."""
    q_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for s in skills:
        text = f"{s['name']} {s['description']}".lower()
        terms = set(re.findall(r"[a-z0-9]+", text))
        score = len(q_terms & terms)
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for score, s in scored[:k] if score > 0]


def build_skill_index_block(skills: list[dict]) -> str:
    lines = ["## Available Skills", ""]
    for s in skills:
        lines.append(f"- **{s['name']}**: {s['description']}")
    return "\n".join(lines)


def build_system_prompt(active_skill: str, index_mode: str, query: str,
                        skills_dir: Path = SKILLS_DIR) -> tuple[str, dict]:
    """Assemble the system prompt the way NetClaw would. Returns (prompt, stats)."""
    core = "\n\n".join(
        read_text(WS / f) for f in ("SOUL.md", "AGENTS.md", "TOOLS.md")
    )
    all_skills = load_skill_index(skills_dir)

    if index_mode == "full":
        index_skills = all_skills
    elif index_mode == "retrieved":
        index_skills = select_skills(all_skills, query, k=8)
    else:  # none
        index_skills = []

    index_block = build_skill_index_block(index_skills) if index_skills else ""

    # Active skill body (full procedure) — always loaded on invocation.
    body = ""
    for s in all_skills:
        if s["name"] == active_skill:
            body = s["body"]
            break

    parts = [core]
    if index_block:
        parts.append(index_block)
    if body:
        parts.append(f"## Active Skill: {active_skill}\n\n{body}")
    prompt = "\n\n---\n\n".join(p for p in parts if p.strip())

    stats = {
        "index_mode": index_mode,
        "index_skill_count": len(index_skills),
        "total_skill_count": len(all_skills),
        "system_prompt_chars": len(prompt),
        "system_prompt_est_tokens": len(prompt) // 4,
    }
    return prompt, stats


# ── Mock tools (mirror the alert-triage skill's real MCP tools) ───────────────
# Schemas use the OpenAI/Ollama "function" shape. Handlers return canned data
# keyed off the active scenario so a full loop runs with no live backend.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "prometheus_query",
            "description": "Run an instant PromQL query against Prometheus/VictoriaMetrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "PromQL expression"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prometheus_range_query",
            "description": "Run a PromQL range query for a time-series trend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "minutes": {"type": "integer", "description": "Lookback window in minutes"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "alertmanager_alerts",
            "description": "List currently firing alerts, optionally filtered by alertname.",
            "parameters": {
                "type": "object",
                "properties": {"alertname": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pyats_run_command",
            "description": "Run a read-only show command on a network device via pyATS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device": {"type": "string"},
                    "command": {"type": "string"},
                },
                "required": ["device", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "loki_query",
            "description": "Query Loki logs with a LogQL expression.",
            "parameters": {
                "type": "object",
                "properties": {"logql": {"type": "string"}},
                "required": ["logql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "post_discord",
            "description": "Post the final triage report to the Discord webhook.",
            "parameters": {
                "type": "object",
                "properties": {"report": {"type": "string"}},
                "required": ["report"],
            },
        },
    },
]


# ── Scenarios ─────────────────────────────────────────────────────────────────
SCENARIOS = {
    "instance_down": {
        "alert": {
            "alertname": "InstanceDown",
            "device_name": "core-sw1",
            "device_ip": "192.168.3.2",
            "device_platform": "iosxe",
            "device_role": "switch",
            "severity": "critical",
            "summary": "Prometheus target core-sw1 has been down for 3m",
            "status": "firing",
        },
        "mock": {
            "prometheus_query": {
                "default": {"result": [{"metric": {"instance": "core-sw1"}, "value": [0]}]},
            },
            "alertmanager_alerts": {
                "default": [{"labels": {"alertname": "InstanceDown", "instance": "core-sw1"}, "status": {"state": "active"}}]
            },
            "pyats_run_command": {
                "default": "Connection timed out; remote host not responding"
            },
            "loki_query": {
                "default": [{"ts": "2026-07-02T10:14:59Z", "line": "%LINK-3-UPDOWN: Interface GigabitEthernet1/0/1, changed state to down"}]
            },
            "prometheus_range_query": {"default": {"result": []}},
            "post_discord": {"default": {"ok": True, "status": 204}},
        },
    },
    "high_cpu": {
        "alert": {
            "alertname": "HighCPU",
            "device_name": "local-ai",
            "device_ip": "192.168.3.250",
            "device_platform": "linux",
            "device_role": "hypervisor",
            "severity": "warning",
            "summary": "CPU on local-ai above 90% for 10m",
            "status": "firing",
        },
        "mock": {
            "prometheus_query": {"default": {"result": [{"metric": {"instance": "local-ai"}, "value": [0.94]}]}},
            "prometheus_range_query": {"default": {"result": [{"values": [[0, 0.6], [60, 0.8], [120, 0.94]]}]}},
            "alertmanager_alerts": {"default": [{"labels": {"alertname": "HighCPU", "instance": "local-ai"}, "status": {"state": "active"}}]},
            "loki_query": {"default": [{"ts": "2026-07-02T10:12:00Z", "line": "ollama runner: model deepseek-v4 loaded, 94% cpu"}]},
            "pyats_run_command": {"default": "N/A (linux host)"},
            "post_discord": {"default": {"ok": True, "status": 204}},
        },
    },
}


def run_mock_tool(scenario: dict, name: str, args: dict) -> str:
    table = scenario["mock"].get(name)
    if table is None:
        return json.dumps({"error": f"unknown tool {name}"})
    payload = table.get("default", {"note": "no mock data"})
    return json.dumps(payload)


# ── Ollama native /api/chat call ──────────────────────────────────────────────
def call_ollama(url: str, api_key: str, model: str, messages: list, tools: list,
                temperature: float, timeout: float) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "options": {"temperature": temperature},
    }
    resp = httpx.post(f"{url.rstrip('/')}/api/chat", headers=headers,
                      json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# ── Agentic loop ──────────────────────────────────────────────────────────────
def run_loop(args, system_prompt: str, scenario: dict) -> dict:
    alert_json = json.dumps(scenario["alert"], indent=2)
    user_msg = (
        "An alert fired. Investigate it following your alert-triage procedure, "
        "call the tools you need, then post the final triage report via "
        f"post_discord.\n\nAlert context:\n{alert_json}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    turns = []
    tool_calls_made = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for turn in range(1, args.max_turns + 1):
        t0 = time.time()
        try:
            data = call_ollama(args.url, args.api_key, args.model, messages,
                               TOOL_SCHEMAS, args.temperature, args.timeout)
        except httpx.HTTPStatusError as e:
            detail = f"HTTP {e.response.status_code}: {e.response.text[:400]}"
            if e.response.status_code == 401:
                detail += (
                    "\n  → The endpoint proxies to Ollama Cloud but has no valid "
                    "credential.\n    Fix on the ollama host: run `ollama signin` (or set "
                    "OLLAMA_API_KEY\n    in the ollama server's environment and restart it). "
                    "Alternatively\n    pass a key to this harness: "
                    "OLLAMA_API_KEY=... python triage_harness.py ..."
                )
            return {"error": detail, "turns": turns}
        except httpx.HTTPError as e:
            return {"error": f"request failed: {e}", "turns": turns}
        dt = time.time() - t0

        msg = data.get("message", {}) or {}
        p_tok = data.get("prompt_eval_count", 0)
        c_tok = data.get("eval_count", 0)
        total_prompt_tokens += p_tok
        total_completion_tokens += c_tok

        raw_calls = msg.get("tool_calls") or []
        turn_calls = []
        for tc in raw_calls:
            fn = tc.get("function", {})
            cname = fn.get("name", "")
            cargs = fn.get("arguments", {})
            if isinstance(cargs, str):
                try:
                    cargs = json.loads(cargs)
                except json.JSONDecodeError:
                    cargs = {"_raw": cargs, "_valid_json": False}
            valid = cname in {t["function"]["name"] for t in TOOL_SCHEMAS}
            turn_calls.append({"name": cname, "args": cargs, "known_tool": valid})
            tool_calls_made.append(cname)

        turns.append({
            "turn": turn,
            "seconds": round(dt, 2),
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "tool_calls": [c["name"] for c in turn_calls],
            "content_preview": (msg.get("content") or "")[:200],
        })

        # Append assistant message
        messages.append(msg)

        if not raw_calls:
            # Model produced a final answer with no tool calls -> done.
            break

        # Execute mock tools and feed results back.
        for c in turn_calls:
            result = run_mock_tool(scenario, c["name"], c["args"])
            messages.append({
                "role": "tool",
                "tool_name": c["name"],
                "content": result,
            })
        # If it just posted to discord, treat as terminal.
        if any(c["name"] == "post_discord" for c in turn_calls):
            break

    return {
        "turns": turns,
        "tool_calls_made": tool_calls_made,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
    }


# ── Reporting ─────────────────────────────────────────────────────────────────
def print_report(args, prompt_stats: dict, result: dict) -> None:
    line = "=" * 68
    print(line)
    print("NetClaw Model Harness — Report")
    print(line)
    print(f"Model:        {args.model}")
    print(f"Endpoint:     {args.url}")
    print(f"Scenario:     {args.scenario}")
    print(f"Skill index:  {prompt_stats['index_mode']} "
          f"({prompt_stats['index_skill_count']}/{prompt_stats['total_skill_count']} skills)")
    print(f"System prompt: {prompt_stats['system_prompt_chars']:,} chars "
          f"(~{prompt_stats['system_prompt_est_tokens']:,} tokens)")
    print(line)

    if "error" in result:
        print(f"ERROR: {result['error']}")
        if result.get("turns"):
            print("Partial turns before failure:")
            for t in result["turns"]:
                print(f"  turn {t['turn']}: {t['tool_calls']}")
        return

    expected = {"prometheus_query", "prometheus_range_query", "alertmanager_alerts",
                "pyats_run_command", "loki_query", "post_discord"}
    used = set(result["tool_calls_made"])
    unknown = [c for c in result["tool_calls_made"]
               if c not in {t["function"]["name"] for t in TOOL_SCHEMAS}]

    print("PER-TURN:")
    for t in result["turns"]:
        calls = ", ".join(t["tool_calls"]) or "(final answer)"
        print(f"  turn {t['turn']:>2} | {t['seconds']:>5}s | "
              f"in {t['prompt_tokens']:>6} / out {t['completion_tokens']:>5} | {calls}")
    print(line)
    print("TOOL-CALLING:")
    print(f"  Total tool calls:     {len(result['tool_calls_made'])}")
    print(f"  Distinct tools used:  {sorted(used) or '(none)'}")
    print(f"  Hallucinated tools:   {unknown or '(none)'}")
    print(f"  Posted final report:  {'yes' if 'post_discord' in used else 'NO'}")
    print(line)
    print("TOKEN BURN (one triage run):")
    print(f"  Prompt (input) tokens:     {result['total_prompt_tokens']:,}")
    print(f"  Completion (output) tokens:{result['total_completion_tokens']:,}")
    print(f"  TOTAL tokens:              {result['total_tokens']:,}")
    print(line)
    # Quota projection helper
    tot = result["total_tokens"]
    if tot:
        print("QUOTA PROJECTION (rough — tokens only, excludes server overhead):")
        for label, runs in (("per 10 triage runs", 10), ("per 100 runs", 100),
                            ("per day @ 1 run/15min", 96), ("per week @ 1 run/15min", 96 * 7)):
            print(f"  {label:<28} {tot * runs:>12,} tokens")
        print(line)


def dry_run_report(args, prompt_stats: dict, system_prompt: str) -> None:
    line = "=" * 68
    print(line)
    print("DRY RUN — prompt assembled, no model called")
    print(line)
    print(f"Scenario:      {args.scenario}")
    print(f"Skill index:   {prompt_stats['index_mode']} "
          f"({prompt_stats['index_skill_count']}/{prompt_stats['total_skill_count']} skills)")
    print(f"System prompt: {prompt_stats['system_prompt_chars']:,} chars "
          f"(~{prompt_stats['system_prompt_est_tokens']:,} tokens)")
    print(f"Tool schemas:  {len(TOOL_SCHEMAS)} tools registered")
    print(line)
    print("First 1200 chars of assembled system prompt:")
    print("-" * 68)
    print(system_prompt[:1200])
    print("-" * 68)
    print("(use --show-full-prompt to print the entire prompt)")
    if args.show_full_prompt:
        print(line)
        print(system_prompt)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser(description="NetClaw model / tool-calling harness")
    p.add_argument("--url", default=os.environ.get("OLLAMA_HARNESS_URL",
                   os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")),
                   help="Ollama endpoint (cloud: https://ollama.com)")
    p.add_argument("--api-key", default=os.environ.get("OLLAMA_API_KEY", ""),
                   help="Ollama API key (required for cloud). Defaults to $OLLAMA_API_KEY")
    p.add_argument("--model", default=os.environ.get("HARNESS_MODEL", "deepseek-v4-pro:cloud"),
                   help="Model tag, e.g. deepseek-v4-pro:cloud")
    p.add_argument("--scenario", choices=list(SCENARIOS), default="instance_down")
    p.add_argument("--skill", default="alert-triage", help="Active skill body to load")
    p.add_argument("--skill-index", choices=["full", "retrieved", "none"],
                   default="full", help="How much of the skill catalog to inject")
    p.add_argument("--skills-dir", type=Path, default=SKILLS_DIR,
                   help="Skills directory to build the index from (default: repo catalog). "
                        "Point at a scoped dir to measure the selector's effect.")
    p.add_argument("--max-turns", type=int, default=8)
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--dry-run", action="store_true",
                   help="Assemble the prompt and report token estimate; no API call")
    p.add_argument("--show-full-prompt", action="store_true")
    args = p.parse_args()

    scenario = SCENARIOS[args.scenario]
    query = f"{scenario['alert']['alertname']} {scenario['alert']['device_platform']} {scenario['alert']['summary']}"
    system_prompt, prompt_stats = build_system_prompt(args.skill, args.skill_index, query,
                                                      args.skills_dir)

    if args.dry_run:
        dry_run_report(args, prompt_stats, system_prompt)
        return 0

    if not args.api_key and "ollama.com" in args.url:
        print("ERROR: cloud endpoint requires an API key. "
              "Set OLLAMA_API_KEY or pass --api-key. "
              "Use --dry-run to inspect the prompt without a key.")
        return 2

    result = run_loop(args, system_prompt, scenario)
    print_report(args, prompt_stats, result)
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
