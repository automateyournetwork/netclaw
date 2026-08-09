# Feature Specification: Fortinet Coverage (FortiOS / FortiManager / FortiAnalyzer)

**Feature Branch**: `080-fortinet-coverage`
**Created**: 2026-07-31
**Status**: Draft
**Roadmap**: R3 — *"Largest single-vendor absence"*. All three planes in the roadmap title are in scope.

## Overview

NetClaw currently advertises Fortinet capability it does not have.

`workspace/skills/fortimanager-ops/SKILL.md` is present, `user-invocable: true`, and declares
`FORTIMANAGER_MCP_CMD`, `FORTIMANAGER_HOST` and `FORTIMANAGER_API_TOKEN` as required. It names
`jmpijll/fortimanager-mcp` as its server. That server is **not vendored, not registered in
`config/openclaw.json` (92 entries, zero Fortinet), not in the installer catalog, and not obtainable by
anyone who installs NetClaw**. `migration-staging/members/fortimanager/` compounds it: an iN2N member
whose `.env` exports `FORTIMANAGER_MCP_CMD` pointing at the same command that was never installed.

This is worse than a missing integration. A missing integration is silent. An unbacked skill is a
**claim** — an agent reading `SOUL.md` sees Fortinet coverage, routes a firewall-policy question to
`fortimanager-ops`, and discovers the gap only when the first tool call cannot execute. The failure
surfaces at the worst possible moment: inside an operator's real question.

Fortinet is NetClaw's largest single-vendor absence by installed base. This feature closes it with a
server that actually ships, and back-fills the skill against what that server really exposes.

## The distinction this feature exists to protect

Fortinet is not one plane. It is four, and they are not substitutes for one another:

| Plane | The question it answers | What NetClaw has today |
|---|---|---|
| **Device CLI** | "What is this box doing *right now*, in its own words?" | ✅ Spec 076 — netmiko `fortinet` driver, read-only, filtered |
| **Device API** (FortiOS REST) | "Give me this box's config and state as *structured objects*." | ❌ Nothing |
| **Manager** (FortiManager) | "What policy is *intended* across the estate?" — ADOMs, policy packages, shared objects, install targets, revisions | ❌ Nothing |
| **Analyzer** (FortiAnalyzer) | "What traffic *actually hit* that policy?" — logs, hit counts, events | ❌ Nothing |

Spec 076 gives NetClaw genuine, safety-filtered CLI reach to FortiOS. That is real and it is not nothing —
but the R1 outcome note already recorded the caveat verbatim: *"That is not FortiManager's policy packages.
R3 is still needed."*

**The failure mode this feature protects against is treating any one plane as the whole truth.**

A rule that exists on a FortiGate but not in its FortiManager policy package is an out-of-band change —
invisible if you read only the manager, and invisible *as a divergence* if you read only the device.
FortiManager's policy database is **intent**; the FortiGate's running config is **state**; they legitimately
diverge between installs, and the gap between them is exactly where drift, unauthorised change and failed
installs live. A hit count of zero on a rule is a FortiAnalyzer question, not a FortiManager one — the
manager knows a rule exists, only the analyzer knows nobody ever matched it.

This is the same shape of error as spec 078's *"no advisories ≠ not vulnerable"* and spec 079's
*"no probes found ≠ outage"*, and it gets the same treatment: the planes are named separately, every answer
is attributed to the plane it came from, and NetClaw is required to say which plane it did **not** consult.

## A composition that is already designed and currently broken

`workspace/skills/fwrule-analyzer/SKILL.md` ships a **FortiOS/FortiGate parser** (contributed upstream by
NetClaw itself) and documents the pairing explicitly:

> `fortimanager-ops` — FortiManager policy export + fwrule FortiOS parser for cross-VDOM analysis

That composition cannot execute today, because the left-hand side has no server. Closing R3 does not just
add Fortinet — it completes a cross-skill workflow NetClaw already claims to support.

## Clarifications

### Session 2026-07-31

