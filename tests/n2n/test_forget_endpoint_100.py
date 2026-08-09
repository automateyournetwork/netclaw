"""Feature 100 (T042): endpoint retirement.

FR-026 is the requirement with teeth: "Achieving any requirement in this feature MUST
NOT require direct database manipulation by an operator." Resolving the 2026-08-06
incident required

    UPDATE federation_peer SET endpoint_host='', endpoint_port=NULL,
           endpoint_updated_at=NULL WHERE identity IN (...)

against the *running* database, because `upsert_peer` treats None as "leave unchanged"
and `endpoint_port` is an INTEGER with no sentinel. That is what this replaces.

FR-022 is the guard: clearing a dial address must not disturb trust, chat, state or
audit history. A "cleanup" that silently de-federated a peer would be far worse than
the noise it fixes.
"""

import pytest


IDENT = "as65099-10.255.255.1"


@pytest.fixture
def peer(manager):
    manager.upsert_peer(65099, "10.255.255.1", display_name="Byrn",
                        endpoint_host="1.2.3.4", endpoint_port=1179)
    return manager.get_peer(IDENT)


# ── The clear itself (FR-021) ────────────────────────────────────────────────

def test_all_three_endpoint_fields_cleared_together(manager, peer):
    assert peer["endpoint_host"] == "1.2.3.4"
    assert peer["endpoint_updated_at"] is not None

    manager.forget_peer_endpoint(IDENT)

    row = manager.get_peer(IDENT)
    assert row["endpoint_host"] is None
    assert row["endpoint_port"] is None
    assert row["endpoint_updated_at"] is None, (
        "data-model §2: a freshness marker without an endpoint is an invalid state")


def test_returns_the_previous_endpoint(manager, peer):
    """Reversible by hand, and reportable to the operator who ran it."""
    result = manager.forget_peer_endpoint(IDENT)
    assert result["forgotten"] is True
    assert result["identity"] == IDENT
    assert result["previous"]["host"] == "1.2.3.4"
    assert result["previous"]["port"] == 1179
    assert result["previous"]["updated_at"] is not None


def test_idempotent_second_call(manager, peer):
    """contracts §2: forgetting an already-absent endpoint is success, not an error."""
    first = manager.forget_peer_endpoint(IDENT)
    second = manager.forget_peer_endpoint(IDENT)
    assert first["forgotten"] is True
    assert second["forgotten"] is False
    assert second["previous"] is None


def test_peer_with_no_endpoint_is_a_noop(manager):
    manager.upsert_peer(65007, "7.7.7.7", display_name="Nicholas")
    result = manager.forget_peer_endpoint("as65007-7.7.7.7")
    assert result["forgotten"] is False
    assert result["previous"] is None


def test_unknown_peer_raises_keyerror(manager):
    """Mapped to HTTP 404 by the route (contracts §3)."""
    with pytest.raises(KeyError):
        manager.forget_peer_endpoint("as65999-9.9.9.9")


def test_partial_endpoint_still_reported_as_forgotten(manager):
    """A row with a host but no port is malformed but must still be clearable."""
    manager.upsert_peer(65008, "8.8.8.8", endpoint_host="5.6.7.8")
    result = manager.forget_peer_endpoint("as65008-8.8.8.8")
    assert result["forgotten"] is True
    assert manager.get_peer("as65008-8.8.8.8")["endpoint_host"] is None


# ── FR-022: everything else untouched ────────────────────────────────────────

def test_federated_state_and_trust_survive(manager):
    manager.upsert_peer(65099, "10.255.255.1", display_name="Byrn",
                        endpoint_host="1.2.3.4", endpoint_port=1179)
    manager.local_consent(65099, "10.255.255.1")
    manager.remote_consent(65099, "10.255.255.1")
    manager.set_chat_enabled(IDENT, True)
    before = manager.get_peer(IDENT)

    manager.forget_peer_endpoint(IDENT)
    after = manager.get_peer(IDENT)

    for col in ("identity", "peer_as", "router_id", "display_name", "state",
                "chat_enabled", "created_at", "trust_model", "pinned_fp"):
        assert after[col] == before[col], f"FR-022: {col} must not change"


