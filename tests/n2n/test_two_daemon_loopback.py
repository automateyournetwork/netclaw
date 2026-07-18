"""T023: two-service loopback integration — the US1 acceptance path.

Exercises the real channel.py + service.py + inventory.py over a TCP socket
pair, mimicking the agent's NCFED discrimination handoff. Covers:
consent → federated → inventory exchange → capability query → restart
persistence (FR-028) → sever (FR-004).
"""

import asyncio
import json

import pytest

from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager, PeerState, peer_identity
from bgp.constants import NCFED_MAGIC
from bgp.federation.channel import read_handshake


def _make_repo(root):
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "openclaw.json").write_text(json.dumps({
        "mcpServers": {"cml-mcp": {"tools": ["list_labs"]}}}))
    sk = root / "workspace" / "skills" / "cml-lab-lifecycle"
    sk.mkdir(parents=True, exist_ok=True)
    (sk / "SKILL.md").write_text("# cml-lab-lifecycle\n\nManage CML labs.\n")
    (root / ".env").write_text("CML_PASSWORD=secretxyz123\n")


def _service(base, repo, local_as, rid, name):
    mgr = FederationManager(base_dir=str(base))
    svc = FederationService(local_as=local_as, router_id=rid, display_name=name, manager=mgr)
    # Point the inventory builder at the test repo
    svc.inventory.repo_root = repo
    svc.inventory.config_path = repo / "config" / "openclaw.json"
    svc.inventory.skills_dir = repo / "workspace" / "skills"
    svc.inventory.env_path = repo / ".env"
    return svc


def test_federation_end_to_end(tmp_path):
    asyncio.run(_federation_end_to_end(tmp_path))


async def _federation_end_to_end(tmp_path):
    repo = tmp_path / "repo"
    _make_repo(repo)

    initiator = _service(tmp_path / "a", repo, 65001, "4.4.4.4", "John")     # lower AS dials
    acceptor = _service(tmp_path / "b", repo, 65007, "7.7.7.7", "Nicholas")  # higher AS listens

    a_ident = peer_identity(65001, "4.4.4.4")
    b_ident = peer_identity(65007, "7.7.7.7")

    # Both operators consent (mutual — FR-001)
    initiator.manager.local_consent(65007, "7.7.7.7", "Nicholas")
    acceptor.manager.local_consent(65001, "4.4.4.4", "John")

    # Acceptor's listener mimics the agent NCFED discrimination branch
    async def on_conn(reader, writer):
        magic = await reader.readexactly(5)
        assert magic == NCFED_MAGIC
        peer_as, rid = await read_handshake(reader)
        await acceptor.accept_channel(peer_as, rid, reader, writer)

    server = await asyncio.start_server(on_conn, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    # Not `async with server`: on Python 3.12+ Server.wait_closed() (run by
    # __aexit__) waits for every connection handler to return — a still-open
    # channel handler would hang the test forever (seen on the 3.14 host).
    try:
        # Lower-AS side dials
        await initiator.open_channel(65007, "7.7.7.7", "127.0.0.1", port)
        # Let hello + inventory exchange settle
        await asyncio.sleep(0.5)

        # Both sides reached FEDERATED
        assert initiator.manager.is_federated(b_ident)
        assert acceptor.manager.is_federated(a_ident)

        # Capability query: acceptor cached the initiator's inventory and vice versa
        got_on_acceptor = acceptor.inventory.load_remote(a_ident)
        got_on_initiator = initiator.inventory.load_remote(b_ident)
        assert got_on_acceptor is not None, "acceptor should have initiator's inventory"
        assert got_on_initiator is not None, "initiator should have acceptor's inventory"
        skills = {s["name"] for s in got_on_acceptor["inventory"]["skills"]}
        assert "cml-lab-lifecycle" in skills
        # No-secrets invariant held (SC-004)
        assert "secretxyz123" not in json.dumps(got_on_acceptor["inventory"])

        # FR-028: acceptor federation state survives a manager restart
        db, base = acceptor.manager.db_path, str(acceptor.manager.base_dir)
        acceptor.manager.close()
        m2 = FederationManager(db_path=db, base_dir=base)
        assert m2.is_federated(a_ident)
        m2.close()

        # Kill switch (FR-004): initiator severs; state severed, no exception
        ok = await initiator.sever_local(b_ident)
        assert ok
        assert initiator.manager.get_peer(b_ident)["state"] == PeerState.SEVERED.value
    finally:
        server.close()