- Q: What live Fortinet endpoint will this feature be verified against? → A: A local lab — **FortiGate-VM on containerlab's `fortinet_fortigate` kind under the permanent free evaluation licence, plus FortiManager-VM on Hyper-V under its 15-day full-featured trial.** Manager and device planes are live-verified; FortiAnalyzer cut from scope. ⚠️ **Superseded 2026-08-01** — see the final bullet in this session; the analyzer cut rested on an unverified premise and was reversed.
- Q: How is the tool-manifest budget of FR-026 quantified, given one candidate ships 200+ tools? → A: A **fixed ceiling of 5,000 tokens** for the entire registered tool manifest, measured and recorded. Exceeding it forces a filtered or lazy tool surface.
- Q: Where is plane attribution enforced — in the tool responses or in skill prose? → A: **Structurally.** Every tool response carries an explicit `plane` field and its scope. Documentation alone is unenforceable; a field is assertable in a test.
- Q: One skill covering both planes, or one skill per plane? → A: **One skill per plane** — `fortimanager-ops` back-filled for the manager plane, a new `fortigate-ops` for the device plane. Each stays single-purpose per Principle VII, and the existing `fortimanager-ops` name keeps working for the six documents that already reference it. *(Became three skills on 2026-08-01 when the analyzer plane was restored — the rule is per-plane, so `fortianalyzer-ops` follows from it.)*
- Q: Is the stale `migration-staging/members/fortimanager/` iN2N member repaired or removed? → A: **Repaired**, by regeneration rather than hand-editing, once a real command exists.
- Q: (2026-08-01, reversing the Q1 cut) Is FortiAnalyzer actually obtainable? → A: **Yes — restored to scope.** FortiAnalyzer-VM ships a free, full-featured **15-day trial, built in, no activation required**, supporting 6 GB/day of logs. All three planes are reachable from one free FortiCare account, so R3 ships at the roadmap's full scope. A third skill, `fortianalyzer-ops`, follows from the Q4 one-skill-per-plane rule.

> **A cut made on an unverified assumption, now reversed.** The Q1 answer dropped FortiAnalyzer on the
> premise that no analyzer was obtainable. That premise was never checked — it was extrapolated from the
> FortiManager trial without confirming the analyzer had a different one. It does not: FortiAnalyzer-VM's
> trial is the same free 15-day full-featured pattern. The scope reduction was therefore unjustified, and
> the analyzer plane, its user story, and its requirements are restored. **Reaching a scope decision
> through an unverified assumption is the exact failure FR-035/FR-036 exist to prevent**, and it happened
> inside the process meant to prevent it.

> **Licence-clock sequencing, binding on the plan.** FortiGate-VM's licence is *permanent*; FortiManager's
> and FortiAnalyzer's are **15 days from first boot**. The lab MUST therefore be built in two stages —
> FortiGate first, developed against indefinitely; FortiManager and FortiAnalyzer booted only once the
> server is ready to verify. Booting all three at the start would spend the verification window on
> implementation.

> **A premise corrected during this session.** The member was initially characterised as carrying a
> spec-075-class machine-specific-path bug. It does not. `migration-staging/` is **untracked in git**, and
> **all 27 members** hardcode the same absolute home path because they are *generated* files. The path is
> the generator's convention, not damage, and no installer ever sees it. Only the dangling
> `FORTIMANAGER_MCP_CMD` reference is a real defect. FR-003 is scoped accordingly — and it is explicitly
> **not** an installability requirement, since untracked local state cannot affect a fresh install.

> **Consequence of the structural answer, carried into planning:** no community server emits a `plane`
> field. Satisfying FR-005 therefore requires either a NetClaw-authored server or a NetClaw-authored
> wrapper over an adopted one. Adopting a community server *unmodified* is no longer an available option.
> This narrows — but does not decide — the build-vs-adopt question, which remains Phase 0 research.

**Research that produced this answer** (2026-07-31), recorded so it is not repeated:

- **Fortinet operates no hosted developer sandbox with API access.** The Demo Center is a request-a-demo
  form leading to guided walkthroughs — registration required, no published credentials, **no API**. A
  GUI-only console cannot verify an MCP server. "FortiSandbox" is Fortinet's malware-detonation appliance,
  not a developer environment; the term is a false friend.
- **The FortiGate-VM 15-day trial no longer exists.** Since FortiOS 7.2.1 it is a **permanent free**
  evaluation licence requiring only a free FortiCloud account, and it now permits HTTPS admin access
  (previously HTTP-only), so the REST API is reachable. It is capped at **1 vCPU, 2 GB RAM, 3 interfaces,
  3 routes and 3 firewall policies**, one licence per FortiCloud account.
- **FortiManager-VM's trial is 15 days, full-featured, capped at 3 managed devices** — a cap on *devices*,
  not on rules per policy package. Manager-plane policy volume is therefore unconstrained.
- Rejected alternatives: **FortiManager Cloud** (real SaaS with real JSON-RPC and a 30-day trial, but still
  requires a registered FortiGate underneath); **public-cloud PAYG** (uncapped and genuinely cloud-hosted,
  but costs money and is self-deployed, not Fortinet-hosted); **NSE training labs** (paid, course-bound,
  not API-oriented).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The unbacked skill answers a real question (Priority: P1)

