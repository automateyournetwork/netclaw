#!/usr/bin/env python3
"""netclaw-watch.py — Live formatted session log viewer.

Usage (from host):
  docker exec netclaw-convergence bash -c 'tail -f /root/.openclaw/agents/main/sessions/*.jsonl' | python3 scripts/netclaw-watch.py

Usage (inside container):
  tail -f /root/.openclaw/agents/main/sessions/*.jsonl | python3 /opt/netclaw/scripts/netclaw-watch.py
"""

import json
import sys
from datetime import datetime

ROLE_COLORS = {
    "user": "\033[1;36m",      # bold cyan
    "assistant": "\033[1;32m", # bold green
    "tool": "\033[1;33m",      # bold yellow
}
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"

def format_timestamp(ts):
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ""

def format_usage(usage):
    if not usage:
        return ""
    inp = usage.get("input", 0)
    out = usage.get("output", 0)
    model = ""
    cost = usage.get("cost", {}).get("total", 0)
    parts = [f"in:{inp:,}", f"out:{out:,}"]
    if cost:
        parts.append(f"${cost:.4f}")
    return f" {DIM}[{' | '.join(parts)}]{RESET}"

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        continue

    msg = d.get("message", {})
    role = msg.get("role", "")
    ts = format_timestamp(d.get("timestamp", ""))
    model = msg.get("model", "")
    usage = msg.get("usage")
    color = ROLE_COLORS.get(role, "")

    for c in msg.get("content", []):
        ctype = c.get("type", "")

        if ctype == "text":
            text = c.get("text", "")
            header = f"{color}{ts} [{role.upper()}]{RESET}"
            if model and role == "assistant":
                header += f" {DIM}({model}){RESET}"
            if usage and role == "assistant":
                header += format_usage(usage)
            print(f"\n{header}")
            # Indent multi-line text
            for tline in text.split("\n"):
                print(f"  {tline}")

        elif ctype == "toolCall":
            name = c.get("name", "?")
            args = c.get("arguments", {})
            args_short = json.dumps(args, indent=None, default=str)
            if len(args_short) > 120:
                args_short = args_short[:117] + "..."
            print(f"\n{ROLE_COLORS['tool']}{ts} [TOOL CALL]{RESET} {BOLD}{name}{RESET}({args_short})")

        elif ctype == "toolResult":
            name = c.get("name", c.get("toolCallId", "?"))
            result = c.get("text", c.get("content", ""))
            if isinstance(result, list):
                result = result[0].get("text", "") if result else ""
            if len(str(result)) > 200:
                result = str(result)[:197] + "..."
            print(f"  {DIM}→ {result}{RESET}")

    sys.stdout.flush()
