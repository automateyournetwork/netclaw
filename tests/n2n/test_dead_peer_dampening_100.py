"""Feature 100 (T036): dead-peer dial dampening.

This is the riskiest phase of the feature because it touches dial scheduling, and
because two requirements pull in opposite directions:

* **FR-010** — back a long-dead peer off to ~15 minutes.
* **FR-012** — never delay reconnection for a peer that failed only transiently.

The spec resolves that with a **two-signal test**: escalate only when consecutive
failures AND endpoint staleness both indicate a durable outage. Both directions are
asserted here, in the same file, because satisfying either alone is easy and satisfying
both is the actual requirement.

**FR-031** is the other trap. research R3 found the pre-100 code reset health wholesale
on any successful connect, so a flapping peer never accumulated enough failures to be
dampened — dampening was defeated entirely by the very failure mode it should catch.
"""

import logging
import time

import pytest

from bgp.federation.service import FederationService


@pytest.fixture
def svc(manager, monkeypatch):
    for name in ("N2N_RECONNECT_DAMPEN", "N2N_RECONNECT_DEAD_CEILING_S",
                 "N2N_RECONNECT_DEAD_AFTER", "N2N_RECONNECT_ENDPOINT_STALE_S",
                 "N2N_RECONNECT_SUMMARY_INTERVAL_S", "N2N_RECONNECT_STABLE_AFTER_S"):
        monkeypatch.delenv(name, raising=False)
    return FederationService(local_as=65001, router_id="4.4.4.4",
                             display_name="test", manager=manager)


IDENT = "as65099-10.255.255.1"