An operator asks NetClaw to audit the firewall policy governing a site. NetClaw invokes
`fortimanager-ops`, reaches a FortiManager, and returns the ADOM, the policy package, the matching rules
and the objects those rules reference — instead of failing on a command that was never installed.

**Why this priority**: This is the entire premise of R3. Every other story is reach into an additional
plane; this one converts an advertised capability from false to true. If only this ships, the roadmap item
has delivered its headline value.

**Independent Test**: run the skill's declared workflow end to end against a reachable FortiManager and
confirm each step returns real data; then confirm the skill's declared env vars and tool names match what
the shipped server actually exposes.

**Acceptance Scenarios**:

1. **Given** a reachable FortiManager, **When** the operator asks which ADOMs and managed devices exist,
   **Then** NetClaw returns them from the manager, each attributed to the manager plane.
2. **Given** an ADOM and a policy package, **When** the operator asks for the rules matching a source,
   destination or service, **Then** NetClaw returns the matching rules with their position, action and the
   named objects they reference.
3. **Given** a rule that references an address group, **When** the operator asks what that group contains,
   **Then** NetClaw resolves the group to its members rather than reporting the group name alone.
4. **Given** the skill's `SKILL.md`, **When** its declared MCP command, environment variables and tool
   names are compared against the shipped server, **Then** they match exactly — no name in the skill is
   absent from the server, and no required variable is undeclared.
5. **Given** a fresh NetClaw install, **When** the operator selects the Fortinet component, **Then** the
   server is installed and registered without any manual step not covered by the installer.

---

### User Story 2 — Device-plane state, including VPN tunnels (Priority: P2)

An operator asks whether a site-to-site tunnel is up. That is a device question — the manager knows the
tunnel was *configured*, only the FortiGate knows whether it is *established*.

**Why this priority**: VPN tunnel status is named in the roadmap checklist and is the most common Fortinet
operational question the manager plane structurally cannot answer. It is also the clearest demonstration
that intent and state are different things.

**Independent Test**: query IPsec tunnel state on a reachable FortiGate and confirm phase-1 and phase-2
status are reported separately, with the device named.

**Acceptance Scenarios**:

1. **Given** a reachable FortiGate, **When** the operator asks for tunnel status, **Then** NetClaw reports
   each tunnel's phase-1 and phase-2 state separately, because a tunnel with phase 1 up and phase 2 down is
   neither "up" nor "down".
2. **Given** a reachable FortiGate, **When** the operator asks for system status, interfaces, routes or
   sessions, **Then** NetClaw returns them as structured data attributed to the device plane.
3. **Given** a device configured in FortiManager but unreachable directly, **When** a device-plane question
   is asked, **Then** NetClaw states that the device did not answer and MUST NOT substitute the manager's
   intended configuration as if it were observed state.
4. **Given** an HA pair, **When** device state is reported, **Then** NetClaw names which cluster member
   answered.

---

### User Story 3 — Writes are gated by two distinct gates (Priority: P2)

An operator wants a policy package installed. NetClaw does not install it on being asked.

**Why this priority**: FortiManager's `install` operation pushes policy to production firewalls — the
highest-blast-radius action in this feature by a wide margin. Spec 076's `/speckit.analyze` pass caught
exactly the error this story exists to prevent: a plan that claimed ITSM gating was "inherited from the
existing approval path". **Human approval and an approved ServiceNow change record are two different
gates.** Neither substitutes for the other.

**Independent Test**: attempt a write with each gate independently absent and confirm it is refused both
times, naming the specific gate that was missing.

**Acceptance Scenarios**:

1. **Given** the default configuration, **When** any write, install or config-changing operation is
   attempted, **Then** it is refused, because read-only is the default and writes are opt-in.
2. **Given** writes enabled and human approval given but **no** approved ServiceNow CR, **When** an install
   is attempted, **Then** it is refused and the refusal names the missing CR specifically.
3. **Given** writes enabled and an approved CR but **no** human approval, **When** an install is attempted,
   **Then** it is refused and the refusal names the missing human approval specifically.
4. **Given** both gates satisfied, **When** an install proceeds, **Then** a baseline is captured before the
   change and the result is verified against expected state afterwards (Principles II and VIII).
5. **Given** any write attempt — permitted or refused — **When** it completes, **Then** a GAIT record
   exists for it (Principle IV).
