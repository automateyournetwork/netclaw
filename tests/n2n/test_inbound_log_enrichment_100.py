"""Feature 100 (T021/T022): the enriched inbound-call log line.

Scope note carried from research R2: inbound calls were **already** logged at info with
peer, target, decision and outcome. The original spec premise ("inbound calls log almost
nothing") was wrong. So FR-001/002/004 are *regression guards* here — the risk is losing
them while enriching the same line — and only FR-003 (denial severity), FR-005 (`req=`),
FR-032 (no second line) and FR-033 (arrival) are new behavior.

The 2026-08-06 incident is the reason FR-032 is tested: every inbound handler routes
every decision branch through Auditor.record(), so a duplicate logging call would double
the log for 8+ handlers at once.
"""

import logging

import pytest

from bgp.federation.audit import _ACTIONABLE_OUTCOMES, Auditor
from bgp.federation.channel import _ARRIVAL_QUIET_METHODS


@pytest.fixture
def auditor(manager):
    manager.upsert_peer(65006, "6.6.6.6", display_name="Nate")
    return Auditor(manager)


def _audit_lines(caplog):
    return [r for r in caplog.records if r.name == "n2n.audit"]


def _record(auditor, **kw):
    base = dict(direction="inbound", peer_identity="as65006-6.6.6.6",
                target_type="tool", target_name="show_version",
                decision="allowlisted", outcome="success")
    base.update(kw)
    return auditor.record(**base)


# ── FR-005: request_id must reach the log ─────────────────────────────────────

def test_request_id_appears_in_the_log_line(auditor, caplog):
    with caplog.at_level(logging.INFO):
        _record(auditor, request_id="a1b2c3d4e5f6g7h8")
    msg = _audit_lines(caplog)[0].getMessage()
    assert "req=a1b2c3d4e5" in msg, f"FR-005: request_id must be joinable: {msg}"


def test_request_id_truncated_to_ten_chars(auditor, caplog):
    """Matches the existing gait=[:10] convention."""
    with caplog.at_level(logging.INFO):
        _record(auditor, request_id="0123456789ABCDEF")
    assert "req=0123456789 " in _audit_lines(caplog)[0].getMessage() + " "


def test_req_token_omitted_when_absent(auditor, caplog):
    """Absent request_id must not render 'req=None' — mirrors how gait= is handled."""
    with caplog.at_level(logging.INFO):
        _record(auditor, request_id=None)
    msg = _audit_lines(caplog)[0].getMessage()
    assert "req=" not in msg
    assert "None" not in msg


def test_logged_req_prefix_matches_the_persisted_row(auditor, caplog):
    """SC-001/002: the log alone must be joinable to the audit row without guesswork."""
    with caplog.at_level(logging.INFO):
        _record(auditor, request_id="deadbeefcafe1234")
    row = auditor.recent(limit=1)[0]
    logged = [t for t in _audit_lines(caplog)[0].getMessage().split()
              if t.startswith("req=")][0].removeprefix("req=")
    assert row["request_id"].startswith(logged)


# ── FR-003: denial severity ───────────────────────────────────────────────────

@pytest.mark.parametrize("outcome", sorted(_ACTIONABLE_OUTCOMES))
def test_actionable_outcomes_emit_at_warning(auditor, caplog, outcome):
    with caplog.at_level(logging.INFO):
        _record(auditor, outcome=outcome, decision="not_allowlisted")
    assert _audit_lines(caplog)[0].levelno == logging.WARNING, (
        f"FR-003: outcome={outcome} must be isolable by severity alone")


@pytest.mark.parametrize("outcome", ["success", "pending", "submitted"])
def test_routine_outcomes_stay_info(auditor, caplog, outcome):
    with caplog.at_level(logging.INFO):
        _record(auditor, outcome=outcome)
    assert _audit_lines(caplog)[0].levelno == logging.INFO


