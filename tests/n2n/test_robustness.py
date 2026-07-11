"""T026-T028 (US5): robustness regression tests.

Consolidate the 052 live hot-patches as tests that fail against pre-053 behavior
(SC-008): client-outlasts-server timeout, trailing-log reply parse, full HTTP
body read across segments, and typed errors for missing fields.
"""

import asyncio
import importlib.util
import os
import re

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(REPO, "mcp-servers", "protocol-mcp")


# ---- T026: client timeout outlasts server timeouts (FR-017) ----------------

def test_client_timeout_outlasts_server():
    server = open(os.path.join(REPO, "mcp-servers", "n2n-mcp", "server.py")).read()
    m = re.search(r"async def _post.*?timeout=(\d+)", server, re.S)
    client_timeout = int(m.group(1))
    # Daemon operation timeouts (defaults): chat 300, skill 600
    chat = int(os.environ.get("N2N_CHAT_IDLE_TIMEOUT_S", "300"))
    skill = int(os.environ.get("N2N_SKILL_TIMEOUT_S", "600"))
    assert client_timeout > chat and client_timeout > skill, (
        f"n2n-mcp _post timeout {client_timeout}s must outlast daemon chat={chat}s "
        f"and skill={skill}s so completed replies are never dropped (FR-017)")


# ---- T027: reply parse tolerates trailing non-JSON (FR-018) ----------------

def test_extract_reply_tolerates_trailing_log():
    import sys
    sys.path.insert(0, PROTO)
    from bgp.federation.gateway import _extract_reply
    envelope = ('legacy migration banner\n'
                '{"result": {"finalAssistantVisibleText": "the answer"}}\n'
                '[agent] run abc123 elapsed=4s stopReason=stop\n')
    reply, tokens = _extract_reply(envelope)
    assert reply == "the answer", f"trailing log line broke parsing: {reply!r}"


# ---- T028: full body read across segments + typed errors (FR-019) ----------

def _load_daemon():
    import sys
    sys.path.insert(0, PROTO)
    spec = importlib.util.spec_from_file_location("bgp_daemon_v2",
                                                  os.path.join(PROTO, "bgp-daemon-v2.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_typed_error_for_missing_field(tmp_path):
    asyncio.run(_typed_error(tmp_path))


async def _typed_error(tmp_path):
    mod = _load_daemon()
    from bgp.federation.service import FederationService
    from bgp.federation.manager import FederationManager
    mod._federation = FederationService(local_as=65001, router_id="4.4.4.4",
                                        manager=FederationManager(base_dir=str(tmp_path)))
    # chat/send with no 'peer' → clean typed 400, not a bare KeyError string
    code, body = await mod.handle_n2n("POST", "/n2n/chat/send", {"text": "hi"})
    assert code == 400 and "peer" in body.get("error", "")


def test_full_body_read_across_segments(tmp_path):
    asyncio.run(_segmented_body(tmp_path))


async def _segmented_body(tmp_path):
    """handle_http must read the whole body even when headers and body arrive in
    separate TCP segments (the 052 'missing peer' root cause)."""
    mod = _load_daemon()
    from bgp.federation.service import FederationService
    from bgp.federation.manager import FederationManager
    mod._federation = FederationService(local_as=65001, router_id="4.4.4.4",
                                        manager=FederationManager(base_dir=str(tmp_path)))
    mod._speaker = None

    import json as _json
    body = _json.dumps({"item_type": "skill", "item_name": "demo", "visibility": "hidden"})
    headers = ("POST /n2n/visibility HTTP/1.1\r\nHost: x\r\n"
               f"Content-Length: {len(body)}\r\nContent-Type: application/json\r\n\r\n")

    reader = asyncio.StreamReader()

    class _W:
        def __init__(self): self.buf = b""
        def write(self, d): self.buf += d
        async def drain(self): pass
        def close(self): pass
        def get_extra_info(self, *a, **k): return None

    w = _W()
    # Feed headers first, then the body in a SEPARATE segment after a tick
    async def feed():
        reader.feed_data(headers.encode())
        await asyncio.sleep(0.05)
        reader.feed_data(body.encode())
        reader.feed_eof()

    asyncio.create_task(feed())
    await mod.handle_http(reader, w)
    resp = w.buf.decode(errors="replace")
    # Body was fully read → visibility route succeeded (not a "missing field" 400)
    assert '"success": true' in resp.lower() or '"success":true' in resp.lower(), resp[-300:]
