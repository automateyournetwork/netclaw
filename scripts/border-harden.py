#!/usr/bin/env python3
"""Opt-in OpenClaw Border hardening (spec 165, T002).

Feature 057 confines iN2N *members*; the Border itself is an ordinary OpenClaw
gateway. Spec 164 T005 showed a Border with host exec/read reaching Convergence
secrets, while OpenClaw's Docker sandbox contained the same attempt. This helper
applies that containment to a Border, through the OpenClaw CLI only:

  agents.defaults.sandbox.mode             = "all"      (every session sandboxed)
  agents.defaults.sandbox.backend          = "docker"
  agents.defaults.sandbox.scope            = "session"
  agents.defaults.sandbox.workspaceAccess  = "none"
  agents.defaults.sandbox.docker.network   = "none"     (other docker keys kept)
  tools.elevated.enabled                   = false      (other elevated keys kept)
  tools.sandbox.tools.alsoAllow           += "bundle-mcp" (existing entries kept;
        merged into tools.sandbox.tools.allow instead when that list is set,
        because OpenClaw rejects allow + alsoAllow in one scope)
  skills.workshop.autonomous.mode          = "off"      (no autonomous learning)

Every change is a leaf assignment, so sibling keys the operator set (for example
agents.defaults.sandbox.docker.image or docker.env) are never rewritten. Current
values are read with `openclaw config get <path> --json` (redacted by OpenClaw);
only the non-secret paths listed above are read or printed.

It is NOT a global default: with no network and no workspace, skills that run
host scripts or need host network run inside the sandbox and can fail.

Usage:
  python3 scripts/border-harden.py              # dry run (default): plan + OpenClaw dry-run
  python3 scripts/border-harden.py --apply      # dry-run, write, then `openclaw config validate`
  python3 scripts/border-harden.py --apply --skip-image-check

Exit codes: 0 success; 1 OpenClaw rejected the change (dry-run, set or validate);
2 preflight failure (openclaw missing, unknown config path, Docker unreachable,
sandbox image missing). Never builds images, restarts services or uses sudo.
"""

import argparse
import grp
import json
import os
import shutil
import subprocess
import sys
import tempfile

DEFAULT_IMAGE = "openclaw-sandbox:bookworm-slim"
BUNDLE_MCP = "bundle-mcp"
OPENCLAW_TIMEOUT = 180
DOCKER_TIMEOUT = 30

SANDBOX_LEAVES = (
    ("mode", "all"),
    ("backend", "docker"),
    ("scope", "session"),
    ("workspaceAccess", "none"),
)

BUILD_INSTRUCTION = f"""\
  OpenClaw's documented build for the default image (npm install; from a source
  checkout use scripts/sandbox-setup.sh instead):

    docker build -t {DEFAULT_IMAGE} - <<'DOCKERFILE'
    FROM debian:bookworm-slim
    ENV DEBIAN_FRONTEND=noninteractive
    RUN apt-get update && apt-get install -y --no-install-recommends \\
      bash ca-certificates curl git jq python3 ripgrep \\
      && rm -rf /var/lib/apt/lists/*
    RUN useradd --create-home --shell /bin/bash sandbox
    USER sandbox
    WORKDIR /home/sandbox
    CMD ["sleep", "infinity"]
    DOCKERFILE

  See OpenClaw docs: gateway/sandboxing/images-and-setup."""


class Preflight(Exception):
    """A condition that blocks hardening (exit 2)."""


def _run(argv, timeout):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, check=False)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", f"timed out after {timeout}s")
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def _envelope_message(text):
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return ""
    if isinstance(data, dict) and data.get("ok") is False:
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or "")
        return str(err or "")
    return ""


_UNSET = object()


def config_get(openclaw, path):
    """Return the authored value at `path`, or _UNSET when OpenClaw reports it unset."""
    proc = _run([openclaw, "config", "get", path, "--json"], OPENCLAW_TIMEOUT)
    if proc.returncode == 0:
        try:
            return json.loads(proc.stdout)
        except ValueError as exc:
            raise Preflight(f"could not parse `openclaw config get {path} --json` output") from exc
    message = _envelope_message(proc.stdout) or proc.stderr.strip()
    lowered = message.lower()
    if "valid but unset" in lowered:
        return _UNSET
    if "unknown config path" in lowered:
        raise Preflight(f"this OpenClaw does not know `{path}` ({message}). Border hardening "
                        "needs an OpenClaw release with that setting; upgrade OpenClaw first.")
    raise Preflight(f"`openclaw config get {path} --json` failed (exit {proc.returncode}): "
                    f"{message or 'no output'}")


