# Verification

Operator Risk on Ubuntu 24.04 amd64, OpenClaw 2026.10.9, Node 24.22.1, Border plus five
running members in testing mode. Commands ran with `umask 077`. No credentials are
recorded here; environment files were read for key names and paths only.

## T001 diagnosis (live)

- Scope against each member's own `openclaw skills check --json`, run with that member's
  `.env` and an unused `OPENCLAW_GATEWAY_PORT`: pyats loaded 1 of 18 scoped skills
  (`PYATS_MCP_SCRIPT` missing). Other refusals are listed in research.
- Without the port override the same command, in a member's environment, failed with
  "unauthorized: gateway token mismatch": it had asked the Border's gateway.
- The Border workspace held 252 skill folders; OpenClaw listed 200, the first 200
  alphabetically. `ue5-network-viz`, `uml-diagram` and `suzieq-observability` were in no
  list.

## T004 tests

- `tests/n2n/test_member_skill_status_174.py` (9 tests): the report's reasons
  (`missing_requirements`, `disabled`, `not_installed`, `not_loaded`) and that the base
  floor is skipped; names-only projection; the router skips a member that cannot load the
  skill and picks another; a refusal that names neither member nor requirement; no report
  routes as before; the peer card leaves out a skill no member can load; the check runs
  `skills check --agent main --json` on an unused port with no gateway URL; a failing
  check, empty scope or Hermes runtime reports nothing; the report goes only to the
  current Border channel.
- `tests/n2n`, excluding four files this host cannot collect (below): 1155 passed,
  5 skipped, 5 failed and 115 errors. The same 120 tests fail identically on
  `upstream/main` in the same environment (protected/Hermes tests).
- `test_direct_transport_168`, `test_exporter_tls_168`, `test_ngrok_transport_168` and
  `test_protected_enrollment_172` do not collect with this host's packages: the system
  pyOpenSSL is incompatible with the installed `cryptography`. Run against the system
  `cryptography`, `test_protected_enrollment_172` has the same 15 failures on this branch
  and on `upstream/main`, including both tests that pin the connection's calls.
- `ruff check --select F,E9` reports no new findings on the changed files.

## T005 live

The four federation files were backported to the operator Risk (its `router.py` predates
the routable-capabilities hint, so only the routing change was ported there). The mesh
daemon and the five running members were restarted.

- Each member reported after connecting, and the Border logged, for example:
  `member byrns-risk/viz cannot load scoped skill ue5-network-viz (missing_requirements;
  missing env: UE5_MCP_URL); not routing it there`. Reports: cml 2 (disabled), pyats 1,
  viz 3, secops 1, guardian-claw 6 (`not_installed`).
- `POST /n2n/route` for `ue5-network-viz` and `wifi-diagnosis` returned
  `IN2N_ERR_NO_CAPABLE_MEMBER` "… It is in scope, but no member's runtime can load it." at
  once, without starting a task. Before the change a `ue5-network-viz` request ran 40 s
  on the member and failed there.
- `markmap-viz`, which viz can load, routed and completed twice (46 s and 50 s). The first
  reply was "Openclaw Tool Search blocked": the model called a `tool_call` wrapper that
  that run did not offer, and never reached the tool. The second called the same wrapper,
  then the markmap server through `exec`, and saved its 5-node SVG. A `ue5-network-viz`
  run on 2026-11-03, before this change, shows the same wrapper calls. That is the model
  and OpenClaw's tool search, not routing; it is recorded, not changed.
