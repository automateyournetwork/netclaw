# On-prem pyATS HA member that reaches CML (stream Q)

Status: source + tests only. Nothing here contacted a device, CML's execution plane, Anthropic, Docker or a Border. It is NOT qualified:
the hosted guard path has no REAL evidence, and no real SSH session to R1 has been run through this member.

## What it is
One exact, reviewed read: `pyats_run_show_command {device_name: R1, command: "show version", timeout: 30, retries: 1}` against a CML IOS-XE IOL router
over strict-host-key SSH from the owner's Mac, as an HA execution member (attaches outbound to the three Borders like the calculator and NetBox members)
on the hosted Sonnet 4.6 profile. **CML itself has no protected tool**: the CML REST API is not exercised through the HA path. CML is only the
environment hosting the router; the qualified route to it is pyATS over an IOL node (members-plan.md (c)).

## Product source changes (REVIEW THESE: security-sensitive, qualified R02 code)
1. **Effect admission around the pyATS effect (new fence).** `protected_runtime.invoke_pyats(..., ha_required, ha_admission)` and the
   call site in `protected_docker.run()` (`native()`): under HA the single `tools/call` is written through `ha/mcp_transport.ha_stdio_client`
   after `ha_admission('tool', 1, sha(tool_call), call)`, exactly as `protected_mcp.invoke_mcp` does for the calculator and NetBox. Before this
   change the pyATS branch passed no admission at all (a real-effect fence gap under HA). Without HA (`'cluster'` not in the payload) behaviour is
   byte-for-byte the R02 path. Note what the fence covers: freshness at the pipe handoff of the one call; the later SSH/CLI work happens in the child
   after that handoff and is covered by the existing execute-once, spent-claim and unknown-outcome rules, not by the admission clock.
2. **`credential_file` (optional field of the pyats binding).** A launcher-started member cannot receive extra environment variables
   (`protected_role._OPTIONAL`), so the three reviewed names (`PYATS_R02_USERNAME/PASSWORD/ENABLE_PASSWORD`) may come from a private
   `<member root>/artifacts/pyats-credential` (0600, owner-only, canonical path, exactly those three names, no extras or duplicates) read by
   `protected_runtime.pyats_credentials`. The path is bound into `tool_contract_digest` only when present (the R02 digest is unchanged). Values reach only the child's environment.
3. **Runtime shape `_PYATS_HOSTED_FIELDS` = the qualified R02 pyats fields + `hosted`** (no `mcp`, no `ollama`) in `validate_runtime_fields`.

## Builder (`labs/ha/r09_member.py`, flavor `pyats`; ollama/netbox flavors untouched)
`identity --flavor pyats`, `freeze` (flavor closure adds exactly `scripts/protected-tool-broker.py` and `scripts/lib/protected_pyats.py`, which
`invoke_pyats` reads from `<source>/scripts`), `python-env`, new `pyats-env` (verifies and records the R02 pyATS environment: pyats/genie/unicon 25.2,
mcp 2.x importable, the pinned Unicon source digest passes `validate_native_policy`, upstream sources hashed), `artifacts`, `materialize`, `validate`.
`artifacts` reads the owner's `~/netclaw/testbed/testbed.yaml` (device R1: iosxe/iol, 192.168.2.201:22, testbed-level default + enable credentials),
writes a REVIEWED minimal testbed with `%ENV{...}` credential references only, the strict `known_hosts` (pre-scanned or `ssh-keyscan`), the endpoint
identity hash, the credential file and the hosted guard files, and pins all of it by hash.

## Tests (python3.10 builder venv has no mcp; the member's own 3.12 env does)
- `tests/n2n/test_ha_pyats_member_182.py`: 23 pass under the R04A member env, 15 pass + 8 skip (mcp-dependent) under the 3.10 venv.
  Runtime shape and its neighbours refused; digest unchanged without `credential_file` and bound with it; credential file refusals (group-readable,
  symlink, missing, extra, duplicate, empty, wrong names) and the unchanged env-only path; **no admission -> no tool call**, **refused/expired admission
  -> no tool call**, **replay into the same operation -> refused, one call only**, **wrong command/policy -> refused** at the catalog contract,
  the child-side validator and `ExactToolBroker`; the HA transport (not the stock one) is used under HA and the stock one without; drift refuses
  before any child; full offline pipeline (identity -> freeze -> python-env -> pyats-env on the REAL R02 env -> artifacts -> materialize -> the
  production role validator, `role_validate=valid`, `closure_import=ok`) with credentials confined to exactly two 0600 files.
- Regression (`test_ha_*`, `test_protected_*`, `test_ollama_*`, `test_skill_failure_*`, 67 files, 3.10 venv with `--continue-on-collection-errors`): mine
  25 failed / 1019 passed / 139 errors; pristine HEAD (7a0c379f, throwaway worktree) 26 failed / 1017 passed / 139 errors. Every failure in mine also
  fails at HEAD (the one HEAD-only failure is the NetBox pipeline test, which needs the git-ignored `mcp-servers/netbox-mcp-server` clone).

