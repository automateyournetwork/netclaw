"""Regression: a phone request must never be killed while its own delegation
is still legitimately running.

`_edge_on_ask` called `gateway.run_agent_turn()` without `timeout_s`, so it
inherited the 300s default — while a member it delegates to gets
`skill_timeout` (default 600s). The INNER budget was twice the OUTER one, so a
delegating phone request was allowed to outlive the request that started it.

Observed twice on a real device (2026-07-26): identical CML questions failed at
exactly 300s while their `cml-node-operations` delegation completed
*afterwards* — the work succeeded and the answer had nowhere to land. A third,
warm-cache run finished in 114s and looked fine, which is the worst failure
profile: passes on retry, fails cold.
"""
import os
import sys
import types
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "mcp-servers", "protocol-mcp"))


def _service_with(skill_timeout=600, env=None):
    """A bare FederationService-like object exposing only what the budget
    helpers touch — this is a units-of-arithmetic test, not an integration one.
    """
    from bgp.federation.service import FederationService
    svc = object.__new__(FederationService)
    svc.invoker = types.SimpleNamespace(skill_timeout=skill_timeout)
    return svc


def test_phone_budget_exceeds_the_member_budget_it_may_wait_on(monkeypatch):
    monkeypatch.delenv("N2N_EDGE_ASK_TIMEOUT_S", raising=False)
    monkeypatch.delenv("N2N_EDGE_ASK_STALL_EXTENSION_S", raising=False)
    svc = _service_with(skill_timeout=600)

    budget = svc._edge_ask_timeout()

    assert budget > 600, (
        "the phone's turn must outlast the member turn it delegates into; "
        f"got {budget}s for a 600s member budget")
    # And it must be a real improvement on the old inherited default.
    assert budget > 300


def test_budget_tracks_a_raised_member_timeout(monkeypatch):
    """Raising the member budget must raise the phone budget with it —
    otherwise the same inversion silently returns."""
    monkeypatch.delenv("N2N_EDGE_ASK_TIMEOUT_S", raising=False)
    monkeypatch.delenv("N2N_EDGE_ASK_STALL_EXTENSION_S", raising=False)

    for member_budget in (300, 600, 1200, 3600):
        svc = _service_with(skill_timeout=member_budget)
        assert svc._edge_ask_timeout() > member_budget, (
            f"inversion returned at skill_timeout={member_budget}")


def test_explicit_override_wins(monkeypatch):
    monkeypatch.setenv("N2N_EDGE_ASK_TIMEOUT_S", "900")
    svc = _service_with(skill_timeout=600)
    assert svc._edge_ask_timeout() == 900


def test_override_is_floored_not_trusted_blindly(monkeypatch):
    """A nonsensically small override would reintroduce the original bug in a
    worse form; floor it instead of honouring it."""
    monkeypatch.setenv("N2N_EDGE_ASK_TIMEOUT_S", "1")
    svc = _service_with(skill_timeout=600)
    assert svc._edge_ask_timeout() >= 60


def test_garbage_override_falls_back_instead_of_crashing(monkeypatch):
    monkeypatch.setenv("N2N_EDGE_ASK_TIMEOUT_S", "not-a-number")
    monkeypatch.delenv("N2N_EDGE_ASK_STALL_EXTENSION_S", raising=False)
    svc = _service_with(skill_timeout=600)
    # Falls through to the derived value rather than raising ValueError inside
    # a live phone request.
    assert svc._edge_ask_timeout() > 600


def test_stall_extension_has_a_sane_floor(monkeypatch):
    monkeypatch.setenv("N2N_EDGE_ASK_STALL_EXTENSION_S", "0")
    svc = _service_with()
    assert svc._edge_ask_timeout.__self__ is svc  # bound, sanity
    assert svc._edge_ask_stall_extension() >= 30


def test_task_progress_is_a_declared_edge_method():
    """The stall notification rides a declared method — an undeclared one would
    be dropped by EdgeChannel's own EDGE_METHODS filter."""
    from bgp.federation.edge import EDGE_METHODS
    assert "n2n/edge/task_progress" in EDGE_METHODS


@pytest.mark.parametrize("method", [
    "n2n/edge/ask", "n2n/edge/ask_result", "n2n/tasks/status",
    "n2n/tasks/result", "n2n/tasks/cancel",
])
def test_existing_edge_surface_is_unchanged(method):
    """Adding task_progress must not disturb the existing command channel."""
    from bgp.federation.edge import EDGE_METHODS
    assert method in EDGE_METHODS
