# R02 research and decisions

2026-11-02; source baseline5e50bbba. Independent read-only audits located reusable
transport/signing, authorization and evidence primitives but no end-to-end
protected OpenClaw member contract. These findings are not live qualification.

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| Add explicit opt-in protected operation profile | Avoid claiming legacy member scope is exact owner approval; preserve existing runtimes | Silently converting existing tasks, prompt-only approvals |
| Reuse pinned iN2N identities and P-256 signatures with domain separation | Existing trust chain; bind stable operation/member/model/tool/principal | Trusting certificate embedded in result or ngrok/DNS as identity |
| Atomically consume admission and separately claim executor/effect | Durable no-replay across processes/restarts | In-memory worker map or retry-on-timeout |
| Signed immutable member result and durable Border ACK | Distinguish completed tool from lost delivery | Model answer text or unsigned cached task as proof |
| Add explicit single-owner ticket/session for protected HUD | Existing nc_hud is conversation binding, not human login | Broad users/SSO advance, loopback-as-authentication |
| Separate agent, guard and broker authority | Existing inherited env/native API key storage cannot prove secret isolation | Giving agent provider or device secrets |
| Retain GAIT with structured principal and mandatory protected audit | Reuse audit; fail closed before effect and preserve uncertainty afterward | Parallel competing audit trail or fabricated success |
| Fresh Linux Docker qualification with explicit containment evidence | Mac-hosted systemd claims would be false | Fake systemd posture, unqualified Docker label |
| Two bounded model calls, one tool effect per operation | Allows proposal and final answer; authoritative result remains tool evidence | Unlimited model/tool retries |

Current runtime design pins official OpenClaw and DefenseClaw rather than importing
Thermidor implementation. DefenseClaw's official guarded custom-provider route
keeps upstream credentials only at the guard; scoped agent credentials authorize
only the guarded route. Fresh isolated agent network, mount/env constraints and
real negative tests must establish no directprovider/tool/host path. Runtime
adapter provides inspected containment evidence to the protected profile, never
misreports systemd confinement. Qualification refuses if any control cannot be
established. Exact pins/launch recipe are recorded before actual activation.

Ralph plugin is a Claude Code stop-hook integration, not a native Codex loop tool
in this session. Optional bounded implementation/test/independent-review passes
will be explicitly counted (maxfive total); no fake hook completion claims.

Known baseline gaps: execution_context and ExecutionBroker are Hermes-only;
OpenClaw lacks dispatch_started evidence; request-id lookup is edge-only;
GAIT lacksstructuredprincipal and allowslegacy auditdegradation; providerkeys are
inherited/written intonativeconfig; localHUDsession creates anonymousbinding.

Evidence sources: current repository service.py, authorization.py, execution.py,
tasks.py, gait.py, controls.py, HUDbindings/runtime/routes and specs165–170.
Private design audits: ~/.local/share/netclaw/roadmap-r02-r05-20261102/.