def read_current(openclaw):
    """Read only the non-secret paths this helper changes or inspects."""
    def obj(path):
        value = config_get(openclaw, path)
        return value if isinstance(value, dict) else {}

    sandbox = obj("agents.defaults.sandbox")
    docker = sandbox.get("docker") if isinstance(sandbox.get("docker"), dict) else {}
    elevated = obj("tools.elevated")
    sandbox_tools = obj("tools.sandbox.tools")
    workshop = config_get(openclaw, "skills.workshop.autonomous.mode")
    return {
        "sandbox": {key: sandbox.get(key, _UNSET) for key, _ in SANDBOX_LEAVES},
        "docker_network": docker.get("network", _UNSET),
        "docker_image": docker.get("image", _UNSET),
        "elevated_enabled": elevated.get("enabled", _UNSET),
        "allow": sandbox_tools.get("allow", _UNSET),
        "also_allow": sandbox_tools.get("alsoAllow", _UNSET),
        "workshop_mode": workshop,
    }


def _merged_list(existing):
    items = list(existing) if isinstance(existing, list) else []
    merged = []
    for item in items + [BUNDLE_MCP]:
        if item not in merged:
            merged.append(item)
    return merged


def build_plan(current):
    """Return [(path, before, after)] leaf assignments (before may be _UNSET)."""
    plan = []
    for key, value in SANDBOX_LEAVES:
        plan.append((f"agents.defaults.sandbox.{key}", current["sandbox"][key], value))
    plan.append(("agents.defaults.sandbox.docker.network", current["docker_network"], "none"))
    plan.append(("tools.elevated.enabled", current["elevated_enabled"], False))
    allow = current["allow"]
    if isinstance(allow, list) and allow:
        # OpenClaw rejects a sandbox tool scope with both allow and alsoAllow.
        plan.append(("tools.sandbox.tools.allow", allow, _merged_list(allow)))
    else:
        plan.append(("tools.sandbox.tools.alsoAllow", current["also_allow"],
                     _merged_list(current["also_allow"])))
    plan.append(("skills.workshop.autonomous.mode", current["workshop_mode"], "off"))
    return plan


def _show(value):
    return "(unset)" if value is _UNSET else json.dumps(value)


def print_plan(plan):
    print("Planned OpenClaw changes (leaf assignments; sibling keys are kept):")
    for path, before, after in plan:
        marker = "  " if before == after else "* "
        print(f"  {marker}{path}: {_show(before)} -> {json.dumps(after)}")


