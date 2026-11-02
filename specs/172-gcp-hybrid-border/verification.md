# R03 verification — source complete in part, live gate open

2026-11-02. R03 is **not100%** and has not been deployed or accepted. Source
implementation is on `172-gcp-hybrid-border`, preserving accepted R02 and R01.
No version/release/public cloud rollout is authorized. Human acceptance gatesR04.

## Implemented and tested

| Area | Evidence | Limit |
|---|---|---|
| Immutable device selector |54 focused tests; exact complete model/tool selection, Cartesian catalog coverage, concurrent isolation, permanent drift latch, old single-runtime dispatch | Synthetic files/executor seams; no new device read |
| Production owner HUD |49 focused tests,35 related Dashboard/Hermes tests,9 actual Chrome checks with4 synthetic operations; secure cookies/CSP/ID recovery/parsed-result projection | Local self-signed TLS/Node proxy, not public CA/Caddy/GCP |
| Border activation/posture |Independent source review closed whole-profile drift and Python import-boundary findings;33 focused role/Border tests | Actual base-image/stdlib/ancestor permissions and VM confinement pending |
| Integrated protected/legacy posture |414 tests passed,2 existing utcnow warnings; subsequent strict pyvenv duplicate-setting test separately passed | No provider/device/cloud effects |
| Transport/service regression |82 tests passed,13 existing utcnow warnings | Local fixtures/two-daemon loopback; not public ingress |
| Full HUD source suite |453 tests passed serialized; production Vite build passed | Existing bundle-size warning; no cloud deployment |
| Cloud infrastructure/host source |20 focused tests;53 integrated cloud/role tests plus23 subtests; OpenTofu schema/format, actual Caddy and Ubuntu systemd validation | Not applied; actual GCP quota/boot/rate enforcement pending |
| Protected enrollment |41 focused tests passed independently;77 focused integrated tests;464 full protected/posture tests | Actual cloud enrollment pending; no executor/legacy bootstrap permitted |
| Offline LinuxAMD64 dependencies |Fresh network-disabled, non-root extraction accepted immutable venv; real TLS1.3/exporter/SAN checks; Node/Express/Caddy/Git checks pass | Actual GCP package delta, base OS and kernel compatibility pending |
| First-create cloud staging |Actual offline install/replay refusal/no-executor factory/certificate/asset proofs; independent archive/source audit passes | Prepared identity has never listened or been uploaded; cloud activation pending |
| Private member/evidence helpers |Builder37, worker21, snapshot adapter10, receipt core25 tests pass; independent reviews complete | Synthetic helper tests and actual host-input validation; no actual protected operation |

Commits: `af0f855e` design; `a7367bca` selector; `ff11d713` HUD;
`398346e9` control-only role/service/posture; `cb0846f0` and `685032b9` cloud
source/expiry; `5843d6ae` strict enrollment contract; `aa861ee3` enrollment source.
Source lanes are integrated; final whole-packet live evidence remains pending.
Shared implementation pass3 source/preparation is complete; actual activation is
gated. No automatic Ralph hook, two prior passes used byR02.

Independent review corrected: source/runtime drift across an awaited effect
permission; whole private-profile edits including Border binding; untrusted
Python import startup; incomplete nested role metadata; unsupported cloud-member
activation; duplicate pyvenv system-site setting. Initial integrated run had15
fixture failures because OperationPair copied a signed expiry into catalog limits.
The fixture now matches the actual R02 five-field catalog; all audit/recovery
assertions are retained and all414 checks pass. No validator was weakened.
Independent enrollment review also closed remote RpcError traceback disclosure;
the CLI now returns bounded generic errors even for token-echoing remote failures.
The expanded combined464-test run exposed an older posture-test import containing
`..`, causing115 source-pin fixture refusals. Canonicalizing that test's import
path preserves the production validator; all464 now pass. The failed run remains
private evidence. Existing utcnow deprecation warnings remain.

## Live dependencies and remaining evidence

- Python TCP probes returned **No route to host**, but native nc/curl reach the
  same CML controller and R1/R2 SSH endpoints. The Python result does not establish
  that CML is down; its cause is unverified. Authenticated pinned-TLS CML metadata
  reports all four exact saved nodes BOOTED. The saved switch addresses were wrong;
  authenticated CML configuration and actual SSH interface output now agree on
  their corrected addresses, retained privately. Original inventories are unchanged.
- R1's actual console public key matches the SSH endpoint. R2/SW1/SW2 use existing
  owner known_hosts trust continuity plus authenticated exact-node CML metadata.
  Strict SSH verified the retained pin before credentials; expected hostname#,
  actual up/up interface/address and returned RSA key all match. Their historical
  pin establishment is undocumented; these are explicitly **not console proofs**.
  All diagnostics used only `show ip interface brief` and
  `show crypto key mypubkey rsa`, with no implicit enable, reconnect, configuration,
  node lifecycle or model call. These are prequalification reads, not the four
  future protected show-version acceptance operations. Fresh profiles still need
  actual cloud identity/enrollment inputs.
- Account CAD prices and resource inventory are verified, but current gross
  accrued billing is unavailable through connected tools. Owner billing/currency/
  tax confirmation is pending. CAD100 total ceiling remains a hard gate.
- R01's existing public egress has no proven finite allowance. NewR03 controls
  alone cannot establish a hard total ceiling for both deployments. Any R01
  traffic-bound/retirement change needs its own exact reviewed delegation.
  The optional single-VM stop in cost-bound-review.md is prepared, not executed;
  owner choice is pending and R01 remains running.
- Fresh resource apply, exact runtime/DNS/secret activation, GCP quota/boot/rate
  enforcement, actual HTTPS owner tests, four native reads, live recovery,
  independent signed evidence and reviewed teardown have not occurred.
- New guard source must be qualified on the actual selected GCP kernel/network
  manager. Docker Desktop lacks NFT_QUOTA; its refusal is preserved and cannot
  count as successful quota enforcement. No unbounded fallback is authorized.

## Private evidence and preservation

Private root: `~/.local/share/netclaw/roadmap-r03-20261102/`.
`integrated-protected-pass3.log` retains the failed fixture run;
`integrated-protected-pass3-corrected.log`, `transport-service-regressions.log`,
`hud-unit-serialized.log`, `hud-build-integrated.log`,
`hud-browser-pass3/browser-report.json` and screenshot retain actual results.
`role-source-review-pass3.json` contains independent reviewed hashes and limits;
`role-import-boundary-probe.json` is the harmless local startup-injection proof.
Pricing/inventory/research files contain sanitized metadata, not credentials.
`integrated-protected-enrollment-pass3-canonical.log` records464 passing tests;
`enrollment-independent-review.json` binds independent review to actual source
hashes. `offline-runtime-preparation.md` and
`offline-runtime-20261102/offline-verification-final.json` describe public-dependency
payloads only. Use artifacts-export, never the retained incomplete artifacts copy.
`cml-readonly/` retains failed console attempts, successful R1 console evidence and
distinct R2/SW1/SW2 trusted-SSH evidence. No failed probe was relabeled successful.
`cloud-runtime-staging/README.md`, `prepared-file-manifest.json` and
`independent-audit.json` bind the intended first-activation identity, original
private state and all upload/source/asset hashes. See runtime-review.md for its
preservation and actual-state activation gates. All owned offline test containers
are removed. Source1.18.3/extension1.5.0 remain unchanged.

No existing runtime, source inventory, R01 state, DNS or cloud resource has been
changed. R02 unknown/spent operations and earlier qualification failures remain
intact. Source changes are unreleased; documentation is maintainer-only.
