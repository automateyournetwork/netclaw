"""Run a local gateway agent turn for N2N delegated chat / skill execution.

OpenClaw's gateway (2026.6+) is WebSocket-only — it does NOT serve an
OpenAI-compatible `/v1/chat/completions` REST route. The gateway (default,
non-embedded) dispatch path in this module talks to the gateway's `agent` RPC
method over a persistent WebSocket connection (see gateway_ws.py), the same
way OpenClaw's own internal `sessions_send` tool does.

Spec 116: this module used to shell out to the `openclaw agent --json` CLI for
every single turn. That CLI's own gateway-dispatch code unconditionally sets
`cleanupBundleMcpOnRunEnd: true`, which tears down the gateway's
session-scoped MCP tool runtime after every turn — a measured ~27s fixed cost
on every single turn, every channel, with zero reuse even within one session
(specs/116-border-turn-latency/research.md). The WS RPC path never sends that
flag, so the gateway's own runtime cache is finally allowed to do its job.

The reply envelope shape (`result.payloads[*].text`) is identical whether it
arrives via CLI stdout or a WS response payload — `_extract_reply` (CLI) and
`_extract_reply_from_ws_payload` (WS) share the same parsing core.

The embedded (`local=True`) path is unchanged by spec 116: it still shells out
to `openclaw agent --local ...` directly (feature 056 — an iN2N MEMBER runs
in-process with its own provider keys and no gateway at all, so there is no
gateway RPC to dispatch through).
"""

import asyncio
import glob
import json
import logging
import os
import re
import shutil
import tempfile
import uuid

from . import gateway_ws

logger = logging.getLogger("n2n.gateway")

AGENT_ID = os.environ.get("N2N_AGENT_ID", "main")


def _openclaw_bin() -> str:
    """Absolute path to the ``openclaw`` CLI (resolved fresh on each call — cheap
    next to spawning the process, and robust to PATH changes over the daemon's
    lifetime).

    A ``systemd --user`` service does not source the shell rc, so an
    nvm-managed openclaw/node -- the common install -- is NOT on the service
    PATH even though it is in an interactive shell (nvm edits PATH only per
    interactive shell). The confined mesh/member units (feature 057) therefore
    could not find ``openclaw`` and every delegated agent turn failed with
    ENOENT. Resolve it explicitly: an OPENCLAW_BIN override, then whatever is on
    PATH, then the newest nvm node that ships it, then common prefixes."""
    cand = os.environ.get("OPENCLAW_BIN")
    if cand and os.path.exists(cand):
        return cand
    cand = shutil.which("openclaw")
    if cand:
        return cand

    def _ver(p):
        m = re.search(r"/v(\d+)\.(\d+)\.(\d+)/", p)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
    nvm = sorted(glob.glob(os.path.expanduser(
        "~/.nvm/versions/node/*/bin/openclaw")), key=_ver, reverse=True)
    cand = next((p for p in nvm if os.path.exists(p)), None)
    if cand:
        return cand
    for p in ("~/.local/bin/openclaw", "/usr/local/bin/openclaw"):
        p = os.path.expanduser(p)
        if os.path.exists(p):
            return p
    logger.warning("openclaw CLI not found via OPENCLAW_BIN, PATH, nvm, or "
                   "common prefixes — agent turns will fail; set OPENCLAW_BIN")
    return "openclaw"


def _agent_env() -> dict:
    """Child environment that can launch openclaw under a confined systemd PATH:
    prepend the directory holding openclaw so its ``#!/usr/bin/env node`` shebang
    (node lives beside it in the nvm bin) resolves too."""
    env = dict(os.environ)
    b = _openclaw_bin()
    if os.sep in b:
        env["PATH"] = os.path.dirname(os.path.abspath(b)) + os.pathsep + env.get("PATH", "")
    return env


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
    if "--model" in cmd:
        index = cmd.index("--model")
        override = cmd[index + 1] if index + 1 < len(cmd) else ""
        route_ok, detail = controls.guarded_model_route(override)
        if not route_ok:
            raise EnforcementRefused(f"model-guard unavailable: {detail}")
    return cmd


def _find_reply_text(o, keys):
    """Recursively search a JSON-like structure for the first string value
    under any of `keys`. Shared by both the CLI-stdout and WS-payload reply
    extraction paths (spec 116: both parse the same underlying envelope
    shape, just delivered over a different transport)."""
    if isinstance(o, dict):
        for k in keys:
            v = o.get(k)
            if isinstance(v, str) and v.strip():
                return v
        for v in o.values():
            r = _find_reply_text(v, keys)
            if r:
                return r
    elif isinstance(o, list):
        for v in o:
            r = _find_reply_text(v, keys)
            if r:
                return r
    return None


