"""Targeted suppression of one stdlib asyncio warning (feature 100, FR-030).

CPython's `asyncio/sslproto.py` emits

    returning true from eof_received() has no effect when using ssl

whenever an application protocol's `eof_received()` returns a true value over TLS.
`asyncio.streams.StreamReaderProtocol.eof_received()` returns `True` unconditionally,
and NetClaw obtains its federation streams from the high-level `asyncio` stream API
with an SSL context — so the pairing is *structural* and fires on every encrypted
channel close. `grep -rn eof_received bgp/` returns nothing: this warning is not
ours, is not caused by peer behavior, and requires no operator action.

Because the emitter is the standard library, no change to NetClaw's own connection
handling can prevent it. The alternative — implementing a custom `asyncio.Protocol`
to control `eof_received` — means rewriting the channel transport to silence one
cosmetic line, which is grossly disproportionate (research R5).

This module exists so the *narrowness* of the suppression is reviewable in one place.
FR-030 is explicit that the remedy must not suppress genuine warnings from the same
runtime, so the filter matches this one message and nothing else. Raising the
`asyncio` logger's level, or filtering by logger name alone, would hide real asyncio
warnings and is exactly what FR-030 forbids.
"""

import logging

# Matched as a substring of the formatted message. CPython has carried this exact
# wording since the warning was introduced; matching a distinctive fragment rather
# than the whole line keeps it robust to incidental punctuation changes while staying
# far too specific to catch anything else.
_EOF_RECEIVED_FRAGMENT = "returning true from eof_received() has no effect when using ssl"


class EofReceivedNoiseFilter(logging.Filter):
    """Drops only the TLS `eof_received` advisory. Everything else passes."""

    def filter(self, record: logging.LogRecord) -> bool:
        # getMessage() applies %-args, so the check works whether the caller passed a
        # pre-formatted string or a format string plus arguments.
        try:
            message = record.getMessage()
        except Exception:
            # A record we cannot even format is certainly not the one we are dropping;
            # let it through rather than silently discarding a malformed log call.
            return True
        return _EOF_RECEIVED_FRAGMENT not in message


def install(logger_name: str = "asyncio") -> EofReceivedNoiseFilter:
    """Attach the filter to the `asyncio` logger. Idempotent.

    Returns the filter instance so a caller (or a test) can remove it again.
    """
    target = logging.getLogger(logger_name)
    for existing in target.filters:
        if isinstance(existing, EofReceivedNoiseFilter):
            return existing
    f = EofReceivedNoiseFilter()
    target.addFilter(f)
    return f
