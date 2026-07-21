"""NCFED -00 pre-submission protocol hardening.

Covers the four spec-relevant patches:
  1. (AS, router-id) tuple tie-break for the deterministic initiator (§5)
  2. Aggregate reassembly bound + timeout + heartbeat-mid-reassembly (§7/§14.7)
  3. Task retrieval bound to the submitting peer (§9.2/§14.6)
  4. MEMBER_ID_TAKEN (-32022) emitted on the wire (§9.3)
"""

import asyncio
import struct

import pytest

from bgp.constants import (
    NCFED_FLAG_CONTINUATION,
    IN2N_ERR_MEMBER_ID_TAKEN,
    ncfed_initiates,
)
from bgp.federation.channel import FederationChannel, RpcError, encode_frames


# ---- 1. deterministic-initiator tuple ordering --------------------------

def test_lower_as_initiates():
    assert ncfed_initiates(65001, "192.0.2.9", 65007, "192.0.2.1")
    assert not ncfed_initiates(65007, "192.0.2.1", 65001, "192.0.2.9")


def test_equal_as_lower_router_id_initiates():
    assert ncfed_initiates(65001, "192.0.2.1", 65001, "192.0.2.2")
    assert not ncfed_initiates(65001, "192.0.2.2", 65001, "192.0.2.1")


def test_router_id_compared_as_network_order_integer():
    # 10.0.0.2 (0x0A000002) < 192.0.2.1 (0xC0000201), regardless of string order
    assert ncfed_initiates(65001, "10.0.0.2", 65001, "192.0.2.1")


def test_equal_tuple_neither_initiates():
    assert not ncfed_initiates(65001, "192.0.2.1", 65001, "192.0.2.1")


# ---- 2. reassembly bounds ------------------------------------------------

class _NullWriter:
    def write(self, b):
        pass

    async def drain(self):
        pass

    def close(self):
        pass


class _FakeManager:
    def is_federated(self, ident):
        return True


def _frame(payload: bytes, continuation: bool) -> bytes:
    flags = NCFED_FLAG_CONTINUATION if continuation else 0
    return struct.pack("!IB", len(payload), flags) + payload


def _run_channel(frames: list):
    """Feed frames to a channel's read loop; return (channel, dispatched params)."""
    seen = []

    async def go():
        reader = asyncio.StreamReader()
        for f in frames:
            reader.feed_data(f)
        reader.feed_eof()

        async def on_hello(channel, params):
            seen.append(params)

        ch = FederationChannel(reader, _NullWriter(),
                               local_identity="as65001-192.0.2.1",
                               peer_as=65007, peer_router_id="192.0.2.7",
                               manager=_FakeManager(), is_initiator=True,
                               handlers={"n2n/hello": on_hello})
        await ch._read_loop()
        return ch

    ch = asyncio.run(go())
    return ch, seen


def _hello_frames() -> list:
    return encode_frames({"jsonrpc": "2.0", "method": "n2n/hello", "params": {"ok": 1}})


def test_chunked_message_within_bound_dispatches():
    msg = {"jsonrpc": "2.0", "method": "n2n/hello", "params": {"blob": "A" * 200000}}
    ch, seen = _run_channel(encode_frames(msg))
    assert len(seen) == 1 and seen[0]["blob"] == "A" * 200000


def test_aggregate_reassembly_bound_closes(monkeypatch):
    import bgp.federation.channel as chmod
    monkeypatch.setattr(chmod, "NCFED_MAX_MESSAGE", 1024)
    frames = [_frame(b"A" * 600, True), _frame(b"B" * 600, True),
              _frame(b"C" * 100, False)] + _hello_frames()
    ch, seen = _run_channel(frames)
    assert ch._closed
    assert seen == []          # nothing dispatched, later frames never processed


def test_reassembly_timeout_closes(monkeypatch):
    import bgp.federation.channel as chmod
    monkeypatch.setattr(chmod, "NCFED_REASSEMBLY_TIMEOUT", -1.0)
    frames = [_frame(b"A" * 10, True), _frame(b"B" * 10, False)] + _hello_frames()
    ch, seen = _run_channel(frames)
    assert ch._closed
    assert seen == []


def test_heartbeat_mid_reassembly_closes():
    # Length-0 CONTINUATION-clear inside a reassembly is a protocol error (§7);
    # before the patch it silently terminated the message instead.
    frames = [_frame(b"A" * 10, True), _frame(b"", False)] + _hello_frames()
    ch, seen = _run_channel(frames)
    assert ch._closed
    assert seen == []


def test_zero_length_continuation_fragment_is_legal():
    # §7: a Length-0 frame WITH the continuation flag is a legal empty fragment.
    payload = b'{"jsonrpc":"2.0","method":"n2n/hello","params":{"ok":2}}'
    frames = [_frame(payload[:10], True), _frame(b"", True),
              _frame(payload[10:], False)]
    ch, seen = _run_channel(frames)
    assert len(seen) == 1 and seen[0]["ok"] == 2


def test_zero_length_continuation_drip_still_times_out(monkeypatch):
    # Regression for the reassembly-timer bug: a drip of legal zero-length
    # continuation frames kept _recv_buf empty, which reset the deadline every
    # frame. With state tracked by an explicit flag, the timer starts on the
    # first fragment and the drip cannot hold the reassembly open past the bound.
    import bgp.federation.channel as chmod
    monkeypatch.setattr(chmod, "NCFED_REASSEMBLY_TIMEOUT", -1.0)
    frames = [_frame(b"", True), _frame(b"", True), _frame(b"", True),
              _frame(b"payload", False)] + _hello_frames()
    ch, seen = _run_channel(frames)
    assert ch._closed
    assert seen == []