def write_batch(plan):
    """Write the batch to a 0600 file inside a fresh 0700 temp dir; return (dir, file)."""
    directory = tempfile.mkdtemp(prefix="netclaw-border-harden-")
    os.chmod(directory, 0o700)
    path = os.path.join(directory, "border-harden.batch.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump([{"path": p, "value": after} for p, _, after in plan], handle, indent=2)
        handle.write("\n")
    return directory, path


def _docker_permission_help():
    lines = [
        "  The current user cannot talk to the Docker daemon (permission denied on the socket).",
        "  OpenClaw's Docker sandbox runs as this user, so it needs Docker access:",
    ]
    try:
        group = grp.getgrnam("docker")
    except KeyError:
        group = None
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    listed = bool(group and user and user in group.gr_mem)
    active = bool(group and group.gr_gid in os.getgroups())
    if listed and not active:
        lines.append(f"  - `{user}` is in the docker group, but this session predates it (stale groups).")
    else:
        lines.append("  - add the user to the docker group: sudo usermod -aG docker \"$USER\"")
    lines += [
        "  - then pick up the new group: log out and back in, or restart the user manager",
        "    (a systemd --user manager started before the group change keeps stale groups,",
        "    so a gateway running as a user service will not see it):",
        "        sudo systemctl restart user@$(id -u)",
        "  This helper never runs sudo itself.",
    ]
    return "\n".join(lines)


def check_docker(image, skip_image_check):
    """Return a list of blocker messages (empty when Docker is ready)."""
    docker = shutil.which("docker")
    if not docker:
        return ["Docker is not on PATH. Install Docker (OpenClaw's sandbox backend) first."]
    info = _run([docker, "info"], DOCKER_TIMEOUT)
    if info.returncode != 0:
        text = f"{info.stdout}\n{info.stderr}".lower()
        if "permission denied" in text:
            return ["`docker info` failed: permission denied.\n" + _docker_permission_help()]
        detail = (info.stderr or info.stdout).strip().splitlines()
        last = detail[-1] if detail else "no output"
        return [f"`docker info` failed (exit {info.returncode}): {last}. Start Docker and retry."]
    if skip_image_check:
        print(f"Sandbox image check skipped (--skip-image-check); configured image: {image}")
        return []
    inspect = _run([docker, "image", "inspect", image], DOCKER_TIMEOUT)
    if inspect.returncode != 0:
        message = f"Sandbox image `{image}` is not present locally."
        if image == DEFAULT_IMAGE:
            message += "\n" + BUILD_INSTRUCTION
        else:
            message += " Build or pull the image you configured in agents.defaults.sandbox.docker.image."
        message += "\n  This helper never builds images. Re-run after building, or pass --skip-image-check."
        return [message]
    print(f"Sandbox image present: {image}")
    return []


def _relay(proc, label):
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    print(f"{label} (exit {proc.returncode}):")
    for text in (out, err):
        for line in text.splitlines():
            print(f"  {line}")


def next_steps(agent):
    print(f"""
Next steps:
  - OpenClaw reports above whether the gateway hot-reloads the change; if it says a
    restart is needed, restart the Border gateway yourself. Running sandbox runtimes
    keep old settings until recreated: openclaw sandbox recreate --all
  - Verify the effective policy (per-agent overrides in agents.list can still opt out):
        openclaw sandbox explain --agent {agent}
  - WARNING: every Border session now runs in a Docker sandbox with no network and no
    workspace access. Skills that run host scripts, read host files or need host
    network (for example local collectors or CLI wrappers) run inside the sandbox and
    may fail. MCP tools stay available through the bundle-mcp sandbox allowance.
  - Skill Workshop autonomous learning is off; re-enable deliberately with
        openclaw config set skills.workshop.autonomous.mode auto""")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Opt-in OpenClaw Border hardening (spec 165).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="show the plan and OpenClaw's dry-run result without writing (default)")
    mode.add_argument("--apply", action="store_true",
                      help="validate with OpenClaw, write the change, then run `openclaw config validate`")
    parser.add_argument("--skip-image-check", action="store_true",
                        help="do not require the sandbox image to exist locally")
    parser.add_argument("--agent", default="main",
                        help="agent id used in the verification hint (default: main)")
    args = parser.parse_args(argv)

    openclaw = shutil.which("openclaw")
    if not openclaw:
        print("ERROR: `openclaw` is not on PATH.", file=sys.stderr)
        return 2

    try:
        current = read_current(openclaw)
    except Preflight as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    image = current["docker_image"]
    image = image if isinstance(image, str) and image else DEFAULT_IMAGE
    blockers = check_docker(image, args.skip_image_check)
    for blocker in blockers:
        print(f"PREFLIGHT: {blocker}", file=sys.stderr)

    plan = build_plan(current)
    print_plan(plan)

    directory, batch = write_batch(plan)
    try:
        dry = _run([openclaw, "config", "set", "--batch-file", batch, "--dry-run"], OPENCLAW_TIMEOUT)
        _relay(dry, "OpenClaw dry-run")
        if dry.returncode != 0:
            print("ERROR: OpenClaw rejected the change; nothing was written.", file=sys.stderr)
            return 1
        if not args.apply:
            if blockers:
                print("Dry run only. --apply would be refused until the preflight issues above are fixed.")
                return 2
            print("Dry run only; nothing was written. Re-run with --apply to write.")
            return 0
        if blockers:
            print("ERROR: refusing --apply until the preflight issues above are fixed.", file=sys.stderr)
            return 2
        applied = _run([openclaw, "config", "set", "--batch-file", batch], OPENCLAW_TIMEOUT)
        _relay(applied, "OpenClaw config set")
        if applied.returncode != 0:
            print("ERROR: `openclaw config set` failed.", file=sys.stderr)
            return 1
    finally:
        shutil.rmtree(directory, ignore_errors=True)

    validated = _run([openclaw, "config", "validate"], OPENCLAW_TIMEOUT)
    _relay(validated, "OpenClaw config validate")
    if validated.returncode != 0:
        print("ERROR: the written config does not validate. The previous values are listed in "
              "the plan above; restore them with `openclaw config set` and re-check.", file=sys.stderr)
        return 1
    next_steps(args.agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