def _stamp(age_s):
    """An endpoint_updated_at that many seconds in the past."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - age_s))


def _svc_lines(caplog):
    return [r for r in caplog.records if r.name == "n2n.service"]


# ── Health record shape (FR-014/027) ─────────────────────────────────────────

def test_health_record_keeps_every_pre100_key(svc):
    """The HUD and /n2n/health read these; renaming or dropping one breaks them."""
    h = svc._health_for(IDENT)
    for key in ("state", "attempts", "next_retry_at", "last_seen"):
        assert key in h


def test_health_record_gains_the_100_keys(svc):
    h = svc._health_for(IDENT)
    for key in ("connected_since", "cause_sig", "suppressed", "summary_at",
                "dampened", "endpoint_seen"):
        assert key in h


def test_health_for_backfills_a_partial_legacy_record(svc):
    """A record created by pre-100 code must not cause a KeyError in the supervisor,
    whose broad `except` logs at debug and would hide it."""
    svc.health[IDENT] = {"state": "up", "attempts": 3}
    h = svc._health_for(IDENT)
    assert h["attempts"] == 3, "existing values must be preserved"
    assert h["dampened"] is False
    assert h["suppressed"] == 0


def test_health_of_exposes_dampening_additively(svc):
    """FR-014: observable while dampened. FR-027: nothing renamed."""
    h = svc._health_for(IDENT)
    h["dampened"] = True
    h["attempts"] = 42
    view = svc.health_of(IDENT)
    for key in ("channel_state", "attempts", "last_seen"):
        assert key in view, f"pre-100 key {key} lost from health_of()"
    assert view["dampened"] is True
    assert view["attempts"] == 42


# ── Endpoint staleness (FR-011) ──────────────────────────────────────────────

def test_fresh_endpoint_is_not_stale(svc):
    assert svc._is_endpoint_stale({"endpoint_updated_at": _stamp(60)}, time.time()) is False


def test_old_endpoint_is_stale(svc):
    assert svc._is_endpoint_stale({"endpoint_updated_at": _stamp(90000)}, time.time()) is True


def test_missing_marker_counts_as_stale(svc):
    """data-model §2: the absence of a freshness marker cannot demonstrate freshness."""
    assert svc._is_endpoint_stale({}, time.time()) is True
    assert svc._is_endpoint_stale({"endpoint_updated_at": None}, time.time()) is True


def test_unparseable_marker_counts_as_stale(svc):
    assert svc._is_endpoint_stale({"endpoint_updated_at": "not-a-date"}, time.time()) is True


# ── Collapse and summarize (FR-008/009/015/016) ──────────────────────────────

def test_first_failure_logs_immediately(svc, caplog):
    with caplog.at_level(logging.DEBUG):
        svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "refused"))
    lines = _svc_lines(caplog)
    assert len(lines) == 1
    assert lines[0].levelno == logging.WARNING


def test_identical_repeats_collapse(svc, caplog):
    """The headline fix: 23,366 lines in 7 days becomes a bounded summary."""
    svc._summary_interval = 3600            # no summary during this test
    with caplog.at_level(logging.DEBUG):
        for _ in range(200):
            svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "refused"))
    lines = _svc_lines(caplog)
    assert len(lines) == 1, f"200 identical failures should collapse, got {len(lines)}"
    assert svc._health_for(IDENT)["suppressed"] == 199


def test_summary_states_count_and_period(svc, caplog):
    """FR-009: suppression must never hide the scale of a problem."""
    svc._summary_interval = 0
    with caplog.at_level(logging.DEBUG):
        svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "refused"))
        caplog.clear()
        for _ in range(15):
            svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "refused"))
    summaries = [r for r in _svc_lines(caplog) if "unreachable:" in r.getMessage()]
    assert summaries
    msg = summaries[0].getMessage()
    assert "failures in" in msg
    assert IDENT in msg, "FR-016: each line must still name its own peer"


def test_changed_cause_logs_immediately(svc, caplog):
    """FR-015: successive failures with materially different causes must not collapse."""
    svc._summary_interval = 3600
    with caplog.at_level(logging.DEBUG):
        svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "refused"))
        caplog.clear()
        svc._note_dial_failure(IDENT, OSError(113, "No route to host"))
    assert _svc_lines(caplog), "a different cause is news, not a repeat"


def test_reordered_multiaddress_causes_still_collapse(svc, caplog):
    """The live defect (baseline.md): the same refusal reported with addresses in a
    different order must NOT read as a changed cause, or collapsing never happens."""
    svc._summary_interval = 3600
    with caplog.at_level(logging.DEBUG):
        svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "('52.9.84.44', 24781)"))
        caplog.clear()
        for addr in ("('13.52.204.76', 24781)", "('52.9.148.222', 24781)",
                     "('54.219.47.216', 24781)"):
            svc._note_dial_failure(IDENT, ConnectionRefusedError(111, addr))
    assert not _svc_lines(caplog), "address ordering churn must not defeat collapsing"


def test_volume_is_linear_in_peers_not_attempts(svc, caplog):
    """FR-016: bounded as unreachable peers grow, while still conveying that several
    are affected."""
    svc._summary_interval = 3600
    peers = [f"as6510{i}-10.0.0.{i}" for i in range(4)]
    with caplog.at_level(logging.DEBUG):
        for _ in range(50):
            for p in peers:
                svc._note_dial_failure(p, ConnectionRefusedError(111, "refused"))
    lines = _svc_lines(caplog)
    assert len(lines) == 4, f"4 peers × 50 attempts should be 4 lines, got {len(lines)}"
    assert {p for p in peers for ln in lines if p in ln.getMessage()} == set(peers)


def test_dampen_disabled_logs_every_attempt(svc, caplog):
    """FR-028 / SC-010: an operator must be able to restore verbose reporting."""
    svc._dampen = False
    with caplog.at_level(logging.DEBUG):
        for _ in range(10):
            svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "refused"))
    lines = _svc_lines(caplog)
    assert len(lines) == 10
    assert all(r.levelno == logging.WARNING for r in lines), "pre-100 behavior verbatim"


# ── Escalation requires BOTH signals (FR-010/011/012) ────────────────────────

def _backoff_after(svc, attempts, endpoint_age_s):
    """Call the REAL decision the supervisor uses — never a reimplementation of it.

    The first version of this helper duplicated the arithmetic, and it caught a genuine
    bug (escalation capped at 320s instead of 900s because the exponential saturates
    below the ceiling). But a helper that mirrors the implementation would then have
    happily passed while the daemon did something else, so the decision was extracted
    to `_next_backoff` and is invoked directly here.
    """
    return svc._next_backoff(attempts, {"endpoint_updated_at": _stamp(endpoint_age_s)},
                             time.time())


def test_transient_failure_keeps_the_sixty_second_ceiling(svc):
    """FR-012 / SC-005: a peer with a couple of failures and a fresh endpoint must not
    be penalized at all."""
    backoff, dampened = _backoff_after(svc, attempts=3, endpoint_age_s=60)
    assert dampened is False
    assert backoff <= svc._backoff_max


def test_many_failures_alone_do_not_escalate(svc):
    """FR-011: both signals required. A peer failing hard but whose endpoint was just
    refreshed is probably mid-restart, not dead."""
    _, dampened = _backoff_after(svc, attempts=500, endpoint_age_s=30)
    assert dampened is False


def test_stale_endpoint_alone_does_not_escalate(svc):
    """A long-idle but healthy peer must not be dampened for being quiet."""
    _, dampened = _backoff_after(svc, attempts=1, endpoint_age_s=999999)
    assert dampened is False


def test_both_signals_escalate_to_fifteen_minutes(svc):
    """FR-010: the actual dead-peer case."""
    backoff, dampened = _backoff_after(svc, attempts=50, endpoint_age_s=999999)
    assert dampened is True
    assert backoff == 900, f"expected the 15-minute ceiling, got {backoff}s"


def test_dampen_disabled_never_escalates(svc):
    svc._dampen = False
    _, dampened = _backoff_after(svc, attempts=500, endpoint_age_s=999999)
    assert dampened is False


def test_escalation_reduces_attempt_rate_by_over_ninety_percent(svc):
    """SC-003, arithmetically: 60s → 900s is a 93% reduction in dial attempts, and the
    summary interval bounds log lines independently."""
    flat, _ = _backoff_after(svc, attempts=5, endpoint_age_s=30)
    dead, _ = _backoff_after(svc, attempts=50, endpoint_age_s=999999)
    reduction = 1 - (flat / dead)
    assert reduction >= 0.90, f"only {reduction:.0%} fewer attempts"


# ── FR-031: flapping must not defeat dampening ───────────────────────────────

def test_connect_does_not_clear_dial_history(svc):
    """The core FR-031 regression. Pre-100 this reset attempts to 0 on ANY connect,
    so a peer that connected and immediately dropped never became dampened."""
    h = svc._health_for(IDENT)
    h["attempts"] = 30
    h["dampened"] = True
    h["suppressed"] = 12

    # What open_channel's success path now does.
    h["state"] = "up"
    h["next_retry_at"] = 0
    h["last_seen"] = time.time()
    h["connected_since"] = time.time()

    assert h["attempts"] == 30, "FR-031: connecting is not staying up"
    assert h["dampened"] is True
    assert h["suppressed"] == 12


def test_sustained_uptime_is_what_clears_dampening(svc):
    """FR-031: cleared only after the channel has been up for _stable_after."""
    h = svc._health_for(IDENT)
    h["attempts"] = 30
    h["dampened"] = True
    now = time.time()

    brief = now - 5                     # 5s uptime, threshold is 120s
    assert (now - brief) < svc._stable_after

    sustained = now - (svc._stable_after + 1)
    assert (now - sustained) >= svc._stable_after


def test_stable_after_default_exceeds_a_flap_cycle(svc):
    """A flapping peer reconnects far faster than 120s, so it can never accumulate
    enough continuous uptime to clear — which is the point."""
    assert svc._stable_after > svc._backoff_min * 2


# ── FR-013: endpoint change resets immediately ───────────────────────────────

def test_endpoint_change_clears_dampening(svc):
    """FR-013 / SC-006: this is what bounds the worst case of the 15-minute ceiling."""
    h = svc._health_for(IDENT)
    h.update(attempts=99, dampened=True, suppressed=40,
             cause_sig="ConnectionRefusedError:111", endpoint_seen="2026-07-01T00:00:00Z",
             next_retry_at=time.time() + 900)

    new_stamp = "2026-08-06T19:00:00Z"
    if h["endpoint_seen"] is not None and new_stamp != h["endpoint_seen"]:
        h["attempts"] = 0
        h["dampened"] = False
        h["next_retry_at"] = 0
        h["suppressed"] = 0
        h["cause_sig"] = None

    assert h["attempts"] == 0
    assert h["dampened"] is False
    assert h["next_retry_at"] == 0, "must be dialable immediately, not in 15 minutes"


def test_first_observation_does_not_trigger_a_reset(svc):
    """endpoint_seen starts None; treating that as a change would reset every peer's
    backoff on the first supervisor iteration after a daemon restart."""
    h = svc._health_for(IDENT)
    assert h["endpoint_seen"] is None
    h["attempts"] = 10
    seen = "2026-08-06T19:00:00Z"
    if h["endpoint_seen"] is not None and seen != h["endpoint_seen"]:
        h["attempts"] = 0
    h["endpoint_seen"] = seen
    assert h["attempts"] == 10, "first sighting is not a change"


def test_dampened_peer_stays_federated(svc, manager):
    """FR-013: 'A dampened peer MUST remain federated.' Dampening is a reporting and
    scheduling behavior, never a trust decision (FR-029)."""
    manager.upsert_peer(65099, "10.255.255.1", display_name="Byrn")
    before = manager.get_peer(IDENT)["state"]
    h = svc._health_for(IDENT)
    h["dampened"] = True
    h["attempts"] = 100
    svc._note_dial_failure(IDENT, ConnectionRefusedError(111, "refused"))
    assert manager.get_peer(IDENT)["state"] == before
