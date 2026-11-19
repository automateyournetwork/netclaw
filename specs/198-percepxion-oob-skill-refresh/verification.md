# Verification

No credentials or private network data are recorded here. Run on Ubuntu 24.04 under WSL2,
Python 3.12.3, Node 22, against `main` at a5e7c3a3.

## Repository checks

- `python3 scripts/verify-spec-artifacts.py`: PASS (188 specs).
- `python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs
  --surface meraki-ids --surface packages --surface portability`: PASS.
- `node scripts/build-catalog.mjs --check` (after `npm --prefix extensions/netclaw-vscode ci
  --ignore-scripts`) and `python3 scripts/build-catalog.py --check`: PASS (242 skills). The
  regenerated catalog changes only the Percepxion component's tool count, the skill's description and
  sha256, and the `scripts/lib/catalog.sh` digest.
- `python3 scripts/check-catalog-metadata.py`: PASS (116 components, 242 skills).
- `python3 scripts/verify-catalog-coverage.py`: PASS.
- `python3 -m unittest discover -s tests -p test_setup_catalog.py`: OK, after updating the Percepxion
  description in `tests/fixtures/setup/catalog-baseline.json` (37 to 38 tools).
- `python3 -m unittest discover -s tests -p test_pyats_testbeds.py`: OK.
- `python3 -m unittest discover -s tests -p test_testbed_setup.py`: 1 failure
  (`test_actual_new_plan_and_legacy_prompts_on_controlling_terminal`), identical on unchanged `main`
  on this host; it needs a controlling terminal.
- `python3 scripts/check-skill-limits.py`: ok, 242 skills covered; prompt characters 98,575 of
  122,000 (98,387 before). The existing 80% note stands.
- `python3 scripts/run-contract-tests.py --suite reconcile|skill-limits|document --prepare`: PASS.
- `python3 -m pytest tests/unit/test_skill_deployment.py`: 4 passed.
- `python3 scripts/prepare-release.py --check`: PASS (1.25.0); `python3 scripts/test-prepare-release.py`: OK.
- `python3 scripts/check-catalog-links.py --base-ref a5e7c3a3...`: no changed catalog links.

## Skill content

- Size: `SKILL.md` 142 lines (from 1,122); references 145, 145 and 154 lines.
- Tool names: every tool named in the skill and references exists in `src/percepxion_mcp/server.py`
  at `533fdc98` and `src/slc_mcp/server.py` at `c5ba7f6b` (the installed revisions). Parameters
  were checked against signatures parsed from those files; they are identical at percepxion-mcp-server
  2.2.0 and slc-mcp-server 1.4.0.
- Related skills: all ten named skills exist under `workspace/skills/`.
- Links: the SLC 9000 user guide, the five Lantronix and community repositories and both PyPI
  projects return HTTP 200.
- Public-only: no reference to unreleased or private Lantronix software, internal hosts, lab
  addresses or ticket IDs (pattern scan over the new and changed files). `gitleaks dir` over the
  changed files reports two findings, both in unchanged README lines (Webex placeholder examples).

## Live checks

- **W9, NetBox:** on a NetBox 4.x lab instance with Lantronix console servers, `netbox_get_objects`
  on `dcim.consoleport` with `{"cabled": true}` returned `connected_endpoints` naming the console
  server port (`Port-14`) and its console server, matching `link_peers` for a direct cable.
- **W9, Nautobot:** the GraphQL query in `references/source-of-truth.md` ran without errors on a
  Nautobot 3.2 lab instance with the Lantronix SSoT app, resolving a console port's
  `connected_console_server_port` (`Port-05`), its `cf_lx_port_state` and `cf_lx_attached_hostname`,
  and the console server's `cf_percepxion_device_id`, `cf_lx_mgmt_ip`, `serial` and `primary_ip4`.
  That instance runs an app build without `lx_ssh_port`; the query still succeeds and the skill falls
  back to the factory SSH port when the field is absent. `lx_ssh_port` is defined in the 0.7.0 release
  source.

## Not verified

- An end-to-end NetClaw session running W9 or W10 with all three servers registered.
- The Nautobot coverage gate through `nautobot_run_job`, and the NetBox gate through the
  `lantronix.oob` role; both were checked against the job, role and MCP server sources only.
- Percepxion tool calls in this session (the skill's Percepxion steps are unchanged in kind from spec
  104 and were checked against the server source).
- The `tesslio/skill-review` score, which runs in CI on the pull request.
- macOS.
