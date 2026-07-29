"""Regression: the edge WebSocket transport limit must not be smaller than the
protocol limit the client codes against.

`websockets.serve()` defaults `max_size` to 1 MiB and it was never set. But
`NCFED_MAX_MESSAGE` is 16 MiB, and the phone caps a capture at
`kMaxCaptureBytes` = 8 MiB of RAW bytes — which base64-encodes to ~10.7 MiB on
the wire. So every photo over roughly 768 KiB raw exceeded the transport limit
while both the protocol and the client considered it perfectly legal.

The failure mode was the worst kind: `websockets` closes the connection with
1009 (message too big), so the request failed AND the socket died — visually
indistinguishable from the reconnect churn already under investigation.

Found by cross-reviewing the iOS PR (#179) against the live Border: that PR
raised the client's attachment send timeout to 120s because a multi-MB base64
attachment can be slow, which is correct — and made it obvious the server had
never been configured to accept one.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "mcp-servers", "protocol-mcp"))

_DAEMON = os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers",
                       "protocol-mcp", "bgp-daemon-v2.py")
_CAPTURE_CLIENT = os.path.join(
    os.path.dirname(__file__), "..", "..", "mobile", "netclaw-mobile", "lib",
    "ncfed", "capture_client.dart")


def _daemon_src():
    with open(_DAEMON) as f:
        return f.read()


def _edge_serve_call():
    src = _daemon_src()
    i = src.index("websockets.serve(")
    return src[i:src.index(")", src.index("max_size", i))]


def test_edge_listener_sets_max_size_explicitly():
    """Relying on the library default is the bug."""
    assert "max_size" in _edge_serve_call(), (
        "websockets.serve() must set max_size — the 1 MiB default silently "
        "rejects legal attachments and kills the connection")


def test_transport_limit_equals_the_protocol_limit():
    from bgp.constants import NCFED_MAX_MESSAGE
    assert "NCFED_MAX_MESSAGE" in _edge_serve_call(), (
        "max_size should be tied to NCFED_MAX_MESSAGE, not a second hardcoded "
        "number that can drift from the protocol bound")
    assert NCFED_MAX_MESSAGE == 16 * 1024 * 1024


def test_transport_limit_admits_the_clients_largest_legal_capture():
    """The actual invariant: whatever the phone is allowed to capture must fit
    through the transport once base64 has inflated it."""
    from bgp.constants import NCFED_MAX_MESSAGE

    with open(_CAPTURE_CLIENT) as f:
        dart = f.read()
    m = re.search(r"kMaxCaptureBytes\s*=\s*([0-9]+)\s*\*\s*1024\s*\*\s*1024", dart)
    assert m, "could not read kMaxCaptureBytes from capture_client.dart"
    raw_cap = int(m.group(1)) * 1024 * 1024

    # base64 is 4 bytes out per 3 in, plus the surrounding JSON-RPC envelope.
    on_the_wire = raw_cap * 4 / 3
    assert on_the_wire <= NCFED_MAX_MESSAGE, (
        f"the phone may capture {raw_cap / 1048576:.1f} MiB, which is "
        f"{on_the_wire / 1048576:.1f} MiB base64-encoded, but the transport "
        f"admits only {NCFED_MAX_MESSAGE / 1048576:.1f} MiB")


def test_the_old_default_would_have_failed_this():
    """Documents the size of the gap that existed, so the numbers above are not
    mistaken for arbitrary."""
    websockets_default = 1024 * 1024
    raw_that_fits = websockets_default * 3 / 4
    assert raw_that_fits < 8 * 1024 * 1024, (
        "sanity: the 1 MiB default admitted only ~768 KiB of raw capture "
        "against an 8 MiB client allowance")


def test_keepalive_settings_survived_the_change():
    """max_size was added alongside the ping settings — neither may be lost."""
    call = _edge_serve_call()
    assert "ping_interval" in call
    assert "ping_timeout" in call
