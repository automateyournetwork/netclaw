"""Model + suggested-timeout negotiation in the n2n/hello handshake.

A claw advertises the model it runs and how long peers should wait for its
replies. The requesting side stores those and sizes its outbound chat/skill
timeout to the peer's advertised value (clamped), so a slow far-side model
doesn't cause a premature client-side timeout.
"""

import os
import tempfile

import pytest

from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation import service as svc


def _mgr():
    return FederationManager(base_dir=tempfile.mkdtemp())


def test_local_profile_from_env(monkeypatch):
    monkeypatch.delenv("N2N_MODEL", raising=False)
    monkeypatch.setenv("NETCLAW_MODEL", "glm-5.2:cloud")
    monkeypatch.delenv("N2N_SUGGESTED_TIMEOUT_S", raising=False)
    monkeypatch.delenv("N2N_CHAT_IDLE_TIMEOUT_S", raising=False)
    assert svc.local_model() == "glm-5.2:cloud"
    assert svc.local_suggested_timeout_s() == 300  # default

    monkeypatch.setenv("N2N_MODEL", "claude-sonnet-4")
    monkeypatch.setenv("N2N_SUGGESTED_TIMEOUT_S", "45")
    assert svc.local_model() == "claude-sonnet-4"        # N2N_MODEL wins
    assert svc.local_suggested_timeout_s() == 45


def test_set_and_get_peer_profile():
    m = _mgr()
    m.upsert_peer(65001, "4.4.4.4", "John")
    ident = peer_identity(65001, "4.4.4.4")
    m.set_peer_profile(ident, model="qwen3:480b-cloud", suggested_timeout_s=200)
    p = m.get_peer(ident)
    assert p["peer_model"] == "qwen3:480b-cloud"
    assert p["peer_suggested_timeout_s"] == 200


def test_set_peer_profile_partial_and_bad_values():
    m = _mgr()
    m.upsert_peer(65007, "7.7.7.7")
    ident = peer_identity(65007, "7.7.7.7")
    # Only model, no timeout
    m.set_peer_profile(ident, model="llama3")
    assert m.get_peer(ident)["peer_model"] == "llama3"
    assert m.get_peer(ident)["peer_suggested_timeout_s"] is None
    # Bad timeout value is ignored, doesn't crash
    m.set_peer_profile(ident, suggested_timeout_s="not-a-number")
    assert m.get_peer(ident)["peer_suggested_timeout_s"] is None


def test_migration_adds_columns_to_legacy_db():
    """A federation.db created before these columns existed gets them added."""
    import sqlite3
    base = tempfile.mkdtemp()
    db = os.path.join(base, "federation.db")
    # Simulate a legacy table without the new columns
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE federation_peer (identity TEXT PRIMARY KEY, peer_as INTEGER, "
        "router_id TEXT, display_name TEXT, endpoint_host TEXT, endpoint_port INTEGER, "
        "state TEXT, chat_enabled INTEGER, created_at TEXT, updated_at TEXT)")
    conn.execute(
        "INSERT INTO federation_peer VALUES ('as65001-4.4.4.4',65001,'4.4.4.4','John',"
        "NULL,NULL,'federated',1,'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')")
    conn.commit()
    conn.close()

    # Opening via the manager should migrate in the missing columns
    m = FederationManager(db_path=db, base_dir=base)
    p = m.get_peer("as65001-4.4.4.4")
    assert p is not None
    assert p["peer_model"] is None
    assert p["peer_suggested_timeout_s"] is None
    # And the setter now works on the migrated row
    m.set_peer_profile("as65001-4.4.4.4", model="claude", suggested_timeout_s=60)
    assert m.get_peer("as65001-4.4.4.4")["peer_model"] == "claude"


def test_chat_honors_peer_timeout_clamped(monkeypatch):
    """ChatManager._peer_wait_timeout clamps the peer value to [default, 900]."""
    from bgp.federation.chat import ChatManager

    monkeypatch.setenv("N2N_CHAT_IDLE_TIMEOUT_S", "300")
    m = _mgr()
    ident = peer_identity(65001, "4.4.4.4")
    m.upsert_peer(65001, "4.4.4.4", "John")

    class _FakeService:
        def __init__(self, manager):
            self.manager = manager
            self.authz = None
            self.audit = None
    cm = ChatManager.__new__(ChatManager)
    cm.manager = m

    # No advertised value -> local default
    assert cm._peer_wait_timeout(ident) == 300
    # Advertised below default -> raised to default (never wait less than ours)
    m.set_peer_profile(ident, suggested_timeout_s=45)
    assert cm._peer_wait_timeout(ident) == 300
    # Advertised above default -> honored
    m.set_peer_profile(ident, suggested_timeout_s=600)
    assert cm._peer_wait_timeout(ident) == 600
    # Advertised above the ceiling -> clamped to 900
    m.set_peer_profile(ident, suggested_timeout_s=99999)
    assert cm._peer_wait_timeout(ident) == 900
