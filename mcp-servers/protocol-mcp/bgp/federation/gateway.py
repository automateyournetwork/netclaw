"""Run a local gateway agent turn for N2N delegated chat / skill execution.

OpenClaw's gateway (2026.6+) is WebSocket-only — it does NOT serve an
OpenAI-compatible `/v1/chat/completions` REST route. The correct way to run an
agent turn from outside the gateway is the CLI:

    openclaw agent --agent <id> --session-key <key> --json -m "<prompt>"

which returns a JSON envelope whose reply text is at result.payloads[*].text.
This module wraps that so the federation responder (chat.py, invocation.py) can
generate replies without assuming a REST endpoint that doesn't exist.
"""

import asyncio
import json
import logging
import os

logger = logging.getLogger("n2n.gateway")

AGENT_ID = os.environ.get("N2N_AGENT_ID", "main")


class EnforcementRefused(RuntimeError):
    """Raised when a production containment control is unavailable, so a member
    task fails closed rather than running unsandboxed/unguarded (feature 057)."""


async def _apply_production_controls(cmd: list, prompt: str) -> list:
    """In production, guard a member's model I/O through DefenseClaw, fail-closed.

    The member PROCESS itself is confined at the OS level by its systemd unit
    (feature 057 US2 = host-level kernel confinement: NoNewPrivileges, read-only
    system, hidden master secrets, and — on native Linux — syscall/namespace
    limits). So the confinement is applied at launch, not per model turn; here we
    only enforce the DefenseClaw model-guard (US3). Returns the command unchanged
    (confinement is out-of-band); raises EnforcementRefused if the guard is
    unavailable. No-op in testing mode."""
    from . import controls
    if not controls.is_production():
        return cmd

    # US3 (FR-007/009): model I/O guard. DefenseClaw guards model I/O via its
    # guardrail PROXY (the member's model provider routes through it); guarding is
    # not a per-call CLI command. Here we FAIL CLOSED if the proxy guard isn't
    # actually available — the member must not run its model turn unguarded. The
    # inspection itself happens in the proxy the member routes through.
    guard_ok, guard_detail = await controls.defenseclaw_available()
    if not guard_ok:
        raise EnforcementRefused(f"model-guard unavailable: {guard_detail}")
    return cmd


def _extract_reply(stdout: str):
    """Parse the `openclaw agent --json` envelope (which is preceded by banner
    noise) and return (reply_text, tokens_used)."""
    # US5/FR-018: use raw_decode so a trailing log line after the JSON envelope
    # (e.g. "[agent] run … stopReason=stop") does NOT break parsing — plain
    # json.loads(stdout[start:]) fails on trailing content. Try each '{' start
    # and raw_decode the first complete object there.
    decoder = json.JSONDecoder()
    start = stdout.find("{")
    obj = None
    while start != -1:
        try:
            obj, _ = decoder.raw_decode(stdout[start:])
            break
        except Exception:
            start = stdout.find("{", start + 1)
    if obj is None:
        # No JSON — return raw trailing text so the caller still gets something.
        return stdout.strip()[-2000:], 0

    # Reply text. OpenClaw builds differ: some put the clean answer in
    # finalAssistantVisibleText, others in result.payloads[*].text. Prefer the
    # visible-text field (recursively, since nesting varies), then fall back.
    def _find(o, keys):
        if isinstance(o, dict):
            for k in keys:
                v = o.get(k)
                if isinstance(v, str) and v.strip():
                    return v
            for v in o.values():
                r = _find(v, keys)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = _find(v, keys)
                if r:
                    return r
        return None

    reply = _find(obj, ("finalAssistantVisibleText", "finalAssistantRawText"))
    result = obj.get("result", obj)
    if not reply:
        # result.payloads[*].text (concatenated), skipping obvious tool-schema dumps
        texts = [p["text"] for p in (result.get("payloads") or [])
                 if isinstance(p, dict) and isinstance(p.get("text"), str)
                 and '"schemaHash"' not in p["text"]]
        reply = "\n".join(t for t in texts if t.strip())
    if not reply:
        for key in ("reply", "text", "message", "output", "response"):
            v = result.get(key)
            if isinstance(v, str) and v.strip():
                reply = v
                break

    # Best-effort token count
    tokens = 0
    try:
        usage = (result.get("meta") or {}).get("usage") or obj.get("usage") or {}
        tokens = usage.get("total_tokens") or usage.get("totalTokens") or 0
    except Exception:
        tokens = 0
    return reply or "(no reply text in agent response)", int(tokens or 0)