6. **Given** a preview capability exists, **When** the operator asks what an install *would* do, **Then**
   the preview runs without either gate, because a preview changes nothing.

---

### User Story 4 — FortiAnalyzer: what actually hit the policy (Priority: P3)

A rule exists and looks correct. The operator asks whether anything has ever matched it.

**Why this priority**: named in the roadmap checklist, and the only plane that can answer "is this rule
dead?" — the manager knows a rule exists, only the analyzer knows nobody ever matched it. P3 because it
depends on a FortiAnalyzer being deployed, which many estates do not have, and because its verification
window is the most constrained.

**Independent Test**: query traffic logs for a known policy over a bounded window and confirm results are
attributed to the analyzer, with the time window stated.

**Acceptance Scenarios**:

1. **Given** a reachable FortiAnalyzer, **When** the operator asks which sessions matched a policy in a
   stated window, **Then** NetClaw returns log entries with the window it actually queried.
2. **Given** a query returning no entries, **When** NetClaw reports it, **Then** it states that **no logs
   matched in that window** — never that the rule is unused, because absence of logs within a retention
   window is not proof of absence of traffic.
3. **Given** a log query with no bounded time window, **When** it is issued, **Then** NetClaw applies and
   states a default bound rather than requesting unbounded history.

---

### Edge Cases

- **The manager and the device disagree.** A rule present on the FortiGate is absent from its policy
  package. NetClaw reports the divergence as a finding attributed to both planes — it does not silently
  prefer one.
- **A plane is unreachable.** Only some of FortiManager / FortiGate / FortiAnalyzer answer. NetClaw answers
  from what responded and states plainly which plane it could not consult.
- **A configured rule with no logs.** "Nothing matched this rule in the queried window" MUST NOT become
  "this rule is unused". A configured rule is not a used rule, and a retention window is not all of history.
- **The advertised server does not exist or does not work.** If the chosen candidate proves unmaintained,
  broken or unable to authenticate, the feature is rescoped honestly — following spec 078's precedent, where
  four of five API families returned 403 and the spec was cut to the one that worked rather than shipping
  claims never exercised.
- **A very large tool manifest.** A server exposing 200+ typed tools loads that manifest into every
  conversation. Adopted unfiltered, it consumes context budget on every turn regardless of whether Fortinet
  is in play.
- **Multi-VDOM.** A FortiGate with VDOMs enabled returns per-VDOM results; a figure reported without its
  VDOM is ambiguous.
- **ADOM scoping.** A policy-package name is only unique within an ADOM. A package named without its ADOM
  is ambiguous.
- **Credentials absent.** A missing variable is reported **by name, never by value**.
- **Session/token expiry.** FortiManager sessions expire. Expiry is reported as an authentication condition
  to re-establish, never as "the device has no policies".
- **Certificate trust.** Fortinet appliances commonly present self-signed certificates. Whether verification
  is relaxed MUST be an explicit, documented, per-deployment choice — never a silent default.

## Requirements *(mandatory)*

### Functional Requirements

#### Backing the existing claim

- **FR-001**: A Fortinet MCP server MUST be obtainable by anyone installing NetClaw — vendored and
  registered, or documented as an on-demand install with installer coverage. "Present on the maintainer's
  machine" does not satisfy this.
- **FR-002**: `workspace/skills/fortimanager-ops/SKILL.md` MUST be back-filled so that every MCP command,
  environment variable and tool name it declares matches what the shipped server actually exposes. No
  declared name may be absent from the server. The skill **keeps its name** — `SOUL.md`, `SOUL-SKILLS.md`,
  `README.md`, `fwrule-analyzer/SKILL.md` and the roadmap all reference it, and renaming would break six
  working cross-references to fix nothing.
- **FR-002a**: A new `workspace/skills/fortigate-ops/SKILL.md` (device plane) and a new
  `workspace/skills/fortianalyzer-ops/SKILL.md` (analyzer plane) MUST be added. `fortimanager-ops` MUST NOT
  absorb their work: the three are different functions against different appliances with different
  credentials, and one skill doing all three would strain Principle VII and mislead routing. Each skill
  MUST state which plane it owns and name the other two as the route for the planes it does not own.
- **FR-003**: The `migration-staging/members/fortimanager/` iN2N member MUST be **regenerated** so its
  `FORTIMANAGER_MCP_CMD` resolves to the shipped command, and MUST then start successfully. It MUST NOT be
  left pointing at a command that was never installed.
- **FR-003a**: FR-003 MUST be satisfied by **re-running the member generator**, not by hand-editing the
  file. The directory is untracked generated state and all 27 members share the same generated shape; a
  hand-edit would diverge one member from its generator and be silently overwritten on the next run.
