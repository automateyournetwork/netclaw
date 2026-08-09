"""Feature 100 (T010/T015): pre-handshake disconnect classification.

Two opposing requirements have to hold simultaneously, which is the whole reason this
file exists:

* **FR-017/020** — a probe, scan, or aborted dial must produce one quiet line and no
  stack trace. Before this feature a zero-byte connect produced a ~10-line ERROR
  traceback from the catch-all.
* **FR-019** — an *unexpected internal fault* must STILL reach that catch-all with
  `exc_info=True`. A too-broad `except` would satisfy FR-017 perfectly while silently
  swallowing real bugs. That regression is invisible in production, so it is asserted
  here.

FR-018 is also guarded: a complete-but-invalid preamble means something spoke far
enough to be wrong, and keeps its existing one-line WARNING.

Run under /usr/bin/python3 (3.14.4) — asyncio exception behavior is under test
(research R1).
"""

import asyncio
import logging

import pytest

from bgp.agent import _BENIGN_PREAMBLE_ERRORS, _PROBE_TRACK_MAX, BGPAgent


def _agent():
    return BGPAgent(local_as=65001, router_id="4.4.4.4")


def _lines(caplog):
    """Only the agent's own records.

    `asyncio.run()` emits its own DEBUG line ("Using selector: EpollSelector") from
    the asyncio logger on every call, which would inflate every count in this file and
    make "exactly one line" assertions meaningless.
    """
    return [r for r in caplog.records if r.name.startswith("BGPAgent")]


class _FakeWriter:
    """Minimal StreamWriter stand-in: records closure, never blocks."""

    def __init__(self, fail_close=False):
        self.closed = False
        self._fail_close = fail_close

    def get_extra_info(self, _key):
        return ("127.0.0.1", 4242)

    def close(self):
        if self._fail_close:
            raise OSError("already gone")
        self.closed = True

    async def wait_closed(self):
        return None


# ── The narrow catch tuple (FR-019's structural guard) ────────────────────────

def test_benign_tuple_covers_the_observed_failure_modes():
    """These are what a probe / aborted dial actually raises."""
    for exc_type in (asyncio.IncompleteReadError, ConnectionResetError,
                     BrokenPipeError, TimeoutError):
        assert issubclass(exc_type, _BENIGN_PREAMBLE_ERRORS)


def test_benign_tuple_does_not_swallow_unexpected_faults():
    """FR-019, structurally. If someone widens the tuple to Exception or adds a broad
    base class, real bugs stop producing tracebacks and this fails."""
    assert Exception not in _BENIGN_PREAMBLE_ERRORS
    assert BaseException not in _BENIGN_PREAMBLE_ERRORS
    for exc_type in (ValueError, TypeError, AttributeError, KeyError,
                     IndexError, RuntimeError, ZeroDivisionError):
        assert not issubclass(exc_type, _BENIGN_PREAMBLE_ERRORS), (
            f"{exc_type.__name__} would be treated as a benign disconnect — "
            "FR-019 requires unexpected faults to keep reaching the catch-all")


def test_oserror_itself_is_not_blanket_benign():
    """ConnectionResetError/BrokenPipeError are benign; a bare OSError (e.g. EMFILE,
    'too many open files') is a real operational fault an operator must see."""
    assert not issubclass(OSError, _BENIGN_PREAMBLE_ERRORS)


# ── One quiet line, no traceback (FR-017, SC-004) ─────────────────────────────

def test_zero_byte_connect_logs_once_without_traceback(caplog):
    agent = _agent()
    writer = _FakeWriter()
    exc = asyncio.IncompleteReadError(partial=b"", expected=1)

    with caplog.at_level(logging.DEBUG):
        asyncio.run(agent._note_benign_disconnect("127.0.0.1", exc, writer, consumed=0))

    recs = _lines(caplog)
    assert len(recs) == 1, "SC-004: exactly one log line"
    rec = recs[0]
    assert rec.exc_info is None, "SC-004: no stack trace"
    assert rec.levelno == logging.DEBUG, "FR-020: a probe is not actionable"
    assert "127.0.0.1" in rec.getMessage(), "FR-017: must name the source"
    assert "IncompleteReadError" in rec.getMessage(), "FR-017: must name the reason"
    assert writer.closed


def test_truncated_preamble_reports_bytes_seen(caplog):
    """'3 of 4 bytes' vs '0 bytes' distinguishes a dying peer from a port scan."""
    agent = _agent()
    exc = asyncio.IncompleteReadError(partial=b"CFE", expected=4)

    with caplog.at_level(logging.DEBUG):
        asyncio.run(agent._note_benign_disconnect("10.0.0.9", exc, _FakeWriter(),
                                                  consumed=1))

    msg = _lines(caplog)[0].getMessage()
    assert "4 bytes" in msg, f"1 consumed + 3 partial should read as 4: {msg}"


