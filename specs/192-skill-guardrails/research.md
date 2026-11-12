# Research

- `n2n_kill` (`mcp-servers/n2n-mcp/server.py`) is documented as destructive: it revokes
  consent, drops the NCFED channel and purges the cached inventory; BGP is untouched.
  `n2n_forget_endpoint` only clears a stale dial address; the peer stays federated and
  reconnects when it registers a new endpoint. The skill described the kill switch but
  not when to propose it.
- `NETCLAW_LAB_MODE` is read from the environment at start by `protocol-mcp`
  (`LAB_MODE`), `gnmi-mcp` and `claroty-mcp` (`itsm_gate.py`). The server gate is real,
  but the value comes from `.env`, which an agent with shell or file tools could edit.
  The skill said "never set this in production" without saying the agent never sets it.
- `servicenow-change-workflow` lists when an emergency applies (active outage, security
  incident, actively exploited vulnerability) and requires notifying the human.
  `pyats-config-mgmt` repeats the four-step emergency path with no qualification, so an
  agent working from that skill alone could treat any urgent-sounding change as an
  emergency. The new conditions are stricter for direct pyATS changes (one change that
  can be rolled back, confirmed by the operator) and keep the same categories.
- The skill catalog (`config/components/catalog.json`) records each SKILL.md's sha256;
  `node scripts/build-catalog.mjs` then `python3 scripts/build-catalog.py` regenerate it
  and `--check` runs in CI.
