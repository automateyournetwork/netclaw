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


async def run_agent_turn(prompt: str, session_key: str = "n2n", timeout_s: int = 300):
    """Run one gateway agent turn. Returns (reply_text, tokens_used).

    Raises TimeoutError on timeout; on non-zero exit returns the stderr tail as
    the reply so the caller can surface a useful message rather than crashing.
    """
    # US4: use the flag our OWN CLI supports, probed once and cached in
    # negotiate.py (builds differ: --session-id vs --session-key). This is the
    # responder running its own agent, so the local probe is authoritative.
    from .negotiate import local_descriptor
    flag = "--" + local_descriptor().get("agent_invoke", "session-id")
    cmd = ["openclaw", "agent", "--agent", AGENT_ID, flag, session_key, "--json", "-m", prompt]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    stdout = out.decode(errors="replace") if out else ""
    if proc.returncode != 0:
        logger.warning("openclaw agent exited %s", proc.returncode)
    return _extract_reply(stdout)