def _extract_one_envelope(obj):
    reply = _find_reply_text(obj, ("finalAssistantVisibleText", "finalAssistantRawText"))
    result = obj.get("result", obj) if isinstance(obj, dict) else {}
    if not reply and isinstance(result, dict):
        # result.payloads[*].text (concatenated), skipping obvious tool-schema dumps
        texts = [p["text"] for p in (result.get("payloads") or [])
                 if isinstance(p, dict) and isinstance(p.get("text"), str)
                 and '"schemaHash"' not in p["text"]]
        reply = "\n".join(t for t in texts if t.strip())
    return reply, result


def _extract_reply_from_envelopes(objs: list):
    """Given a list of candidate JSON envelope objects (newest-last), find the
    best reply text and token count. Shared core of `_extract_reply` (CLI
    stdout) and `_extract_reply_from_ws_payload` (WS RPC response) — both
    transports carry the identical envelope shape (spec 116,
    contracts/gateway-ws-rpc.md: "the underlying result shape is the same
    result.payloads structure whether it arrives via CLI stdout or WS
    response payload")."""
    if not objs:
        return None, 0

    # The agent envelope is normally the LAST object; scan newest-first and take
    # the first object that yields real reply text, so plugin JSON noise earlier
    # in the stream can never masquerade as the agent's answer.
    obj, reply, result = objs[-1], None, {}
    for cand in reversed(objs):
        r, res = _extract_one_envelope(cand)
        if r:
            obj, reply, result = cand, r, res
            break
    if not reply:
        obj = objs[-1]
        result = obj.get("result", obj) if isinstance(obj, dict) else {}
        if isinstance(result, dict):
            for key in ("reply", "text", "message", "output", "response"):
                v = result.get(key)
                if isinstance(v, str) and v.strip():
                    reply = v
                    break

    # Best-effort token count
    tokens = 0
    try:
        meta = result.get("meta") or {}
        usage = meta.get("usage") or (meta.get("agentMeta") or {}).get("usage") or obj.get("usage") or {}
        tokens = usage.get("total_tokens") or usage.get("totalTokens") or usage.get("total") or 0
    except Exception:
        tokens = 0
    return reply, int(tokens or 0)


def _extract_reply(stdout: str):
    """Parse the `openclaw agent --json` envelope (which is preceded by banner
    noise) and return (reply_text, tokens_used). Still used by the `local=True`
    embedded dispatch path, which continues to shell out to the CLI."""
    # US5/FR-018: use raw_decode so a trailing log line after the JSON envelope
    # (e.g. "[agent] run … stopReason=stop") does NOT break parsing — plain
    # json.loads(stdout[start:]) fails on trailing content. Collect EVERY
    # complete object in the stream: plugins (e.g. DefenseClaw 0.8.x's fetch
    # interceptor) emit their own JSON lines BEFORE the agent envelope, so the
    # first object is no longer guaranteed to be the reply.
    decoder = json.JSONDecoder()
    objs = []
    start = stdout.find("{")
    while start != -1:
        try:
            obj, consumed = decoder.raw_decode(stdout[start:])
            objs.append(obj)
            start = stdout.find("{", start + max(consumed, 1))
        except Exception:
            start = stdout.find("{", start + 1)
    if not objs:
        raise RuntimeError("Agent returned no valid JSON result; task result unavailable")

    reply, tokens = _extract_reply_from_envelopes(objs)
    if not reply:
        raise RuntimeError("Agent returned no reply text; task result unavailable")
    return reply, tokens


def _extract_reply_from_ws_payload(payload: dict):
    """Parse a gateway WS RPC `agent` response payload and return
    (reply_text, tokens_used). No banner-noise problem exists on this path
    (the payload is already structured JSON, not subprocess stdout), so this
    wraps the single payload as a one-element envelope list and reuses the
    exact same extraction core `_extract_reply` uses (spec 116,
    contracts/run-agent-turn.md: "Reused unchanged")."""
    reply, tokens = _extract_reply_from_envelopes([payload] if isinstance(payload, dict) else [])
    if not reply:
        raise RuntimeError("Agent returned no reply text; task result unavailable")
    return reply, tokens


_RECOGNIZED_ORIGINS = {"voice"}

_VOICE_COMPOSITION_INSTRUCTION = (
    "Answer in one or two short, plain spoken sentences. No headers, bullet "
    "lists, or emphasis markup. If the full answer cannot fit, summarise "
    "honestly rather than truncate."
)