- **FR-003b**: FR-003 is **local hygiene, not installability**. The directory is untracked, so it cannot
  affect a fresh install and MUST NOT be counted toward FR-001. The generated absolute home path shared by
  all 27 members is the generator's convention and is explicitly **out of scope** — it is not a
  spec-075 portability defect and MUST NOT be "fixed" here.
- **FR-004**: The entry point is **all three planes — manager, device and analyzer**. This decision and its
  reasoning MUST be recorded in the shipped documentation, so a later roadmap item does not re-litigate it.

#### Plane attribution — the core of this feature

- **FR-005**: Every tool response MUST carry an explicit `plane` field whose value is `manager` (intent),
  `device` (observed state) or `analyzer` (observed traffic). This is a **structural property of the
  response, not a documentation convention** — prose in a `SKILL.md` is a request to the model, whereas a
  field is a guarantee that survives paraphrase and is assertable in a test.
- **FR-005a**: Because no known community server emits such a field, FR-005 MUST be satisfied by
  NetClaw-authored code — either a server or a wrapper over an adopted one. Registering a community server
  unmodified does not satisfy this requirement.
- **FR-006**: NetClaw MUST NOT present manager-plane configuration as observed device state, nor device
  state as estate-wide intent.
- **FR-007**: When a question spans planes and one plane is unreachable, NetClaw MUST answer from what
  responded **and state which plane it could not consult**. Silent partial answers are prohibited.
- **FR-008**: Where both manager and device data are available for the same policy, NetClaw MUST be able to
  report a divergence between them as a finding rather than resolving it silently.
- **FR-009**: Every response MUST additionally carry the scope that makes it unambiguous, in structured
  form alongside `plane`: **ADOM** for manager-plane responses, **device and VDOM** for device-plane
  responses, **time window** for analyzer-plane responses. A response that cannot name its scope MUST be an
  error rather than an unqualified result.

#### Manager plane

- **FR-010**: NetClaw MUST be able to enumerate ADOMs and the devices managed within them.
- **FR-011**: NetClaw MUST be able to list policy packages within an ADOM and retrieve the rules in a
  package, including position, action and enabled/disabled state.
- **FR-012**: NetClaw MUST be able to search rules by source, destination, service or object reference.
- **FR-013**: NetClaw MUST be able to resolve address objects, service objects and groups to their members
  — a rule reported only by object name is not an audit.
- **FR-014**: NetClaw MUST be able to retrieve revision history and install status for a policy package, so
  a change review has rollback context.

#### Device plane

- **FR-015**: NetClaw MUST be able to retrieve FortiGate system status, interfaces and routing state as
  structured data.
- **FR-016**: NetClaw MUST be able to report IPsec VPN tunnel status with **phase 1 and phase 2 reported
  separately**.
- **FR-017**: Where a FortiGate is in an HA cluster, results MUST name the answering member.
- **FR-018**: Device-plane results MUST be reported per VDOM where VDOMs are enabled.

#### Analyzer plane

- **FR-018a**: NetClaw MUST be able to query FortiAnalyzer traffic and event logs filtered by policy,
  address or service within a bounded time window.
- **FR-018b**: Every log query MUST state the time window it covered. An empty result MUST be reported as
  "no logs matched in this window", never as "this rule is unused" — absence of logs within a retention
  window is not proof of absence of traffic.
- **FR-018c**: A log query issued without a window MUST apply a stated default bound rather than requesting
  unbounded history.

#### Read-only default and the two gates

- **FR-019**: Read-only MUST be the default posture. Writes, installs and config changes MUST be disabled
  unless explicitly enabled by the operator.
- **FR-020**: When writes are enabled, every write MUST require **both** an explicit human approval **and**
  an approved ServiceNow change record. These are two distinct gates; satisfying one MUST NOT satisfy the
  other.
- **FR-020a**: A refusal MUST name **which** gate was missing. "Not authorised" is insufficient.
- **FR-021**: Policy-package install MUST be treated as production change execution: baseline captured
  before, state verified after, rollback context (revision) identified in advance (Principles II and VIII).
- **FR-022**: A read-only *preview* of what an install would do MUST NOT require either gate, because it
  changes nothing — and MUST be clearly distinguished from the install itself.
- **FR-023**: Every Fortinet operation, read or write, permitted or refused, MUST produce a GAIT record
  (Principle IV).
