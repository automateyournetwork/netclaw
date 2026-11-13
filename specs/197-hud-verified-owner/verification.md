# Verification

Design review run, 2026-11-13 04:17–05:02 UTC. Baseline cfafa46c. Attempt 1 of 3. The current HUD validates its installation-bound owner for built-in reads. A locally installed adapter has no supported interface for a verified owner. Acceptance for this proposal is a reviewable contract grounded in current source and denial behavior. Implementation and deployment require separate verification.

At the upstream baseline the following checks passed from ui/netclaw-visual after npm ci --ignore-scripts --no-audit --no-fund.

- node --test src/security/local-access.test.js src/hud-server/{bindings,convergence,open-lab-bindings,protected-operations,remote-hud}.test.js — 63 passed.
- node --test src/hud-server/{open-lab-workspace.integration,protected-server}.test.js — 15 passed, including HTTP denials and late revocation.

The tests describe today's host behavior. The proposed adapter, handler isolation, future browser workflows and candidate deployments still need their own qualification. No service was installed.

The proposal passed python3 scripts/verify-spec-artifacts.py, python3 scripts/verify-catalog-coverage.py and python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs --surface meraki-ids --surface packages --surface portability. Both python3 scripts/run-contract-tests.py --list and --matrix exited 2 because tests/gcp has no manifest entry. Both failures reproduced on a clean cfafa46c checkout.

## Downstream reviewer fixture

An isolated HTTPS fixture ran with two independent Chromium browser contexts and temporary certificates trusted only in that fixture. The API required a client certificate enrolled to the installation. The reviewer listener used the shared Convergence password verifier with two synthetic accounts. Browser sessions rotated at login. A viewer could read its authorized site; an operator disposition recorded that operator, duplicate case IDs at another site did not provide access, and signing one user out left the other session intact. A hostile-origin form POST reached the listener without a reviewer cookie and was denied before service dispatch. Missing trust, a bad hostname, missing or unenrolled client certificates, native owner/terminal routes, WebSocket upgrades, implicit HEAD and spoofed headers were rejected. The test used a minimal review document and in-memory grants, case data and audit. It does not qualify the actual HUD shell, deployment ingress, grant lifecycle across replicas or a production case mutation.

The candidate profile and downstream service contract are discussed in the [Convergence design](https://github.com/byrn-baker/convergence-platform/pull/8).
