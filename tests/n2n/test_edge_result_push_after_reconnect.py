"""Regression: the finished answer must be pushed to the member's CURRENT
channel, not only to the object that submitted the request.

`_push_result_when_done` guarded on `ch is channel` — object identity against
the channel that had submitted the ask. Phones reconnect constantly (a real
iPhone reconnected 4x during one 2-minute turn), so on any request long enough
to span a reconnect the push was skipped **entirely**: not attempted, not
logged, not retried. The work completed, the answer existed on the Border, and
the phone sat on "Working" forever.

Object identity was never the security property. The member identity and the
channel's `trusted` flag are, and both are still enforced.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "mcp-servers", "protocol-mcp"))


class _FakeChannel:
    """Minimal stand-in for EdgeChannel: records what was notified."""

    def __init__(self, trusted=True, member_id="risk/phone", fail=False):
        self.trusted = trusted
        self.member_id = member_id
        self.notified = []
        self._fail = fail

    async def notify(self, method, params):
        if self._fail:
            raise ConnectionError("socket gone")
        self.notified.append((method, params))


async def _push(service, member_id, task_id, submitting_channel, result):
    """The delivery decision under test, mirroring _push_result_when_done's
    guards after the worker has completed."""
    ch = service.edge_channels.get(member_id)
    if ch is None:
        return "no-channel"
    if not getattr(ch, "trusted", False):
        return "untrusted"
    try:
        await ch.notify("n2n/edge/ask_result", {
            "task_id": task_id,
            "state": result.get("state"),
            "output_text": result.get("output_text"),
            "error": result.get("error"),
            "tokens_used": result.get("tokens_used"),
        })
    except Exception:
        return "notify-failed"
    return "pushed"


class _Svc:
    def __init__(self):
        self.edge_channels = {}


def test_push_reaches_a_reconnected_channel():
    """The scenario that broke: submit on channel A, reconnect to B, finish."""
    svc = _Svc()
    submitted_on = _FakeChannel()
    svc.edge_channels["risk/phone"] = submitted_on
    # ... the phone reconnects mid-turn; a NEW channel object replaces it.
    reconnected = _FakeChannel()
    svc.edge_channels["risk/phone"] = reconnected

    outcome = asyncio.run(_push(
        svc, "risk/phone", "t1", submitted_on,
        {"state": "completed", "output_text": "the answer", "tokens_used": 5}))

    assert outcome == "pushed", "a reconnect must not lose the answer"
    assert reconnected.notified, "the live channel should have received it"
    method, params = reconnected.notified[0]
    assert method == "n2n/edge/ask_result"
    assert params["output_text"] == "the answer"
    assert not submitted_on.notified, "the dead channel must not be used"


def test_push_still_works_without_a_reconnect():
    svc = _Svc()
    ch = _FakeChannel()
    svc.edge_channels["risk/phone"] = ch

    outcome = asyncio.run(_push(svc, "risk/phone", "t1", ch,
                                {"state": "completed", "output_text": "x"}))

    assert outcome == "pushed"
    assert len(ch.notified) == 1


def test_no_live_channel_is_reported_not_silently_dropped():
    """The phone recovers via n2n/tasks/result — but the skip must be visible."""
    svc = _Svc()
    outcome = asyncio.run(_push(svc, "risk/phone", "t1", _FakeChannel(),
                                {"state": "completed", "output_text": "x"}))
    assert outcome == "no-channel"


def test_an_untrusted_channel_is_never_pushed_to():
    """Dropping object identity must NOT drop the actual security check."""
    svc = _Svc()
    svc.edge_channels["risk/phone"] = _FakeChannel(trusted=False)

    outcome = asyncio.run(_push(svc, "risk/phone", "t1", _FakeChannel(),
                                {"state": "completed", "output_text": "secret"}))

    assert outcome == "untrusted"
    assert not svc.edge_channels["risk/phone"].notified


def test_a_push_to_another_member_is_impossible():
    """Delivery is keyed by member_id, so one phone's answer cannot land on
    another phone's channel."""
    svc = _Svc()
    mine = _FakeChannel(member_id="risk/mine")
    theirs = _FakeChannel(member_id="risk/theirs")
    svc.edge_channels["risk/mine"] = mine
    svc.edge_channels["risk/theirs"] = theirs

    asyncio.run(_push(svc, "risk/mine", "t1", mine,
                      {"state": "completed", "output_text": "mine only"}))

    assert mine.notified
    assert not theirs.notified


def test_a_failed_task_forwards_its_reason():
    svc = _Svc()
    ch = _FakeChannel()
    svc.edge_channels["risk/phone"] = ch

    asyncio.run(_push(svc, "risk/phone", "t1", ch,
                      {"state": "failed", "error": "agent turn timed out"}))

    _, params = ch.notified[0]
    assert params["error"] == "agent turn timed out", (
        "a bare 'failed' with no reason is what made this undiagnosable")


def test_a_dead_socket_does_not_raise_out_of_the_worker():
    svc = _Svc()
    svc.edge_channels["risk/phone"] = _FakeChannel(fail=True)

    outcome = asyncio.run(_push(svc, "risk/phone", "t1", _FakeChannel(),
                                {"state": "completed", "output_text": "x"}))

    assert outcome == "notify-failed"


def test_real_service_guard_no_longer_uses_object_identity():
    """Guard against the identity check being reintroduced in the source."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers",
                        "protocol-mcp", "bgp", "federation", "service.py")
    with open(path) as f:
        src = f.read()
    start = src.index("async def _push_result_when_done")
    body = src[start:start + 2600]
    assert "if ch and ch is channel:" not in body, (
        "the object-identity guard is back — a reconnect will silently drop "
        "the answer again")
    assert 'notify("n2n/edge/ask_result"' in body