- **FR-024**: Lab-mode devices MAY be modified without a CR, but MUST still be GAIT-logged and MUST still
  require human approval (Principle III). The FortiGate-VM and FortiManager-VM of the verification lab are
  lab-mode devices.

#### Tool-surface budget

- **FR-025**: The token cost of the Fortinet tool manifest MUST be measured before adoption and recorded as
  a number. The measurement is the token count of the server's serialised `tools/list` response — every
  tool name, description and input schema that a client loads — counted with the Anthropic SDK's
  `count_tokens`, the method feature 006 established and the `token-tracker` skill documents.
- **FR-026**: The registered manifest MUST NOT exceed **5,000 tokens**. This is a hard ceiling, not a
  guideline: the manifest is loaded into *every* conversation whether or not Fortinet is in play, so its
  cost is paid by every unrelated task. Roughly 2.5% of a 200k window, it accommodates a 20–40 tool manager
  + device surface comfortably and excludes an unfiltered 200+ tool manifest by design.
- **FR-026a**: If a candidate server exceeds the ceiling, the tool surface MUST be filtered or made lazy
  before adoption. Exceeding it is not a reason to abandon a server, but it MUST NOT be registered whole.
- **FR-027**: The measured figure, the ceiling, and any filtering rule — including **which tools were
  excluded and why** — MUST be documented, so a later maintainer can see what was traded away and can
  re-measure after a server upgrade changes the manifest.

#### Credentials and transport

- **FR-028**: All Fortinet credentials MUST be supplied via environment variables, never in YAML, committed
  files or the config (Principle XIII). `.env.example` MUST document the variable names with descriptions
  and no values.
- **FR-029**: A missing or invalid credential MUST be reported by variable name, never by value. No token,
  API key, session ID or password may appear in NetClaw output, logs or GAIT records.
- **FR-030**: Certificate verification behaviour MUST be explicit and documented. If verification can be
  relaxed for self-signed appliance certificates, it MUST be an opt-in, per-deployment setting that is never
  the silent default. The verification lab's appliances present self-signed certificates, so this path is
  exercised rather than theoretical.

#### Composition boundaries

- **FR-031**: The boundary against spec 076's multivendor CLI driver MUST be stated: that driver reaches
  FortiOS **CLI** and is the right tool for raw command output; this feature reaches the structured API and
  manager planes. Neither replaces the other.
- **FR-032**: The composition with `fwrule-analyzer` MUST be made real: policy retrieved through this
  feature MUST be usable as input to the existing FortiOS parser for overlap, shadowing and conflict
  analysis — the pairing that skill already documents but cannot currently execute.
- **FR-033**: The boundary against `servicenow-change-workflow` MUST be stated as the CR gate of FR-020, not
  as a general integration note.
- **FR-034**: The three skills MUST compose rather than overlap: a "is this rule dead?" question routes
  manager → analyzer, and a "is intent matching reality?" question routes manager → device. Each skill MUST
  name the others for the planes it does not own, so a cross-plane question is routed rather than answered
  from the wrong plane.

#### Honest verification reporting

- **FR-035**: On completion, the feature MUST state explicitly, capability by capability, **what was
  exercised against the verification lab** and **what could only be verified statically**.
- **FR-036**: Any capability that could not be exercised MUST be recorded as unverified, or the scope cut to
  exclude it. Claiming coverage that was never exercised is prohibited — this is spec 078's precedent, where
  four of five API families were dropped after returning 403 rather than being shipped as claims.
- **FR-036a**: The verification lab MUST be committed as a reproducible topology, following spec 076's
  `labs/multivendor-r1/` precedent, so a later maintainer can re-run the evidence rather than trust it.
  Licences and credentials are obtained by the operator and MUST NOT be committed.

#### Artifact coherence (Principle XI)

- **FR-037**: All of the following MUST be updated, none assumed: `config/openclaw.json` registration with
  **repo-relative paths** (or an `EXTERNAL_INTEGRATIONS` entry with a stated reason); `scripts/lib/catalog.sh`
  entry **and curated install-profile membership**; `scripts/lib/install-steps.sh` install function; **both**
  HUD entries in `ui/netclaw-visual/server.js` (node list *and* annotation map — one without the other
  renders nothing); `README.md` and `SOUL.md` including the counts; a `SOUL.md` **capability section**, not
  merely a bumped count; **all three** `SKILL.md` files (`fortimanager-ops` back-filled, `fortigate-ops`
  and `fortianalyzer-ops` new); `.env.example` (names only); `TOOLS.md`; and a server `README.md`.