## Verified on this Mac (read-only)
- CML 2.10.0 authenticates; lab `NetClaw-Full-Topo` is STARTED with R1/R2 (iol-xe) BOOTED, MGMT-BRIDGE and MGMT-SW booted (R1 and R2 SSH ports 22 open from the Mac;
  SW1 STOPPED). CML reports no layer-3 addresses for the IOL nodes, so the address comes from the owner testbed (192.168.2.201).
- With the exact strict policy the adapter requires (`-F /dev/null -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile=<scanned>`)
  OpenSSH 10.3 completes the host-key handshake with R1 and stops at authentication (`ssh-rsa` host key, "Permission denied (publickey,keyboard-interactive,password)");
  no credential was sent.

## Live runbook (parent runs; PY = r09venv python, MPY = the member env python, G = current deployment root)
```
cd /Users/john.capobianco/netclaw
PY=/private/tmp/claude-503/-Users-john-capobianco-netclaw/8e4f7aba-bfb3-4565-9ae8-2535153d5ff0/scratchpad/r09venv/bin/python
MPY=~/.local/share/netclaw/roadmap-r04a-owner-20261104/local-member/venv/bin/python        # has mcp; run with PYTHONDONTWRITEBYTECODE=1 / -B
G=~/.local/share/netclaw/r09-gen4-20261109   M=~/.local/share/netclaw/r09-member-pyats-20261109
$PY  -m labs.ha.r09_member identity   --root $M --deployment $G --flavor pyats
$PY  -m labs.ha.r09_member freeze     --root $M
$PY  -m labs.ha.r09_member python-env --root $M
PYTHONDONTWRITEBYTECODE=1 $MPY -m labs.ha.r09_member pyats-env --root $M            # records the R02 env (resolved generation directory)
ssh-keyscan -T 8 -t rsa 192.168.2.201 > /tmp/r1-known-hosts                         # then VERIFY the fingerprint against R1's console (below)
( set -a; . ~/netclaw/.env; set +a; PYTHONDONTWRITEBYTECODE=1 $MPY -m labs.ha.r09_member artifacts --root $M --known-hosts-file /tmp/r1-known-hosts )
PYTHONDONTWRITEBYTECODE=1 $MPY -m labs.ha.r09_member materialize --root $M
PYTHONDONTWRITEBYTECODE=1 $MPY -m labs.ha.r09_member validate    --root $M          # expect role_validate=valid, closure_import=ok
# enroll exactly as for the other members (stop 3 Borders, wait for lease expiry, labs/ha/r09_vm_enroll.py with $M/identity/member.json, restart Montreal first),
# start with the production launcher (cwd=$M/home, env -i PATH=/usr/bin:/bin HOME=$M/home, python from contract.json), verify attachments == 3,
# then prepare/approve pyats_run_show_command R1 `show version` from the HUD or VS Code (members listed by member_id; this one is nc182-r09/pyats-*).
```
Independent check afterwards: the member's `runtime/<op>/tool/device.log`, `tool-evidence.json` (raw output, `raw_sha256`, `execute_calls: 1`) and R1's own
`show users` / AAA or `show logging` for one login at the operation time. `read_provider_fence(<runtime>/<op>)` counts the model calls.

## CML prerequisites (for the owner)
- Keep lab **NetClaw-Full-Topo** STARTED with **R1** (iol-xe) BOOTED and reachable from the Mac on 192.168.2.201:22 (R2 on .202 is the alternate; use `--device R2` in `pyats-env`).
- The user in the testbed must log in at **privilege 15** (the adapter refuses unless the post-login Unicon state is `enable`, `initial_exec_state_required`).
  If R1's account lands at `>`, the operation refuses safely before any command.
- R1 must still carry the SSH host key that the scanned `known_hosts` pins; if the lab is wiped/restarted with a new key, re-scan and rebuild (the hash is signed).

## Decisions the owner must review
1. The effect-admission edit in qualified `protected_runtime.py` / `protected_docker.py` (item 1 above) and that it does not cover the in-child SSH time.
2. `credential_file` (item 2): the Mac holds the device login in a 0600 file; the guard holds the Anthropic key in a 0600 file; both are plaintext at rest on the owner's machine.
3. **Trust-on-first-use of R1's host key**: the strict `known_hosts` is whatever `ssh-keyscan` returns over the LAN at build time. Compare the SHA256 fingerprint with the device console (`show crypto key mypubkey rsa` / `show ip ssh`) before enrolling.
4. Hosted+pyats runtime shape accepted by `validate_runtime_fields` (item 3). The hosted guard path itself remains unqualified (no egress filter, no spend meter, derived guard config; see netbox-member.md).
5. Limits: tool timeout 120 s with the signed hosted task cap of 180 s; a slow device plus two model calls could exceed the task window and end `unknown`.
6. This is a read of a lab router with a fixed command; any other device, command or retry count is refused at the catalog, the broker and the child. No config mode is reachable (`init_config_commands: []`).
7. The shared guard-image model pin (claude-sonnet-4-6) and the open (unauthenticated) HUD apply here as for NetBox.
