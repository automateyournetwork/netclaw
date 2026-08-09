"""Feature 100 (T013): the asyncio `eof_received` filter must be narrow.

FR-030 is explicit that the remedy "MUST NOT be addressed by suppressing genuine
warnings from the same runtime." The failure mode this guards is therefore not "the
noisy line still appears" — it is "the fix silenced the asyncio logger wholesale and
now real asyncio warnings are invisible too." That second failure is silent, which is
why it is tested rather than eyeballed.

Run under /usr/bin/python3 (3.14.4) — this asserts stdlib logging behavior, and the
repo .venv is a different interpreter (research R1).
"""

import logging

import pytest

from bgp.federation.logfilter import (
    EofReceivedNoiseFilter,
    _EOF_RECEIVED_FRAGMENT,
    install,
)

EOF_MESSAGE = "returning true from eof_received() has no effect when using ssl"


def _record(msg, *args, level=logging.WARNING, name="asyncio"):
    return logging.LogRecord(name=name, level=level, pathname=__file__, lineno=1,
                             msg=msg, args=args, exc_info=None)


@pytest.fixture
def filt():
    return EofReceivedNoiseFilter()


# ── The line it must drop ─────────────────────────────────────────────────────

def test_drops_the_eof_received_advisory(filt):
    assert filt.filter(_record(EOF_MESSAGE)) is False


def test_drops_it_when_embedded_in_a_longer_line(filt):
    """CPython may prefix or suffix context; substring matching must still catch it."""
    assert filt.filter(_record(f"ssl transport: {EOF_MESSAGE} (protocol=X)")) is False


def test_drops_it_when_built_from_format_args(filt):
    """getMessage() must be used, not record.msg — otherwise a %-formatted emission
    slips through."""
    assert filt.filter(_record("returning true from %s has no effect when using ssl",
                               "eof_received()")) is False


# ── Everything else must pass (FR-030's real constraint) ──────────────────────

@pytest.mark.parametrize("msg", [
    "socket.send() raised exception.",
    "Executing <Task pending ...> took 0.512 seconds",
    "SSL handshake failed",
    "Future exception was never retrieved",
    "eof_received",                        # bare token, not the advisory
    "returning true from eof_received() has no effect",   # truncated, not the advisory
    "Unclosed client session",
])
def test_other_asyncio_warnings_pass_through(filt, msg):
    assert filt.filter(_record(msg)) is True


def test_does_not_filter_by_level(filt):
    """Severity must be irrelevant — an ERROR from asyncio is never suppressed."""
    for level in (logging.DEBUG, logging.INFO, logging.WARNING,
                  logging.ERROR, logging.CRITICAL):
        assert filt.filter(_record("genuine asyncio problem", level=level)) is True


def test_does_not_filter_by_logger_name(filt):
    """The match is on message text alone. A record from any logger carrying the
    advisory is dropped; a record from asyncio not carrying it is kept."""
    assert filt.filter(_record(EOF_MESSAGE, name="asyncio.sslproto")) is False
    assert filt.filter(_record("real problem", name="asyncio")) is True


def test_malformed_record_is_passed_through_not_swallowed():
    """A record that cannot be formatted is certainly not the advisory — letting it
    through beats discarding a broken log call."""
    filt = EofReceivedNoiseFilter()
    bad = _record("%d items", "not-an-int")     # %-formatting will raise
    assert filt.filter(bad) is True


# ── Installation ──────────────────────────────────────────────────────────────

def test_install_attaches_to_the_asyncio_logger():
    target = logging.getLogger("asyncio")
    before = list(target.filters)
    try:
        f = install()
        assert f in logging.getLogger("asyncio").filters
    finally:
        target.filters = before


def test_install_is_idempotent():
    """The daemon may import more than once; a second install must not stack filters."""
    target = logging.getLogger("asyncio")
    before = list(target.filters)
    try:
        first = install()
        second = install()
        assert first is second
        installed = [f for f in target.filters if isinstance(f, EofReceivedNoiseFilter)]
        assert len(installed) == 1
    finally:
        target.filters = before


def test_installed_filter_suppresses_end_to_end(caplog):
    """Through a real logger call, not just filter() in isolation."""
    target = logging.getLogger("asyncio")
    before = list(target.filters)
    try:
        install()
        # caplog's handler sits on the root logger; a logger-level filter drops the
        # record before propagation, so this exercises the real path.
        with caplog.at_level(logging.WARNING, logger="asyncio"):
            target.warning(EOF_MESSAGE)
            target.warning("a genuine asyncio warning")
        messages = [r.getMessage() for r in caplog.records]
        assert EOF_MESSAGE not in messages
        assert "a genuine asyncio warning" in messages
    finally:
        target.filters = before


def test_fragment_matches_the_cpython_wording():
    """Guard against someone 'tidying' the fragment into something that never matches.
    The daemon would then go back to emitting the advisory with no test failing."""
    assert _EOF_RECEIVED_FRAGMENT in EOF_MESSAGE
