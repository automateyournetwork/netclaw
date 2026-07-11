"""T015: consent state machine + kill switch (FR-001, FR-004, FR-028)."""

from bgp.federation.manager import PeerState, peer_identity


def test_mutual_consent_required(manager):
    ident = peer_identity(65007, "7.7.7.7")
    # Local only → pending remote
    assert manager.local_consent(65007, "7.7.7.7", "Nicholas") == PeerState.CONSENT_PENDING_REMOTE
    assert not manager.is_federated(ident)
    # Remote arrives → federated
    assert manager.remote_consent(65007, "7.7.7.7") == PeerState.FEDERATED
    assert manager.is_federated(ident)


def test_remote_first_then_local(manager):
    ident = peer_identity(65099, "10.255.255.1")
    assert manager.remote_consent(65099, "10.255.255.1") == PeerState.CONSENT_PENDING_LOCAL
    assert not manager.is_federated(ident)
    assert manager.local_consent(65099, "10.255.255.1") == PeerState.FEDERATED


def test_kill_switch_severs_and_purges(manager):
    ident = peer_identity(65007, "7.7.7.7")
    manager.local_consent(65007, "7.7.7.7")
    manager.remote_consent(65007, "7.7.7.7")
    # Plant a cached inventory to prove it gets purged
    inv = manager.base_dir / "inventories" / f"{ident}.json"
    inv.write_text('{"version": 1}')
    assert manager.sever(ident)
    assert manager.get_peer(ident)["state"] == PeerState.SEVERED.value
    assert not manager.is_federated(ident)
    assert not inv.exists()


def test_refederation_requires_fresh_consent(manager):
    ident = peer_identity(65007, "7.7.7.7")
    manager.local_consent(65007, "7.7.7.7")
    manager.remote_consent(65007, "7.7.7.7")
    manager.sever(ident)
    # After sever, a single new local consent should NOT re-federate on its own
    assert manager.local_consent(65007, "7.7.7.7") == PeerState.CONSENT_PENDING_REMOTE
    assert not manager.is_federated(ident)


def test_state_survives_reopen(manager):
    """FR-028: federation state persists across a manager restart (new process)."""
    ident = peer_identity(65007, "7.7.7.7")
    manager.local_consent(65007, "7.7.7.7")
    manager.remote_consent(65007, "7.7.7.7")
    db_path, base = manager.db_path, str(manager.base_dir)
    manager.close()

    from bgp.federation.manager import FederationManager
    m2 = FederationManager(db_path=db_path, base_dir=base)
    assert m2.is_federated(ident)  # survived without re-consent
    m2.close()