def _normalize_origin(origin: str | None) -> str | None:
    """FR-012: an unrecognized origin value is treated as though none were
    supplied, and must never cause the request to fail."""
    return origin if origin in _RECOGNIZED_ORIGINS else None


def _build_agent_rpc_params(prompt: str, session_key: str, timeout_s: int,
                             origin: str | None = None) -> dict:
    """Build the gateway `agent` RPC params per
    specs/116-border-turn-latency/contracts/gateway-ws-rpc.md.

    Deliberately does NOT include `cleanupBundleMcpOnRunEnd` — its absence is
    the entire fix (research.md Findings 2/3): OpenClaw's own internal
    `sessions_send`/`runAgentStep` calls this same RPC method the same way and
    also omits it, letting the gateway's session-scoped MCP runtime cache
    survive across turns instead of being torn down after every one.

    Also deliberately does NOT set `inputProvenance` for voice origin: the
    gateway's `normalizeInputProvenance` (confirmed by reading its bundled
    source, input-provenance-CQSqbDss.js) validates `.kind` against a fixed
    enum (`external_user`/`inter_session`/`internal_system`) and silently
    drops anything else — an ad-hoc `{"origin": "voice"}` shape is not a
    recognized extension point and would be inert. `extraSystemPrompt` alone
    is the real, gateway-accepted mechanism that drives FR-010's composition
    change; origin retention for FR-013 is handled by the caller recording
    `origin` itself, not by round-tripping it through the gateway.
    """
    params = {
        "message": prompt,
        "agentId": AGENT_ID,
        "sessionKey": session_key,
        "deliver": False,
        "timeout": timeout_s,
        "idempotencyKey": str(uuid.uuid4()),
    }
    normalized_origin = _normalize_origin(origin)
    if normalized_origin == "voice":
        # FR-010/FR-011/FR-011a: brevity by composition instruction, never by
        # post-hoc truncation.
        params["extraSystemPrompt"] = _VOICE_COMPOSITION_INSTRUCTION
    return params


