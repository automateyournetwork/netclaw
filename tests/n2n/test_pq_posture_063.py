"""Feature 063 / US4 (P4): PQ posture + honest KEX visibility.

The reference host (Python 3.10 / OpenSSL 3.0.2) cannot offer the X25519MLKEM768
hybrid nor read the negotiated group. These tests prove the daemon is HONEST about
that: opportunistic is the unchanged default, `require` fails fast at startup on a
non-PQ stack (never silently refuses every peer), the KEX readout degrades without
crashing, and a classical group is never mislabeled PQ.
"""

import pytest

from bgp.federation import tls
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager


def _svc(tmp_path):
    return FederationService(local_as=65001, router_id="4.4.4.4", display_name="A",
                             manager=FederationManager(base_dir=str(tmp_path)))


# ---- capability probes are honest on this stack -----------------------------

def test_stack_probes_are_false_here():
    # On OpenSSL 3.0.2 / Python 3.10 neither PQ nor ECH is available.
    assert tls.pq_available() is False
    assert tls.ech_available() is False


def test_is_pq_group_classifies_conservatively():
    assert tls.is_pq_group("X25519MLKEM768") is True
    assert tls.is_pq_group("x25519_kyber768") is True
    assert tls.is_pq_group("x25519") is False
    assert tls.is_pq_group(None) is False   # unreadable is NOT treated as PQ


# ---- posture knob -----------------------------------------------------------

def test_opportunistic_is_default(tmp_path, monkeypatch):
    monkeypatch.delenv("N2N_PQ_MODE", raising=False)
    s = _svc(tmp_path)
    assert s.pq_mode == "opportunistic"
    assert s.pq_available is False


def test_require_fails_fast_on_non_pq_stack(tmp_path, monkeypatch):
    monkeypatch.setenv("N2N_PQ_MODE", "require")
    with pytest.raises(RuntimeError, match="post-quantum"):
        _svc(tmp_path)


# ---- KEX readout degrades without crashing ----------------------------------

class _FakeSSL:
    def version(self):
        return "TLSv1.3"

    def cipher(self):
        return ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)
    # no `group` attribute → mirrors Python 3.10


def test_channel_kex_reads_version_cipher_group_none():
    k = tls.channel_kex(_FakeSSL())
    assert k["tls_version"] == "TLSv1.3"
    assert k["cipher"] == "TLS_AES_256_GCM_SHA384"
    assert k["kex_group"] is None   # not readable on this stack, honest


# ---- require-mode enforcement (logic exercised on a simulated PQ stack) ------

def test_pq_ok_noop_when_stack_cannot_do_pq(tmp_path, monkeypatch):
    monkeypatch.delenv("N2N_PQ_MODE", raising=False)
    s = _svc(tmp_path)
    s.pq_mode = "require"          # set post-construction; stack still can't do PQ
    s.pq_available = False
    assert s._pq_ok(_FakeSSL(), "as65007-7.7.7.7") is True  # degrade, don't break


class _PQGroupSSL(_FakeSSL):
    group = "X25519MLKEM768"


def test_pq_ok_accepts_pq_and_refuses_classical_on_capable_stack(tmp_path, monkeypatch):
    monkeypatch.delenv("N2N_PQ_MODE", raising=False)
    s = _svc(tmp_path)
    s.pq_mode = "require"
    s.pq_available = True          # simulate a PQ-capable stack
    assert s._pq_ok(_PQGroupSSL(), "as65007-7.7.7.7") is True     # negotiated PQ → ok
    assert s._pq_ok(_FakeSSL(), "as65007-7.7.7.7") is False        # classical → refused
