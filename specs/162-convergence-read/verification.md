# Verification ledger

## Run and scope

- Start: 2026-10-31 00:09:29 UTC. Deadline: 00:54:29 UTC.
- Limit: three attempts per task, shared across coordinator and delegates.
- Checkout: `/home/ubuntu/netclaw-convergence-read`; branch: `162-convergence-read`.
- Base: upstream `4d791a364989405a98ac52bec91a9530cf4317b4`.
- External service: `f54bafca82f339d8573c55c53795fa05bd9dd843`.
- Main fork and production runtime were not changed. This is a new milestone after
  spec 1012. The checked-in Spec Kit workflow was followed manually, with the spec
  committed before implementation.
- Coordinator owned configuration, installation, documentation and qualification;
  two workers owned the connector and HUD respectively. A separate verifier
  reviewed the integrated result. Delegates could not push, merge or operate services.

## Attempts and findings

**T001, complete:** confirmed accepted proposal 161, current upstream, unused spec
number and remote branch/PR inventory. Agreed the two-tool envelope and pinned service.

**T002/T003/T004, attempt 1:** implemented the connector, optional HUD and installation
surfaces. Independent review found missing native defaults, escaped credential
reflection in projected text, and incomplete registration instructions. All were
fixed with regression coverage. The final verifier reported no remaining blocker.

**T004, attempt 2, complete:** added the plan dispatcher and explicit stdio launch
declaration, updated inventory assertions additively, and checked safe defaults
exactly. Local tests initially rejected group-writable temporary fixtures under
umask 002. With umask 022, the existing core deployment tests passed without source
changes; ownership protections were not weakened. The installer and setup suites
passed, as did the full unit suite (156.29 seconds).

**T005, attempt 1:** the real summary passed, but evidence returned a compatibility
error. A private fixture diagnostic identified GoFlow2's named UDP/TCP protocol
field, which the new adapter had incorrectly treated as numeric-only.

**T005, attempt 2, complete locally:** accepted bounded protocol names and added a
regression without relaxing address, site, exporter or time-window checks. Both demo
and host paths passed through real export, retained storage, viewer-scoped generated
native MCP registration and Chromium. Repeat installation, wrong credential/site,
disable/reprojection, unrelated-setting preservation and restart persistence passed.
Demo produced two records; the host summary had 62 records and the later bounded
sample had 64 while traffic continued. Browser 156.0.8078.4 reported zero JavaScript
errors. Both screenshots were visually inspected.

**T006, attempt 1, complete:** independent review and local gates passed. Prepared source
release 1.15.0 and published [upstream PR #311](https://github.com/automateyournetwork/netclaw/pull/311).
All 40 hosted checks passed on implementation commit `3ca7b8b6`, including native
Linux amd64 and ARM64 demo/host integration. See the [integration run](https://github.com/automateyournetwork/netclaw/actions/runs/41150919562)
and [repository gates](https://github.com/automateyournetwork/netclaw/actions/runs/41150919451).
The final documentation commit will receive the same hosted checks before the PR
is marked ready. No tag, deployment or upstream merge has been performed.

## Reproducible local checks

Run from this checkout with umask 022. The contract runner's `--prepare` creates
isolated ignored environments; the integration needs Docker and Chromium.

| Check | Result |
|---|---|
| `tests/convergence-read/.venv/bin/python tests/convergence-read/test_connector.py` | PASS, 18 tests |
| `npm --prefix ui/netclaw-visual test` | PASS, 393 tests |
| `npm --prefix ui/netclaw-visual run build` | PASS |
| `python3 scripts/run-contract-tests.py --suite installer --prepare` | PASS |
| `python3 scripts/run-contract-tests.py --suite setup-installer --prepare` | PASS |
| `python3 scripts/run-contract-tests.py --suite unit --prepare` | PASS |
| `python3 -m unittest discover -s tests -p test_setup_catalog.py` | PASS, 9 tests |
| `python3 scripts/verify-spec-artifacts.py` | PASS, 145 specs and four legacy exceptions |
| `python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs --surface meraki-ids --surface packages --surface portability` | PASS, all six surfaces |
| `node scripts/build-catalog.mjs --check` and `python3 scripts/build-catalog.py --check` | PASS |
| `python3 scripts/check-catalog-metadata.py` and `python3 scripts/verify-catalog-coverage.py` | PASS |
| `python3 scripts/check-catalog-links.py --base-ref 4d791a364989405a98ac52bec91a9530cf4317b4 --output PRIVATE_REPORT` | PASS, no dead or unreviewed links |
| `python3 scripts/test-prepare-release.py` and `python3 scripts/prepare-release.py --check` | PASS |
| `git diff --check` | PASS |

Actual integration command (with `CONVERGENCE_PLAYWRIGHT_MODULE` selecting an
installed Playwright module and optional `CONVERGENCE_BROWSER_EXECUTABLE`):

```bash
tests/convergence-read/.venv/bin/python tests/convergence-read-integration/run-tests.py \
  --service-checkout /path/to/pinned/external-checkout \
  --evidence-dir /path/to/private/evidence
```

Local artifacts are in `~/.local/state/convergence-read-evidence`; logs are in
`~/.local/state/convergence-home-test/read-*.log`. Private diagnostic payloads,
connection files and credentials are not committed or uploaded. CI publishes only
fixture screenshots, sanitized reports and resource measurements. The harness
reuses the pinned service's disposable producer/cleanup fixture and replaces its
consumer callbacks; no service deployment code is imported into upstream.

## Qualification boundaries

Local Linux amd64 and hosted native amd64/arm64 integration passed. The tests
actually invoke generated native MCP entries with resolved private references.
They do not qualify a full OpenClaw gateway/model session, Hermes execution,
macOS, Windows/WSL2 or physical network capture. External service qualification
alone does not qualify this connector. Historical proposal 161 remains a proposal;
this spec owns the implementation and its evidence.