def test_connection_reset_is_benign(caplog):
    agent = _agent()
    with caplog.at_level(logging.DEBUG):
        asyncio.run(agent._note_benign_disconnect("8.8.8.8", ConnectionResetError(),
                                                  _FakeWriter()))
    recs = _lines(caplog)
    assert len(recs) == 1
    assert recs[0].exc_info is None


def test_writer_close_failure_does_not_add_noise(caplog):
    """The peer is gone by definition; a failed polite close is not worth a line."""
    agent = _agent()
    with caplog.at_level(logging.DEBUG):
        asyncio.run(agent._note_benign_disconnect(
            "1.2.3.4", ConnectionResetError(), _FakeWriter(fail_close=True)))
    assert len(_lines(caplog)) == 1


# ── Probe collapsing (FR-038) ─────────────────────────────────────────────────

def test_first_sighting_always_logged_then_repeats_collapse(caplog):
    """A single genuine aborted dial must never be silently swallowed, but a scan
    must not produce a line per connection."""
    agent = _agent()
    agent._probe_summary_interval = 3600        # never summarize during this test

    with caplog.at_level(logging.DEBUG):
        for _ in range(50):
            asyncio.run(agent._note_benign_disconnect(
                "203.0.113.7", ConnectionResetError(), _FakeWriter()))

    recs = _lines(caplog)
    assert len(recs) == 1, (
        f"FR-038: 50 probes from one source should collapse to the first line, "
        f"got {len(recs)}")
    assert agent._probe_health["203.0.113.7"]["count"] == 49


def test_summary_emitted_after_the_interval(caplog):
    agent = _agent()
    agent._probe_summary_interval = 0           # summarize on the next repeat

    with caplog.at_level(logging.DEBUG):
        asyncio.run(agent._note_benign_disconnect("203.0.113.8", ConnectionResetError(),
                                                  _FakeWriter()))
        caplog.clear()
        for _ in range(5):
            asyncio.run(agent._note_benign_disconnect(
                "203.0.113.8", ConnectionResetError(), _FakeWriter()))

    summaries = [r for r in _lines(caplog) if "probe traffic" in r.getMessage()]
    assert summaries, "FR-038 requires a periodic summary"
    msg = summaries[0].getMessage()
    assert "non-protocol connections" in msg
    assert "203.0.113.8" in msg, "the summary must still name its source"
    assert summaries[0].levelno == logging.INFO


def test_changed_reason_logs_immediately(caplog):
    """FR-015's principle applied to probes: a materially different cause is news."""
    agent = _agent()
    agent._probe_summary_interval = 3600

    with caplog.at_level(logging.DEBUG):
        asyncio.run(agent._note_benign_disconnect("203.0.113.9", ConnectionResetError(),
                                                  _FakeWriter()))
        caplog.clear()
        asyncio.run(agent._note_benign_disconnect(
            "203.0.113.9", asyncio.IncompleteReadError(partial=b"", expected=1),
            _FakeWriter()))

    assert _lines(caplog), "a changed reason must not wait for the interval"


def test_probe_dict_is_bounded_under_source_rotation():
    """data-model §5: a scanner rotating source IPs must not grow this without limit.
    A log-noise fix becoming a memory leak would be a worse defect than the noise."""
    agent = _agent()
    agent._probe_summary_interval = 3600

    for i in range(_PROBE_TRACK_MAX + 200):
        ip = f"198.51.{i // 256}.{i % 256}"
        asyncio.run(agent._note_benign_disconnect(ip, ConnectionResetError(),
                                                  _FakeWriter()))

    assert len(agent._probe_health) <= _PROBE_TRACK_MAX, (
        f"probe tracking grew to {len(agent._probe_health)}, cap is {_PROBE_TRACK_MAX}")


def test_dampen_disabled_logs_every_occurrence(caplog):
    """FR-028's principle: an operator diagnosing must be able to see them all."""
    agent = _agent()
    agent._probe_dampen = False

    with caplog.at_level(logging.DEBUG):
        for _ in range(5):
            asyncio.run(agent._note_benign_disconnect(
                "192.0.2.1", ConnectionResetError(), _FakeWriter()))

    assert len(_lines(caplog)) == 5


def test_distinct_sources_each_get_a_line(caplog):
    """FR-038/FR-016: suppression must still convey that multiple sources are involved."""
    agent = _agent()
    agent._probe_summary_interval = 3600

    with caplog.at_level(logging.DEBUG):
        for i in range(4):
            asyncio.run(agent._note_benign_disconnect(
                f"192.0.2.{i}", ConnectionResetError(), _FakeWriter()))

    assert len(_lines(caplog)) == 4
