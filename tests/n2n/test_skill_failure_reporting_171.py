"""Spec 171: a delegated skill request tells the agent to report a failed or
missing tool instead of substituting output of its own."""

import asyncio

from bgp.federation.gateway import SKILL_FAILURE_RULE
from bgp.federation.manager import FederationManager
from bgp.federation.service import FederationService

PEER = "as65001-4.4.4.4"


def test_peer_skill_request_carries_the_failure_rule(tmp_path, monkeypatch):
    mgr = FederationManager(base_dir=str(tmp_path / "n2n"))
    svc = FederationService(local_as=65002, router_id="5.5.5.5", display_name="Bob", manager=mgr)
    seen = {}

    async def fake_run(prompt, **kwargs):
        seen["prompt"] = prompt
        return "ok", 1

    import bgp.federation.gateway as gw
    monkeypatch.setattr(gw, "run_agent_turn", fake_run)
    try:
        out = asyncio.run(svc.invoker._exec_skill_gateway("markmap-viz", "draw the risk", peer=PEER))
    finally:
        mgr.close()
    assert out == ("ok", 1)
    prompt = seen["prompt"]
    assert "'markmap-viz'" in prompt and prompt.endswith("draw the risk")
    # The rule precedes the request, so request text cannot pose as part of it.
    assert prompt.index(SKILL_FAILURE_RULE) < prompt.index("draw the risk")