async def run_agent_turn(prompt: str, session_key: str = "n2n", timeout_s: int = 300,
                         local: bool = False, model: str = None,
                         untrusted: bool = False, on_stall=None,
                         stall_after_s: int = 120, message_file: str = None,
                         origin: str | None = None, execution=None):
    """Run one agent turn. Returns (reply_text, tokens_used).

    Two modes:
      - gateway (default): a persistent WebSocket JSON-RPC connection to the
        running gateway's `agent` method (spec 116 — previously an `openclaw
        agent --agent <id> …` CLI subprocess per turn; see gateway_ws.py's
        module docstring and specs/116-border-turn-latency/research.md for
        why that was replaced: the CLI path forced a ~27s full MCP-tool-set
        rebuild on every single turn). Used by the Border / a standalone claw
        (eN2N responder).
      - embedded (local=True): `openclaw agent --local --model <model> …` — the
        agent runs in-process with the member's own provider API keys and ONLY
        the MCP servers in the member's config dir. This is how an iN2N MEMBER
        executes a delegated skill: no gateway, no comms, scoped tools, its own
        model/provider (feature 056). `model` is 'provider/model' or a model id.
        UNCHANGED by spec 116 — still dispatches via CLI subprocess.

    `untrusted` marks the prompt as carrying EXTERNAL (eN2N) peer input. An
    untrusted turn may NEVER run embedded outside verified production
    containment: embedded mode has no gateway scope-approval gate and no gateway
    session log, so for an external peer it is only acceptable inside the
    sandbox + model guard, both fail-closed (2026-07-14 delegation-bypass
    security review).

    `on_stall(waited_s)` (gateway mode only): called once if the turn produces
    no result within `stall_after_s` — the signature of the gateway holding the
    session at its scope-upgrade approval gate. It may return extra seconds to
    wait (e.g. the operator approval window) so an approval can land instead of
    the turn dying on a blind hard timeout.

    Raises TimeoutError on timeout.

    `message_file` (feature 068): when set, the message body is read from this
    path instead of using `prompt` directly. In embedded (CLI) mode this
    avoids Linux ARG_MAX on a large capture attachment (research 068-D3); in
    gateway (WS) mode there is no ARG_MAX constraint, but the file is still
    read and its content used as the message body, for parity. `prompt` is
    still required and is what `_apply_production_controls` inspects (embedded
    mode only); the file's content is expected to match it.

    `origin` (spec 116, FR-007): optional marker for where the request
    originated (currently only `"voice"` is recognized). Default `None` is
    fully backward compatible (FR-008) — every existing caller that does not
    pass this argument sees identical behavior to before spec 116. An
    unrecognized value is normalized to `None` rather than failing the request
    (FR-012). Gateway (WS) mode only; the embedded path does not use it.
    """
    from .runtime import selected
    if selected().kind == 'hermes':
        if message_file or model: # selected Hermes config is the qualified model binding
            if message_file:raise RuntimeError('capability_unsupported: file ingress is not qualified for Hermes federation')
        from .hermes_runtime import run_turn
        return await run_turn(prompt,execution)
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

    if local:
        # US4: use the flag our OWN CLI supports, probed once and cached in
        # negotiate.py (builds differ: --session-id vs --session-key). This is
        # the responder running its own agent, so the local probe is
        # authoritative. Only needed on the CLI-subprocess (embedded) path.
        from .negotiate import local_descriptor
        flag = "--" + local_descriptor().get("agent_invoke", "session-id")
        message_args = ["--message-file", message_file] if message_file else ["-m", prompt]
        cmd = [_openclaw_bin(), "agent", "--local"]
        if model:
            cmd += ["--model", model]
        cmd += [flag, session_key, "--json"] + message_args
        # feature 057: in production a MEMBER executes INSIDE the OpenShell sandbox
        # (US2/FR-004/005) with its model I/O guarded by DefenseClaw (US3/FR-007/009).
        # Both fail closed — a member that cannot be sandboxed or guarded does NOT
        # run unprotected. Testing mode runs unwrapped (fast iteration, FR-006).
        cmd = await _apply_production_controls(cmd, prompt)
        # Keep JSON separate from plugin diagnostics. A large Node stdout write
        # to a pipe can also be truncated by an explicit process exit; regular
        # files are synchronous on POSIX. Anonymous private files retain neither
        # prompts nor credentials after the turn and avoid pipe backpressure.
        with tempfile.TemporaryFile() as output_file, tempfile.TemporaryFile() as error_file:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=output_file, stderr=error_file, env=_agent_env())
            try:
                await asyncio.wait_for(proc.wait(), timeout=float(timeout_s))
            except BaseException:
                if proc.returncode is None:
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                await proc.wait()
                raise
            if proc.returncode != 0:
                raise RuntimeError(f"Agent process exited {proc.returncode}; task result unavailable")
            output_file.seek(0)
            out = output_file.read(16 * 1024 * 1024 + 1)
            if len(out) > 16 * 1024 * 1024:
                raise RuntimeError("Agent result exceeded 16 MiB; task result unavailable")
            stdout = out.decode(errors="replace")
        return _extract_reply(stdout)

    # Gateway (default) path: persistent WS RPC, no per-turn subprocess, no
    # forced MCP-runtime teardown (spec 116 fix).
    effective_prompt = prompt
    if message_file:
        with open(message_file, "r", encoding="utf-8") as f:
            effective_prompt = f.read()

    client = await gateway_ws.get_gateway_ws_client()
    params = _build_agent_rpc_params(effective_prompt, session_key, timeout_s, origin=origin)
    normalized_origin = _normalize_origin(origin)
    if normalized_origin:
        # FR-013: retain origin for after-the-fact inspection. gateway.py has
        # no turn/session log store of its own (that lives with the callers --
        # chat.py, invocation.py); the logger is the record this function
        # itself controls, so an operator can grep for how a given session_key
        # reached NetClaw.
        logger.info("agent turn origin=%s session_key=%s", normalized_origin, session_key)
    call_future = asyncio.ensure_future(client.call("agent", params, None))
    try:
        remaining = float(timeout_s)
        if on_stall and stall_after_s and stall_after_s < remaining:
            done, _ = await asyncio.wait({call_future}, timeout=stall_after_s)
            remaining -= stall_after_s
            if not done:
                # Silent this long usually means the gateway is holding the session
                # at its scope-upgrade approval gate. Surface it to the operator and
                # let the caller extend the window so the approval can land.
                try:
                    remaining += max(0, int(on_stall(stall_after_s) or 0))
                except Exception as e:
                    logger.warning("on_stall notifier failed: %s", e)
        if not call_future.done():
            await asyncio.wait({call_future}, timeout=remaining)
        if not call_future.done():
            call_future.cancel()
            raise asyncio.TimeoutError(
                f"agent turn for session '{session_key}' timed out — if the gateway "
                f"is holding a scope-upgrade approval, approve it and retry")
        payload = await call_future
        return _extract_reply_from_ws_payload(payload)
    finally:
        if not call_future.done():
            call_future.cancel()
        # Consume cancellation/result so no pending RPC survives caller timeout
        # or cancellation. The remote execution budget remains params['timeout'].
        await asyncio.gather(call_future, return_exceptions=True)