# ---- 3. task retrieval bound to the submitting peer ----------------------

@pytest.fixture
def ledger(manager):
    from bgp.federation.tasks import TaskManager
    return TaskManager(manager, audit=None)


def test_task_owner_sees_status_and_result(ledger):
    tid = ledger.create(direction="inbound", peer_identity="as65007-192.0.2.7",
                        target_type="skill", target_name="demo", input_text="x")
    assert ledger.status(tid, owner="as65007-192.0.2.7")["state"] == "submitted"
    assert ledger.result(tid, owner="as65007-192.0.2.7")["state"] == "submitted"


def test_task_non_owner_sees_unknown(ledger):
    tid = ledger.create(direction="inbound", peer_identity="as65007-192.0.2.7",
                        target_type="skill", target_name="demo", input_text="x")
    # Existence must not be probeable: apart from the echoed task_id, the answer
    # is exactly the missing-task shape
    got = ledger.status(tid, owner="as65099-192.0.2.99")
    missing = ledger.status("no-such-task", owner="as65099-192.0.2.99")
    assert got == {"task_id": tid, "state": "unknown"}
    assert missing == {"task_id": "no-such-task", "state": "unknown"}
    assert ledger.result(tid, owner="as65099-192.0.2.99")["state"] == "unknown"
    assert ledger.cancel(tid, owner="as65099-192.0.2.99") is False


def test_task_outbound_rows_not_retrievable_remotely(ledger):
    # A peer must not read our record of a task WE submitted to someone,
    # even if it somehow learns the id — remote retrieval serves inbound only.
    ledger.record_outbound("out-1", "as65007-192.0.2.7", "skill", "demo")
    assert ledger.status("out-1", owner="as65007-192.0.2.7")["state"] == "unknown"
    assert ledger.status("out-1")["state"] == "submitted"   # local view unrestricted


def test_task_local_callers_unrestricted(ledger):
    tid = ledger.create(direction="inbound", peer_identity="as65007-192.0.2.7",
                        target_type="skill", target_name="demo", input_text="x")
    assert ledger.status(tid)["state"] == "submitted"


# ---- 4. MEMBER_ID_TAKEN emitted on the wire -------------------------------

def test_enroll_maps_member_id_taken_to_32022():
    from bgp.federation.service import FederationService

    class _Risk:
        def is_border(self):
            return True

        def verify_possession(self, cert, nonce, sig):
            return True

        def consume_token(self, *a, **kw):
            raise ValueError("IN2N_ERR_MEMBER_ID_TAKEN: already pinned to another key")

    class _Chan:
        nonce = b"\x00" * 32

    svc = FederationService.__new__(FederationService)
    svc.risk = _Risk()
    with pytest.raises(RpcError) as ei:
        asyncio.run(svc._in2n_on_enroll(_Chan(), {
            "token": "in2n_x", "member_id": "r/cml",
            "cert_pem": "PEM", "signature": ""}))
    assert ei.value.code == IN2N_ERR_MEMBER_ID_TAKEN == -32022


def test_enroll_maps_spent_token_to_32021():
    from bgp.federation.service import FederationService
    from bgp.constants import IN2N_ERR_ENROLL_TOKEN_INVALID

    class _Risk:
        def is_border(self):
            return True

        def verify_possession(self, cert, nonce, sig):
            return True

        def consume_token(self, *a, **kw):
            raise ValueError("IN2N_ERR_ENROLL_TOKEN_INVALID: token spent")

    class _Chan:
        nonce = b"\x00" * 32

    svc = FederationService.__new__(FederationService)
    svc.risk = _Risk()
    with pytest.raises(RpcError) as ei:
        asyncio.run(svc._in2n_on_enroll(_Chan(), {
            "token": "in2n_x", "member_id": "r/cml",
            "cert_pem": "PEM", "signature": ""}))
    assert ei.value.code == IN2N_ERR_ENROLL_TOKEN_INVALID == -32021


# ---- 5. no remote sever method (NCFED -00 §13) ---------------------------

def test_no_remote_sever_handler(manager):
    from bgp.federation.service import FederationService
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=manager)
    # Severing is local-only; there must be no wire method a peer can call to
    # revoke our grant (a keyless federated claimant could otherwise do so).
    assert "n2n/sever" not in svc.handlers
    assert not hasattr(svc, "_on_sever")


def test_sever_local_still_works(manager):
    from bgp.federation.service import FederationService
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=manager)
    manager.local_consent(65007, "7.7.7.7")
    manager.remote_consent(65007, "7.7.7.7")
    ident = "as65007-7.7.7.7"
    assert manager.is_federated(ident)
    assert asyncio.run(svc.sever_local(ident)) is True
    assert not manager.is_federated(ident)


# ---- 6. TLS 1.3 minimum (NCFED -00 §6.1) ---------------------------------

def test_tls_contexts_require_tls13():
    import ssl
    from bgp.federation import tls, certs
    cert_pem, key_pem = certs.create_self_signed("as65001-4.4.4.4")
    sctx = tls.server_context(cert_pem, key_pem)
    assert sctx.minimum_version == ssl.TLSVersion.TLSv1_3
    for model in ("domain-verified", "pinned"):
        cctx, _ = tls.client_context(model, claw_domain="example.test")
        assert cctx.minimum_version == ssl.TLSVersion.TLSv1_3