async def run_agent_turn(prompt: str, session_key: str = "n2n", timeout_s: int = 300,
                         local: bool = False, model: str = None,
                         untrusted: bool = False, on_stall=None,
                         stall_after_s: int = 120):
    """Run one agent turn. Returns (reply_text, tokens_used).

    Two modes:
      - gateway (default): `openclaw agent --agent <id> …` against the running
        gateway. Used by the Border / a standalone claw (eN2N responder).
      - embedded (local=True): `openclaw agent --local --model <model> …` — the
        agent runs in-process with the member's own provider API keys and ONLY
        the MCP servers in the member's config dir. This is how an iN2N MEMBER
        executes a delegated skill: no gateway, no comms, scoped tools, its own
        model/provider (feature 056). `model` is 'provider/model' or a model id.

    `untrusted` marks the prompt as carrying EXTERNAL (eN2N) peer input. An
    untrusted turn may NEVER run embedded outside verified production
    containment: embedded mode has no gateway scope-approval gate and no gateway
    session log, so for an external peer it is only acceptable inside the
    sandbox + model guard, both fail-closed (2026-07-14 delegation-bypass
    security review).

    `on_stall(waited_s)` (gateway mode only): called once if the turn produces
    no result within `stall_after_s` — the signature of the gateway holding the
    session at its scope-upgrade approval gate (the CLI stays silent while the
    gateway waits for the operator). It may return extra seconds to wait (e.g.
    the operator approval window) so an approval can land instead of the turn
    dying on a blind hard timeout.

    Raises TimeoutError on timeout; on non-zero exit returns the stderr tail as
    the reply so the caller can surface a useful message rather than crashing.
    """
    if local and untrusted:
        # Fail-closed eN2N gate: never run external-peer input embedded unless
        # the 057 production controls actually verify. This makes the one-line
        # `local=True` approval-gate bypass impossible to reintroduce silently.
        from . import controls
        if not controls.is_production():
            raise EnforcementRefused(
                "embedded (--local) execution refused for untrusted eN2N input "
                "outside production mode — use the gateway path (approval gate "
                "+ session logging)")
        sandbox_ok, sandbox_detail = await controls.sandbox_available()
        if not sandbox_ok:
            raise EnforcementRefused(
                f"embedded execution refused for untrusted eN2N input — "
                f"sandbox unavailable: {sandbox_detail}")
        # model-guard is enforced fail-closed by _apply_production_controls below

    # US4: use the flag our OWN CLI supports, probed once and cached in
    # negotiate.py (builds differ: --session-id vs --session-key). This is the
    # responder running its own agent, so the local probe is authoritative.
    from .negotiate import local_descriptor
    flag = "--" + local_descriptor().get("agent_invoke", "session-id")
    if local:
        cmd = ["openclaw", "agent", "--local"]
        if model:
            cmd += ["--model", model]
        cmd += [flag, session_key, "--json", "-m", prompt]
        # feature 057: in production a MEMBER executes INSIDE the OpenShell sandbox
        # (US2/FR-004/005) with its model I/O guarded by DefenseClaw (US3/FR-007/009).
        # Both fail closed — a member that cannot be sandboxed or guarded does NOT
        # run unprotected. Testing mode runs unwrapped (fast iteration, FR-006).
        cmd = await _apply_production_controls(cmd, prompt)
    else:
        cmd = ["openclaw", "agent", "--agent", AGENT_ID, flag, session_key, "--json", "-m", prompt]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    comm = asyncio.ensure_future(proc.communicate())
    # asyncio.wait (unlike wait_for) does NOT cancel `comm` on timeout, so the
    # turn keeps running across the stall checkpoint and any extension.
    remaining = float(timeout_s)
    if on_stall and not local and stall_after_s and stall_after_s < remaining:
        done, _ = await asyncio.wait({comm}, timeout=stall_after_s)
        remaining -= stall_after_s
        if not done:
            # Silent this long usually means the gateway is holding the session
            # at its scope-upgrade approval gate. Surface it to the operator and
            # let the caller extend the window so the approval can land.
            try:
                remaining += max(0, int(on_stall(stall_after_s) or 0))
            except Exception as e:
                logger.warning("on_stall notifier failed: %s", e)
    if not comm.done():
        await asyncio.wait({comm}, timeout=remaining)
    if not comm.done():
        try:
            proc.kill()
        except Exception:
            pass
        comm.cancel()
        raise asyncio.TimeoutError(
            f"agent turn for session '{session_key}' timed out — if the gateway "
            f"is holding a scope-upgrade approval, approve it and retry")
    out, _ = await comm
    stdout = out.decode(errors="replace") if out else ""
    if proc.returncode != 0:
        logger.warning("openclaw agent exited %s", proc.returncode)
    return _extract_reply(stdout)