def test_denied_is_separable_from_success_by_level_alone(auditor, caplog):
    """The operator gesture this enables: journalctl -p warning | grep 'AUDIT['."""
    with caplog.at_level(logging.INFO):
        _record(auditor, outcome="success", request_id="ok1")
        _record(auditor, outcome="denied", decision="not_allowlisted", request_id="no1")
    warnings = [r for r in _audit_lines(caplog) if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "denied" in warnings[0].getMessage()


def test_every_denial_decision_reaches_warning_via_outcome(auditor, caplog):
    """data-model §3.1: keying off `outcome` rather than `decision` is what makes the
    growing list of refusal reasons a non-issue."""
    for decision in ("not_allowlisted", "approval_required", "not_found",
                     "out_of_scope", "guardrail_blocked"):
        caplog.clear()
        with caplog.at_level(logging.INFO):
            _record(auditor, decision=decision, outcome="denied")
        assert _audit_lines(caplog)[0].levelno == logging.WARNING, decision


# ── FR-032: exactly one line per audit write ──────────────────────────────────

def test_exactly_one_line_per_record_call(auditor, caplog):
    with caplog.at_level(logging.DEBUG):
        _record(auditor, request_id="single")
    assert len(_audit_lines(caplog)) == 1, (
        "FR-032: the existing line is enriched in place; a parallel logger would "
        "double the log across all 8+ inbound handlers")


def test_volume_scales_one_to_one_with_records(auditor, caplog):
    with caplog.at_level(logging.DEBUG):
        for i in range(5):
            _record(auditor, request_id=f"r{i}")
    assert len(_audit_lines(caplog)) == 5


# ── FR-001/002/004 regression guards (already satisfied pre-100) ──────────────

def test_existing_fields_all_survive_enrichment(auditor, caplog):
    with caplog.at_level(logging.INFO):
        _record(auditor, target_type="skill", target_name="cml-lab-lifecycle",
                decision="allowlisted", outcome="success", request_id="keepme",
                channel_kind="in2n")
    msg = _audit_lines(caplog)[0].getMessage()
    for token in ("AUDIT[in2n]", "inbound", "as65006-6.6.6.6",
                  "skill/cml-lab-lifecycle", "allowlisted", "success"):
        assert token in msg, f"regression: {token!r} lost from the audit line"


def test_audit_prefix_and_field_order_unchanged(auditor, caplog):
    """Anything grepping 'AUDIT[' must keep working (contracts §5.2)."""
    with caplog.at_level(logging.INFO):
        _record(auditor, request_id="ordercheck")
    msg = _audit_lines(caplog)[0].getMessage()
    assert msg.startswith("AUDIT[en2n] inbound as65006-6.6.6.6 tool/show_version → ")
    # req= must precede gait= when both are present.
    if "gait=" in msg:
        assert msg.index("req=") < msg.index("gait=")


def test_audit_row_still_written_completely(auditor):
    """SC-009: audit completeness unchanged — logging changes must not touch the row."""
    _record(auditor, request_id="rowcheck", target_type="tool", target_name="ping")
    row = auditor.recent(limit=1)[0]
    for col in ("direction", "peer_identity", "target_type", "target_name",
                "request_id", "decision", "outcome", "requested_at", "completed_at"):
        assert row[col] is not None, f"SC-009: {col} lost from the audit row"


# ── FR-003 second clause: denials can never be dampened ──────────────────────

def test_auditor_has_no_dampening_surface(auditor, caplog):
    """FR-003: 'MUST NOT allow denials to be suppressed by any noise-dampening
    behavior'. Structural: the Auditor reads no dampening state at all, so repeated
    identical denials each produce their own line."""
    for name in dir(auditor):
        assert "dampen" not in name.lower()
        assert "suppress" not in name.lower()

    with caplog.at_level(logging.INFO):
        for i in range(10):
            _record(auditor, outcome="denied", decision="not_allowlisted",
                    request_id=f"dny{i}")
    warnings = [r for r in _audit_lines(caplog) if r.levelno == logging.WARNING]
    assert len(warnings) == 10, "identical denials must never collapse"


# ── FR-007: no secrets ────────────────────────────────────────────────────────

def test_arguments_are_never_logged(auditor, caplog):
    """The audit line takes target *names*, not argument values — record() has no
    parameter through which a payload could reach the log."""
    import inspect
    params = inspect.signature(auditor.record).parameters
    for leaky in ("arguments", "params", "payload", "body", "result", "token",
                  "secret", "credential"):
        assert leaky not in params, f"FR-007: record() must not accept {leaky!r}"


# ── FR-033: arrival event ─────────────────────────────────────────────────────

def test_routine_chatter_is_excluded_from_arrival_logging():
    """n2n/heartbeat fires on a timer; logging its arrival would swamp the signal this
    feature exists to surface."""
    assert "n2n/heartbeat" in _ARRIVAL_QUIET_METHODS
    assert "n2n/hello" in _ARRIVAL_QUIET_METHODS
    assert "n2n/inventory" in _ARRIVAL_QUIET_METHODS


def test_capability_methods_are_not_excluded():
    """A denylist means a newly added capability method gets arrival visibility
    automatically — the point of choosing a denylist over an allowlist."""
    for method in ("n2n/tools/call", "n2n/tasks/submit", "n2n/knowledge/query",
                   "n2n/chat/message", "n2n/some/future/capability"):
        assert method not in _ARRIVAL_QUIET_METHODS
