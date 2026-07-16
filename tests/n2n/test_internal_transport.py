"""iN2N internal transport: member-initiated dial + pinned-key auth (feature 056, US1).

Drives a real Border + Member FederationService over a loopback TCP socket
(the same harness style as test_two_daemon_loopback.py). Covers FR-006/007/007a/
013a and SC-011. The frozen NCFED framing is reused via InternalChannel.
"""

import asyncio
import json

import pytest

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.internal_channel import IN2N_MAGIC, InternalChannel
from bgp.constants import NCFED_MAX_PAYLOAD
from bgp.federation.channel import encode_frames


def _service(base, local_as, rid, name):
    mgr = FederationManager(base_dir=str(base))
    return FederationService(local_as=local_as, router_id=rid, display_name=name, manager=mgr)


def test_frames_byte_identical_to_en2n():
    """InternalChannel reuses the frozen NCFED framing (encode_frames)."""
    msg = {"jsonrpc": "2.0", "id": 1, "method": "in2n/hello", "params": {}}
    frames = encode_frames(msg)
    # single frame, 5-byte header (4 len + 1 flags), same as eN2N
    assert len(frames) == 1
    assert len(frames[0]) == 5 + len(json.dumps(msg, separators=(",", ":")))


def test_enroll_then_reconnect_over_loopback(tmp_path):
    asyncio.run(_enroll_then_reconnect(tmp_path))


async def _enroll_then_reconnect(tmp_path):
    border = _service(tmp_path / "border", 65001, "4.4.4.4", "Border")
    member = _service(tmp_path / "member", 65001, "4.4.4.4", "Member")

    border.risk.set_role("border", risk_name="risk", enabled_stacks="in2n",
                         border_endpoint="127.0.0.1:0")
    member.risk.set_role("member", risk_name="risk", border_endpoint="127.0.0.1:0",
                         self_member_id="risk/cml")
    token = border.risk.issue_token(label="cml")["token"]

    async def on_conn(reader, writer):
        await border.accept_internal(reader, writer)

    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    # Not `async with server`: on Python 3.12+ Server.wait_closed() (run by
    # __aexit__) waits for every connection handler to return, and the border's
    # accept_internal handlers live as long as the member channel stays open —
    # the test would hang forever. close() alone stops the listener; asyncio.run
    # teardown reaps the handler tasks.
    try:
        # First contact: member dials out and ENROLLS (token + signed nonce).
        resp = await member.dial_border("127.0.0.1", port, enrollment_token=token)
        await asyncio.sleep(0.2)
        assert resp["pinned"] is True
        mem = border.risk.get_member("risk/cml")
        assert mem["state"] == "active"
        # Border pinned the member's self-signed key.
        assert mem["key_fingerprint"] == border.risk.fingerprint_of(member.risk.self_cert_pem())
        # Hub-and-spoke: the member holds no member registry of its own (no
        # member-to-member), and opened no listener (FR-007a/SC-011).
        assert member.member_channels == {}
        assert "risk/cml" in border.member_channels

        # Token is single-use — cannot enroll a second time with it.
        with pytest.raises(Exception):
            m2 = _service(tmp_path / "m2", 65001, "4.4.4.4", "M2")
            m2.risk.set_role("member", risk_name="risk", self_member_id="risk/dup")
            await m2.dial_border("127.0.0.1", port, enrollment_token=token)
        await asyncio.sleep(0.1)

        # Drop the member's channel; RECONNECT authenticates via the pinned key
        # (in2n/hello, no token).
        await member.border_channel.close()
        border.member_channels.pop("risk/cml", None)
        await asyncio.sleep(0.1)
        resp2 = await member.dial_border("127.0.0.1", port)  # no token → hello path
        await asyncio.sleep(0.2)
        assert resp2["trusted"] is True
        assert "risk/cml" in border.member_channels
    finally:
        server.close()

    border.manager.close(); member.manager.close()


def test_wrong_key_reconnect_refused(tmp_path):
    asyncio.run(_wrong_key_refused(tmp_path))


async def _wrong_key_refused(tmp_path):
    border = _service(tmp_path / "b", 65001, "4.4.4.4", "Border")
    border.risk.set_role("border", risk_name="risk", enabled_stacks="in2n")
    token = border.risk.issue_token()["token"]

    # Enroll a legit member first.
    member = _service(tmp_path / "m", 65001, "4.4.4.4", "Member")
    member.risk.set_role("member", risk_name="risk", self_member_id="risk/cml")

    async def on_conn(reader, writer):
        await border.accept_internal(reader, writer)
    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    # See _enroll_then_reconnect: no `async with server` — wait_closed() on
    # Python 3.12+ would block on the live member-channel handler forever.
    try:
        await member.dial_border("127.0.0.1", port, enrollment_token=token)
        await asyncio.sleep(0.2)
        # An imposter claiming the same member_id with a DIFFERENT key → refused.
        imposter = _service(tmp_path / "imp", 65001, "4.4.4.4", "Imposter")
        imposter.risk.set_role("member", risk_name="risk", self_member_id="risk/cml")
        with pytest.raises(Exception):
            await imposter.dial_border("127.0.0.1", port)  # hello with non-pinned key
        await asyncio.sleep(0.1)
    finally:
        server.close()
    border.manager.close(); member.manager.close(); imposter.manager.close()