- **FR-038**: `python3 scripts/reconcile-mcp.py` MUST exit 0 across all four surfaces.
- **FR-039**: `python3 scripts/verify-inventory-counts.py` MUST exit 0 with the counts updated from the
  current 204 skills / 152 integrations. Skills becomes **206** (`fortigate-ops` and `fortianalyzer-ops`
  added; `fortimanager-ops` already counted); the integration count rises by however many servers are
  registered.
- **FR-040**: `python3 scripts/trace-skill.py` MUST resolve for **all three** of `fortimanager-ops`,
  `fortigate-ops` and `fortianalyzer-ops` — the specific check that would have caught this feature's
  premise long ago.
- **FR-041**: Any dependency pin on a package whose submodule is imported MUST be upper-bounded, and
  installation MUST use `netclaw_pip_install`, never a bare `pip`/`pip3` (spec 077).

### Key Entities

- **ADOM** — a FortiManager administrative domain. The scope within which a policy-package name is unique.
- **Policy package** — an ordered ruleset held in FortiManager as **intent**, assigned to install targets and
  pushed to devices. Distinct from what is running on any device.
- **Managed device** — a FortiGate known to FortiManager, with an install status and revision history.
- **VDOM** — a virtual domain within a FortiGate. Device-plane results are per VDOM.
- **Object** — an address, service or group referenced by rules. A rule is only auditable once its objects
  are resolved to members.
- **Revision** — a point-in-time snapshot of a policy package. The rollback context for FR-021.
- **Tunnel** — an IPsec VPN association with independent phase-1 and phase-2 state.
- **Log entry** — an analyzer-plane record that a session matched a policy, always qualified by the time
  window it was found in. Evidence of use; its absence is not evidence of disuse.
- **Plane** — one of `manager` (intent), `device` (observed state) or `analyzer` (observed traffic). Every
  response carries one, structurally (FR-005).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `python3 scripts/trace-skill.py` resolves for all three of `fortimanager-ops`,
  `fortigate-ops` and `fortianalyzer-ops`; each skill's declared command, environment variables and tool
  names all match the shipped server, and each names the others as the route for the planes it does not own.
- **SC-002**: A fresh installer run can select and install the Fortinet component with no manual step
  outside the installer.
- **SC-002a**: **Every** tool response returned during verification carries a `plane` field valued
  `manager`, `device` or `analyzer`, and the scope required by FR-009 — asserted mechanically across all
  tools, not spot-checked. A response missing either is a failure.
- **SC-002b**: The regenerated `migration-staging/members/fortimanager/` member starts successfully and its
  `FORTIMANAGER_MCP_CMD` resolves to a command that exists.
- **SC-003**: ADOMs, managed devices, policy packages and package rules are retrieved from a real
  FortiManager, with the ADOM named on every result.
- **SC-004**: A rule referencing an address group is reported with the group resolved to its members.
- **SC-005**: A policy package's revision history and install status are retrieved and usable as rollback
  context.
- **SC-006**: IPsec tunnel status is reported from a real FortiGate with phase 1 and phase 2 stated
  separately.
- **SC-007**: A device-plane question about an unreachable device is answered as "the device did not
  respond", with no manager-plane configuration substituted for observed state.
- **SC-007a**: A FortiAnalyzer log query returns entries with the queried window stated; an empty result
  reads as "no logs matched in this window", not "the rule is unused".
- **SC-008**: With writes disabled, every write, install and config-changing operation is refused.
- **SC-009**: With writes enabled, an install is refused when human approval is absent and refused when an
  approved ServiceNow CR is absent — **each refusal naming the specific missing gate** — and succeeds only
  when both are present.
- **SC-010**: A read-only install preview runs without either gate and is clearly labelled as not having
  changed anything.
- **SC-011**: Every Fortinet operation performed during verification has a corresponding GAIT record.
- **SC-012**: No credential value appears in any NetClaw output, log or GAIT record; a missing credential is
  reported by variable name.
- **SC-013**: The registered Fortinet tool manifest measures **≤ 5,000 tokens**, with the measured figure
  recorded; if filtering was applied to reach it, the filtering rule and the excluded tools are documented.
- **SC-014**: Policy retrieved through this feature is accepted as input by `fwrule-analyzer`'s FortiOS
  parser, completing the pairing that skill already documents.
- **SC-015**: The skills state the boundary against spec 076's CLI driver, state that manager intent and
  device state are different things, and route cross-plane questions to the plane that owns them.
- **SC-016**: A per-capability verification table exists distinguishing **live-exercised** from
  **static-only**, with anything unexercised either marked unverified or removed from scope.
