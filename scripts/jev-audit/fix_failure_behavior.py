"""
Mechanical fix for the 123 skills sweep 1 flagged as having no specified
failure behavior. Appends a short, tailored "## Failure Behavior" section
(env vars actually required by that skill, and whether it has write-capable
tools) rather than one generic paragraph pasted 123 times verbatim.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "workspace" / "skills"
TARGETS_PATH = Path(__file__).resolve().parent / "data" / "fix_targets.json"

ENV_REF_PATTERN = re.compile(r"\$([A-Z][A-Z0-9_]*(?:_MCP_[A-Z0-9_]+|_SCRIPT|_URL|_HOST|_TOKEN|_KEY|_USERNAME|_PASSWORD))")
METADATA_ENV_PATTERN = re.compile(r'"env"\s*:\s*\[([^\]]*)\]')
BACKTICK_IDENTIFIER_PATTERN = re.compile(r"`([a-z][a-z0-9_]*)`")
WRITE_VERB_PREFIXES = (
    "create_", "update_", "delete_", "remove_", "deploy_", "set_", "enable_", "disable_",
    "restart_", "reboot_", "rollback_", "push_", "apply_", "write_", "add_", "modify_",
    "override_", "isolate_", "quarantine_", "send_", "post_", "reset_", "escalate_",
    "resolve_", "acknowledge_", "trigger_", "kill_", "reconfigure_",
    # "start_"/"stop_" deliberately excluded: collide with common parameter names
    # (start_time, end_time) far more often than with genuine mutating tool names.
)
READ_ONLY_OVERRIDE = {
    # topolograph-igp-analysis documents its own write tools (add_lsp/update_lsp/
    # delete_lsp) as explicitly blocked (TOPOLOGRAPH_MCP_READ_ONLY=true, defenseclaw
    # tool block) — the verb-prefix heuristic can't see "but these are disabled".
    "topolograph-igp-analysis",
}
ALREADY_HAS_SECTION = re.compile(r"^##\s*Failure Behavior", re.MULTILINE | re.IGNORECASE)


def extract_env_vars(content: str) -> list[str]:
    names = set(ENV_REF_PATTERN.findall(content))
    m = METADATA_ENV_PATTERN.search(content)
    if m:
        for item in re.findall(r'"([A-Za-z0-9_]+)"', m.group(1)):
            names.add(item)
    return sorted(names)


def has_write_tools(content: str, name: str = "") -> bool:
    if name in READ_ONLY_OVERRIDE:
        return False
    if re.search(r"requires write", content, re.IGNORECASE):
        return True
    # Only trust backtick-quoted tool-name-shaped identifiers (e.g. `create_schedule`),
    # not prose — an earlier version matched substrings like "deployment"/"apply" in
    # ordinary sentences and misclassified read-only skills as write-capable.
    for identifier in BACKTICK_IDENTIFIER_PATTERN.findall(content):
        if identifier.startswith(WRITE_VERB_PREFIXES):
            return True
    return False


def build_section(env_vars: list[str], writes: bool) -> str:
    lines = ["## Failure Behavior", ""]
    if env_vars:
        env_list = ", ".join(f"`{v}`" for v in env_vars)
        verb = "is" if len(env_vars) == 1 else "are"
        lines.append(
            f"- If a tool call fails with an authentication or connection error, check that "
            f"{env_list} {verb} set and valid before assuming a data or device problem."
        )
    lines.append(
        "- On a tool error (timeout, unreachable host, malformed response), report the failure "
        "and its error message directly to the user rather than fabricating or guessing at results."
    )
    if writes:
        lines.append(
            "- Do not automatically retry a write/mutating operation after a failure — surface the "
            "error and get explicit confirmation before retrying, since a blind retry on a "
            "partially-applied change can leave state inconsistent."
        )
    else:
        lines.append(
            "- All tools here are read-only, so a failed call has no side effects — it's safe to "
            "retry once after confirming connectivity, but don't loop indefinitely on repeated failures."
        )
    return "\n".join(lines) + "\n"


def main():
    targets = json.loads(TARGETS_PATH.read_text())["no_failure"]
    changed, skipped = [], []
    for name in targets:
        skill_file = SKILLS_DIR / name / "SKILL.md"
        if not skill_file.is_file():
            skipped.append((name, "file not found"))
            continue
        content = skill_file.read_text(encoding="utf-8", errors="replace")
        if ALREADY_HAS_SECTION.search(content):
            skipped.append((name, "already has a Failure Behavior section"))
            continue
        env_vars = extract_env_vars(content)
        writes = has_write_tools(content, name)
        section = build_section(env_vars, writes)
        new_content = content.rstrip("\n") + "\n\n" + section
        skill_file.write_text(new_content, encoding="utf-8")
        changed.append(name)
    print(f"changed: {len(changed)}")
    print(f"skipped: {len(skipped)}")
    for name, reason in skipped:
        print(f"  skipped {name}: {reason}")


if __name__ == "__main__":
    main()
