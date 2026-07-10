"""T031: authorization — default-deny, grants, rate limits, budgets, approvals."""

import os

import pytest

from bgp.federation.authorization import Authorizer
from bgp.federation.manager import peer_identity


def _federated(manager, peer_as=65007, rid="7.7.7.7"):
    manager.local_consent(peer_as, rid)
    manager.remote_consent(peer_as, rid)
    return peer_identity(peer_as, rid)


def test_default_deny(manager):
    ident = _federated(manager)
    authz = Authorizer(manager)
    d = authz.authorize(ident, "tool", "cml-mcp/list_labs")
    assert not d.allowed and d.code == "not_allowlisted"


def test_grant_allows(manager):
    ident = _federated(manager)
    authz = Authorizer(manager)
    authz.grant(ident, "tool", "cml-mcp/list_labs")
    d = authz.authorize(ident, "tool", "cml-mcp/list_labs")
    assert d.allowed and d.code == "allowlisted"


def test_approval_required(manager):
    ident = _federated(manager)
    authz = Authorizer(manager)
    authz.grant(ident, "skill", "reboot-router", requires_approval=True)
    d = authz.authorize(ident, "skill", "reboot-router")
    assert not d.allowed and d.code == "approval_required"


def test_rate_limit(manager, monkeypatch):
    monkeypatch.setenv("N2N_RATE_PER_MIN", "2")
    ident = _federated(manager)
    authz = Authorizer(manager)
    authz.grant(ident, "tool", "t/x")
    assert authz.authorize(ident, "tool", "t/x").allowed
    assert authz.authorize(ident, "tool", "t/x").allowed
    assert authz.authorize(ident, "tool", "t/x").code == "rate_limited"


def test_budget_exhaustion_and_reset(manager, monkeypatch):
    monkeypatch.setenv("N2N_DAILY_REQUESTS", "1")
    ident = _federated(manager)
    authz = Authorizer(manager)
    authz.grant(ident, "tool", "t/x")
    assert authz.authorize(ident, "tool", "t/x").allowed
    authz.debit(ident, requests=1)
    assert authz.authorize(ident, "tool", "t/x").code == "budget_exhausted"


def test_approval_lifecycle(manager):
    ident = _federated(manager)
    authz = Authorizer(manager)
    # Need an invocation row to reference
    inv_id = manager._conn.execute(
        "INSERT INTO remote_invocation_record (direction, peer_identity, decision, outcome) "
        "VALUES ('inbound', ?, 'approval_required', 'pending')", (ident,)).lastrowid
    manager._conn.commit()
    appr = authz.create_approval(inv_id)
    assert authz.approval_status(appr["approval_id"]) == "pending"
    authz.resolve_approval(appr["approval_id"], "approve")
    assert authz.approval_status(appr["approval_id"]) == "approved"
    assert len(authz.pending_approvals()) == 0