def test_audit_history_survives(manager):
    from bgp.federation.audit import Auditor
    manager.upsert_peer(65099, "10.255.255.1", endpoint_host="1.2.3.4",
                        endpoint_port=1179)
    auditor = Auditor(manager)
    auditor.record(direction="inbound", peer_identity=IDENT, target_type="tool",
                   target_name="show_version", request_id="keep-me",
                   decision="allowlisted", outcome="success")
    before = len(auditor.recent(peer_identity=IDENT, limit=50))

    manager.forget_peer_endpoint(IDENT)

    assert len(auditor.recent(peer_identity=IDENT, limit=50)) == before


def test_updated_at_is_bumped(manager, peer):
    """The change must be visible as a modification of the row."""
    manager.forget_peer_endpoint(IDENT)
    assert manager.get_peer(IDENT)["updated_at"] is not None


# ── FR-023/024: dialling stops, then resumes on re-registration ──────────────

def test_supervisor_skip_condition_is_met_after_forgetting(manager, peer):
    """FR-023: the supervisor's pre-existing 'no endpoint → skip' branch is what makes
    this take effect with no restart, since list_peers() is re-read every iteration."""
    manager.forget_peer_endpoint(IDENT)
    row = [p for p in manager.list_peers() if p["identity"] == IDENT][0]
    assert not (row.get("endpoint_host") and row.get("endpoint_port")), (
        "FR-023: peer must be skipped by dialling")


def test_reregistration_restores_dialling(manager, peer):
    """FR-024: no operator action required — the normal inbound-contact path calls
    upsert_peer, which is all that is needed."""
    manager.forget_peer_endpoint(IDENT)
    manager.upsert_peer(65099, "10.255.255.1", endpoint_host="9.9.9.9",
                        endpoint_port=2179)
    row = manager.get_peer(IDENT)
    assert row["endpoint_host"] == "9.9.9.9"
    assert row["endpoint_port"] == 2179
    assert row["endpoint_updated_at"] is not None, (
        "FR-013 depends on this marker changing so backoff resets immediately")


# ── FR-026 / research R7: the API must actually be capable of clearing ───────

def test_upsert_peer_cannot_clear_an_endpoint(manager, peer):
    """The reason this method exists. If upsert_peer ever gains clear semantics, this
    documents why forget_peer_endpoint was added and can be revisited."""
    manager.upsert_peer(65099, "10.255.255.1", endpoint_host=None, endpoint_port=None)
    row = manager.get_peer(IDENT)
    assert row["endpoint_host"] == "1.2.3.4", (
        "upsert_peer treats None as 'leave unchanged' — hence a dedicated method")


def test_forget_does_not_touch_other_peers(manager, peer):
    manager.upsert_peer(65006, "6.6.6.6", display_name="Nate",
                        endpoint_host="netclaw.thirdlevel.ai", endpoint_port=1179)
    manager.forget_peer_endpoint(IDENT)
    other = manager.get_peer("as65006-6.6.6.6")
    assert other["endpoint_host"] == "netclaw.thirdlevel.ai"
    assert other["endpoint_port"] == 1179


# ── The MCP tool and route exist and are wired (Constitution XI/XII) ─────────

def test_mcp_tool_is_registered():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[2] / "mcp-servers/n2n-mcp/server.py"
    text = src.read_text()
    assert "async def n2n_forget_endpoint" in text
    assert "/n2n/peers/forget-endpoint" in text


def test_daemon_route_is_registered():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[2]
           / "mcp-servers/protocol-mcp/bgp-daemon-v2.py")
    text = src.read_text()
    assert '"/n2n/peers/forget-endpoint"' in text
    assert "forget_peer_endpoint" in text
    assert "unknown peer" in text, "FR: unknown identity must map to 404"


def test_route_records_attribution():
    """FR-025 / Constitution IV: no operation may execute silently."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[2]
           / "mcp-servers/protocol-mcp/bgp-daemon-v2.py")
    text = src.read_text()
    assert "endpoint-forgotten" in text
