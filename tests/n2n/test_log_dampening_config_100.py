"""Feature 100 (T007): the dead-peer dampening configuration surface.

Guards two things the spec makes explicit:

1. **Defaults preserve today's behavior.** contracts/interfaces.md §1 fixes the six
   values; drifting one silently changes dial scheduling on every deployment.
2. **A malformed value must not stop the daemon booting.** These are read in
   `FederationService.__init__` during startup, so an `int()` that raises would turn a
   typo in `mesh.systemd.env` into a dead mesh (contracts §1.1).

Run under /usr/bin/python3 (3.14.4) — the interpreter netclaw-mesh.service executes.
"""

import os

import pytest

from bgp.federation.service import FederationService, _cause_sig, _env_int

DAMPEN_VARS = (
    "N2N_RECONNECT_DAMPEN",
    "N2N_RECONNECT_DEAD_CEILING_S",
    "N2N_RECONNECT_DEAD_AFTER",
    "N2N_RECONNECT_ENDPOINT_STALE_S",
    "N2N_RECONNECT_SUMMARY_INTERVAL_S",
    "N2N_RECONNECT_STABLE_AFTER_S",
)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove every dampening var so defaults are what is under test."""
    for name in DAMPEN_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _svc(manager):
    return FederationService(local_as=65001, router_id="4.4.4.4",
                             display_name="test", manager=manager)


# ── Defaults (contracts/interfaces.md §1) ─────────────────────────────────────

def test_defaults_match_the_contract(clean_env, manager):
    svc = _svc(manager)
    assert svc._dampen is True
    assert svc._dead_ceiling == 900        # ≈15 min, per clarification
    assert svc._dead_after == 20
    assert svc._endpoint_stale_s == 86400  # 24h
    assert svc._summary_interval == 300    # 5 min
    assert svc._stable_after == 120        # 2 min sustained uptime


def test_preexisting_backoff_defaults_unchanged(clean_env, manager):
    """FR-028/Constitution XV: the three pre-100 vars keep their meanings."""
    for name in ("N2N_RECONNECT_BACKOFF_MIN_S", "N2N_RECONNECT_BACKOFF_MAX_S",
                 "N2N_RECONNECT_UNREACHABLE_AFTER"):
        clean_env.delenv(name, raising=False)
    svc = _svc(manager)
    assert svc._backoff_min == 5
    assert svc._backoff_max == 60
    assert svc._unreachable_after == 5


# ── Overrides ─────────────────────────────────────────────────────────────────

def test_values_are_overridable(clean_env, manager):
    clean_env.setenv("N2N_RECONNECT_DEAD_CEILING_S", "1800")
    clean_env.setenv("N2N_RECONNECT_DEAD_AFTER", "3")
    clean_env.setenv("N2N_RECONNECT_STABLE_AFTER_S", "45")
    svc = _svc(manager)
    assert svc._dead_ceiling == 1800
    assert svc._dead_after == 3
    assert svc._stable_after == 45


def test_dampen_zero_is_a_bypass_flag(clean_env, manager):
    """FR-028 / SC-010: DAMPEN=0 must read as a complete bypass."""
    clean_env.setenv("N2N_RECONNECT_DAMPEN", "0")
    assert _svc(manager)._dampen is False


@pytest.mark.parametrize("truthy", ["1", "2", "-1"])
def test_any_nonzero_dampen_enables(clean_env, manager, truthy):
    clean_env.setenv("N2N_RECONNECT_DAMPEN", truthy)
    assert _svc(manager)._dampen is True


# ── Malformed input must never raise out of __init__ (contracts §1.1) ─────────

@pytest.mark.parametrize("bad", ["", "   ", "abc", "900s", "15m", "None", "9.5", "0x10"])
def test_malformed_values_fall_back_instead_of_raising(bad):
    assert _env_int("N2N_TEST_ONLY_VAR_100", 42) == 42, "unset must use the default"
    os.environ["N2N_TEST_ONLY_VAR_100"] = bad
    try:
        assert _env_int("N2N_TEST_ONLY_VAR_100", 42) == 42
    finally:
        del os.environ["N2N_TEST_ONLY_VAR_100"]


def test_service_still_constructs_with_garbage_env(clean_env, manager):
    """The regression that matters: a typo must not prevent the mesh from booting."""
    for name in DAMPEN_VARS:
        clean_env.setenv(name, "not-a-number")
    svc = _svc(manager)                     # must not raise
    assert svc._dead_ceiling == 900
    assert svc._dampen is True
    assert svc._stable_after == 120


def test_whitespace_is_tolerated(clean_env, manager):
    clean_env.setenv("N2N_RECONNECT_DEAD_AFTER", "  7  ")
    assert _svc(manager)._dead_after == 7


# ── Cause signature normalization (FR-015, data-model §1.3) ───────────────────

def test_cause_sig_ignores_addresses_and_ordering():
    """The live defect: six addresses in varying order must yield ONE signature.

    Verbatim comparison of the real cause strings reported a changed cause on nearly
    every attempt, which would defeat collapsing entirely (baseline.md).
    """
    a = OSError(111, "Connect call failed ('52.9.84.44', 24781)")
    b = OSError(111, "Connect call failed ('13.52.204.76', 24781)")
    # Note: CPython auto-specializes OSError(111, ...) to ConnectionRefusedError, so
    # the class half of the signature is already more discriminating than OSError.
    # What FR-015 requires is that these two COLLAPSE, which is what is asserted.
    assert _cause_sig(a) == _cause_sig(b)
    assert _cause_sig(a) == "ConnectionRefusedError:111"


def test_cause_sig_distinguishes_materially_different_causes():
    """FR-015: differing causes must NOT collapse into one another."""
    refused = OSError(111, "Connection refused")
    unreachable = OSError(113, "No route to host")
    assert _cause_sig(refused) != _cause_sig(unreachable)
    assert _cause_sig(TimeoutError()) != _cause_sig(refused)


def test_cause_sig_reaches_into_multiple_exceptions():
    """asyncio happy-eyeballs raises an ExceptionGroup-like carrier with no errno of
    its own; the signature must still discriminate rather than collapsing every
    multi-address failure to one opaque value."""
    grouped = OSError("Multiple exceptions: [Errno 111] ...")
    grouped.exceptions = (OSError(111, "refused"), OSError(111, "refused"))
    assert _cause_sig(grouped).endswith(":111")


def test_cause_sig_never_leaks_addresses():
    """FR-007-adjacent: the signature lands in logs, so it must carry no endpoint
    detail that a normalized signature has no business exposing."""
    exc = OSError(111, "Connect call failed ('52.9.84.44', 24781)")
    sig = _cause_sig(exc)
    assert "52.9.84.44" not in sig and "24781" not in sig


def test_cause_sig_handles_exception_without_errno():
    assert _cause_sig(ValueError("nope")) == "ValueError:"