- **SC-017**: The verification lab is committed as a reproducible topology containing no licences or
  credentials, and a later maintainer can rebuild it from what is in the repository.
- **SC-018**: `python3 scripts/reconcile-mcp.py` exits 0 across all four surfaces.
- **SC-019**: `python3 scripts/verify-inventory-counts.py` exits 0 with updated counts.
- **SC-020**: `SOUL.md` gains a capability section describing what NetClaw can now do with Fortinet and its
  routing boundaries — not only an incremented count.

## Assumptions

- **All candidate servers are community, none Fortinet-endorsed.** The roadmap names
  `ivillagomez/fortigate-mcp` (read-only FortiGate + FortiAnalyzer, best default safety posture),
  `rstierli/fortimanager-mcp` (FortiManager JSON-RPC), and `paoloamato2/fortinet-mcp-server` (FortiOS 7.6.6
  REST as 200+ typed tools). Which — or whether to build instead, as spec 076 chose to — is a research
  decision for planning, evaluated against maintenance status, safety posture, tool-manifest cost and
  credential handling. This spec states the capability required, not the repository that supplies it.
- **Writes are in scope but disabled by default**, following spec 076's precedent of shipping gated writes
  with real CR checking rather than deferring them. If the adopted server is read-only by construction, the
  write requirements (FR-019–FR-024) become a documented boundary instead of an implementation.
- **The verification lab is three Hyper-V VMs** — FortiGate, FortiManager, FortiAnalyzer — from one free
  FortiCare account. **containerlab was dropped** once the FortiGate was deployed on Hyper-V: it has
  exactly one Fortinet kind (`fortinet_fortigate`) and none for the other two planes, so it could never
  have covered the lab. The FortiGate is live at `192.168.2.130` running **FortiOS v8.0.0**, newer than
  any community reference server targets. Four consequences shape the plan:
  - **The FortiGate-VM licence caps the device at 3 interfaces, 3 routes and 3 firewall policies.** This
    constrains what can be *installed onto* the device — it does **not** constrain FortiManager, whose trial
    caps managed *devices* at 3 and places no limit on rules per policy package. Manager-plane policy audit
    and the `fwrule-analyzer` composition (SC-004, SC-014) are therefore verifiable at realistic rule
    counts; only device-plane installs are small.
  - **Analyzer verification will be real but thin.** With 3 policies on the FortiGate, log volume and
    diversity are limited. Enough to prove a policy-filtered, window-bounded query returns attributed
    entries; not enough to exercise log scale. SC-007a is scoped to the former.
  - **Two licence clocks, one permanent.** FortiGate is permanent; FortiManager and FortiAnalyzer are
    **15 days from first boot**. The lab MUST be staged: FortiGate first and developed against
    indefinitely, FMG and FAZ booted only when the server is ready to verify. This is a hard sequencing
    constraint on task ordering, not a preference. Importing the VMs does not start the clock — only
    powering them on does.
  - **The reference servers all target older FortiOS.** `paoloamato2` pins to 7.6.6; the lab runs 8.0.0.
    Endpoint knowledge borrowed from the community repos MUST be re-verified against v8 rather than
    trusted, which strengthens the build-over-adopt decision rather than undermining it.
- **containerlab's `fortinet_fortigate` kind is version-sensitive.** It was tested against v7.0.14, which
  carries the old self-contained eval; v7.2.0 and later require FortiCloud activation and internet access at
  boot. Which version the lab pins is a Phase 0 research decision.
- **Spec 076's FortiOS CLI reach stays as it is.** This feature does not modify the multivendor CLI driver.
- **`fwrule-analyzer`'s FortiOS parser is consumed as-is.** This feature supplies it input; it does not
  change the parser.

## Out of Scope

- **FortiOS CLI access** — already delivered by spec 076. This feature is the API and manager planes.
- **Firewall rule overlap/shadowing analysis** — already delivered by `fwrule-analyzer`. This feature feeds
  it and MUST NOT duplicate it (Principle VII).
- **The wider Fortinet Security Fabric** — FortiSIEM, FortiEDR, FortiNAC, FortiSwitch/FortiAP management,
  FortiWeb, FortiSASE. Each is a separate product with its own API and belongs to a later roadmap item.
- **Palo Alto PAN-OS / Panorama** — that is R4.
- **Automated remediation.** Nothing here proposes NetClaw authoring firewall rules on its own initiative.
- **Ongoing policy-drift monitoring.** FR-008 makes divergence *reportable on request*; continuous drift
  detection is a scheduling concern, not this feature.
