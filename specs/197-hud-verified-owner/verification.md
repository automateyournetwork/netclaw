# Verification

Design review run, 2026-11-13 04:17–05:02 UTC. Baseline cfafa46c. Attempt 1 of 3. The current HUD validates its installation-bound owner for built-in reads. A locally installed adapter has no supported interface for a verified owner. Acceptance for this proposal is a reviewable contract grounded in current source and denial behavior. Implementation and deployment require separate verification.

At the upstream baseline the following checks passed from ui/netclaw-visual after npm ci --ignore-scripts --no-audit --no-fund.

- node --test src/security/local-access.test.js src/hud-server/{bindings,convergence,open-lab-bindings,protected-operations,remote-hud}.test.js — 63 passed.
- node --test src/hud-server/{open-lab-workspace.integration,protected-server}.test.js — 15 passed, including HTTP denials and late revocation.

The tests describe today's host behavior. The proposed adapter, handler isolation, future browser workflows and candidate deployments still need their own qualification. No service was installed.

The proposal passed python3 scripts/verify-spec-artifacts.py, python3 scripts/verify-catalog-coverage.py and python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs --surface meraki-ids --surface packages --surface portability. Both python3 scripts/run-contract-tests.py --list and --matrix exited 2 because tests/gcp has no manifest entry. Both failures reproduced on a clean cfafa46c checkout.
