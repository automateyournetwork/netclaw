"""A platform push is a wake signal, not a delivery (spec 106).

Reported from production 2026-08-13: the operator saw notifications arrive on a
real iPhone, tapped into the app, and found an empty feed. The Border reported
`queued=0` and logged no `Replaying` line, because the content had never been
written down anywhere.

Two independent loss paths in the POST /n2n/edge/push route caused it:

  1. A successful platform push RETURNED, without enqueueing. But a push
     notification only draws the OS banner. The sole writer to the phone's
     MessageFeedStore is the WS handler for `n2n/edge/message` — nothing on the
     device persists an FCM data payload, and the notification-tap handler only
     *searches* the store for an already-persisted match. So the content was
     lost between the two tiers.

  2. Only `ValueError` fell through to the fallback. `push_to_edge` raises
     ValueError just for "not connected"; a channel that exists but whose device
     is suspended raises `RpcError(ERR_EXECUTION_TIMEOUT)` after the 30s call
     timeout, and a closed socket raises a websockets error. Both escaped as a
     500 with no push and no queue — the common case for iOS, which holds a
     registered channel for seconds after backgrounding.

These are source-level assertions because bgp-daemon-v2.py is a script, not an
importable module — the same convention as test_member_liveness_shared.py and
test_edge_ws_frame_size.py. Weaker than a behavioural test, but sufficient to
pin the specific regressions, and the route's tiering had no coverage at all
before this, which is why the bug shipped.
"""

import os

_DAEMON = os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers",
                       "protocol-mcp", "bgp-daemon-v2.py")


def _push_route_src():
    """Just the POST /n2n/edge/push handler body."""
    with open(_DAEMON) as f:
        src = f.read()
    start = src.index('if path == "/n2n/edge/push" and method == "POST":')
    # The next route registration ends this one.
    end = src.index('return 404, {"error": f"unknown n2n route {path}"}', start)
    return src[start:end]


def test_successful_platform_push_also_persists_for_replay():
    """The reported bug: a banner counted as delivery and nothing was queued."""
    route = _push_route_src()
    via_push = route.index('"via": "push_notification"')
    # Walk back to the enclosing success path and require a persist before it.
    before = route[:via_push]
    assert "_persist(" in before, (
        "the successful push-notification path must enqueue for replay — a push "
        "notification only wakes the device, it does not put content in the app. "
        "Without this the message is lost between tiers 2 and 3.")


def test_push_success_reports_in_app_delivery_as_pending():
    """A caller must be able to tell a banner-only wake from real delivery."""
    route = _push_route_src()
    assert '"in_app_delivery": "pending_replay"' in route, (
        'a push-notification response claiming {"delivered": true} without '
        'qualification is what made this bug invisible to callers')


def test_live_delivery_failure_falls_through_instead_of_500ing():
    """A registered-but-suspended device must not lose the message."""
    route = _push_route_src()
    assert "except ValueError" in route, "the not-connected tier must still exist"
    assert "except Exception" in route, (
        "push_to_edge raises RpcError(ERR_EXECUTION_TIMEOUT) on a call timeout "
        "and a websockets error on a closed socket — neither is a ValueError, so "
        "catching only ValueError sends both to the outer handler as a 500 with "
        "no push and no queue")
    # The fallback must be reachable from the broad catch, i.e. the push_notify
    # import cannot be nested inside the ValueError branch any more.
    assert route.index("except Exception") < route.index("send_push_notification"), (
        "the broad catch must precede the fallback so a live-delivery failure "
        "reaches the platform push and the queue")


def test_enqueue_failure_cannot_500_a_successful_push():
    """Bookkeeping must not convert a delivered push into an error."""
    route = _push_route_src()
    persist = route[route.index("def _persist("):]
    assert "except Exception" in persist[:persist.index("return 200")], (
        "_persist must swallow and log an enqueue failure — the push already "
        "left the Border, so raising here would report failure for a message "
        "that was in fact sent")
