# Feature Specification: Catalyst Center — official Cisco MCP server, curated

**Feature Branch**: `087-catalyst-center-official`
**Created**: 2026-08-04
**Status**: Draft
**Roadmap**: new item (operator-requested), Tier 1 adjacent — replaces existing Catalyst Center coverage

## Overview

Cisco has released a **first-party** Catalyst Center MCP server. NetClaw's existing Catalyst Center
coverage is a community server that is measurably worse in four ways, so this is a **replacement**, not a
new integration.

What is installed today:

| | Measured |
|---|---|
| Server | `catalyst-center-mcp` — 7 tools |
| Dependency pin | **`fastmcp>=0.1.0`, unbounded** → resolves 3.x, the conflict that blocked spec 083 |
| Git | **untracked** — 0 files under version control |
| Registration | **absent from `config/openclaw.json`** — installed on disk, never wired up |
| Licence | UNLICENSE (public domain) |

An integration that is unregistered, untracked and carrying the known dependency hazard is not a baseline
worth preserving.

## The central problem: 515 tools

`cisco-en-programmability/catc-mcp-oss` is genuine Cisco, **Apache-2.0** (licence-identical to NetClaw), and
actively developed — pushed 2026-08-03, the day before this spec. But:

| Configuration | Tools | Manifest | vs 5,000 ceiling |
|---|---|---|---|
| **Default bundle** | **515** | **64,420 tokens** | **12.9× over** |
| Curated directory (measured) | 10 | 2,827 tokens | **PASS** |

For scale, this project has previously rejected candidates at 53, 111, 237 and 313 tools. **515 is the
largest surface ever evaluated here**, and its manifest is thirteen times the entire budget.

So the feature is **not "adopt an MCP server."** It is **"curate one" — and the curation is the
engineering.** Everything else is plumbing.

### The curation mechanism exists, and needs no patching

Verified by reading the source and running the loader: `config.py:108` reads
**`CATALYST_CENTER_BUNDLED_TOOLS_DIR`**, and `tool_loader.load_tools(root)` accepts an arbitrary directory.

```
load_tools()            → 515 tools · 64,420 tokens
load_tools(curated/)    →  10 tools ·  2,827 tokens
```

**The vendored tree is never modified.** NetClaw supplies a directory of chosen tool definitions and points
the env var at it. That preserves the adopt-unmodified posture spec 083 established, while solving a problem
spec 083's candidate did not have.

At **~283 tokens per tool**, the ceiling supports roughly **15 tools with headroom**. The curated set must be
chosen, not accumulated.

## What the official server gets right, and one thing it does not

**Right:** of 515 tools, **513 are GET**. Only two mutate — one POST (`getApplicationPolicy`, misleadingly
named) and one DELETE (`complianceRemediation`). A Catalyst Center MCP surface that is 99.6% read is a
better starting posture than the roadmap's warnings about write tools implied.

**Not right:** the README states plainly that it

> *"does not add an authorization layer or enforce read-only access. The bundled catalog includes generated
> API operations and may include operations that change configuration."*

There is **no `--read-only` flag** — unlike spec 084's Kubernetes server, which enforced read-only at tool
registration. Safety here rests entirely on (a) which tools NetClaw includes in the curated directory, and
(b) the Catalyst Center account's own RBAC.

Both are usable controls. Curation is in fact the *stronger* of the two, because a tool absent from the
directory is not registered and cannot be called at all — the same structural property spec 084 relied on,
arrived at by a different route.

## Two structural surprises worth recording

**`main` contains no code.** Only governance files — README, LICENSE, CONTRIBUTING, `.github/`. The
implementation lives on **`release/<catalyst-version>` branches**; currently only `release/2.3.7.11`.
A shallow clone of the default branch yields nothing runnable, which will confuse anyone who tries.

**It is version-coupled by design.** The branch name *is* the supported Catalyst Center version, and the
manifest carries per-tool `min_controller_version` / `max_controller_version` with 19 tools excluded as
`unsupported_release`. Pinning a branch therefore pins a target appliance version — a real maintenance
consideration, not a detail.

**Transport is streamable HTTP on port 7001, not stdio.** Every other NetClaw MCP server is stdio. This one
ships a Dockerfile and `docker-compose.yaml` exposing `7001:7001`. That difference has to be handled at
registration rather than assumed away.

## The dependency hazard, and why Docker resolves it

`pyproject.toml` declares **`fastmcp>=2.0.0` — unbounded**. That resolves to fastmcp 3.x and reproduces
exactly the conflict that blocked spec 083's first candidate: five NetClaw servers pin `fastmcp<3`.

Running it **in its own container** makes the conflict structurally impossible — the same outcome spec 083
achieved with a dedicated virtualenv and spec 084 achieved with a static Go binary, by a third route. This
is now the third distinct isolation mechanism in the repo for the same recurring hazard.

## The sandbox is real, and the obvious host is the wrong one

| Host | Auth | Devices | Sites |
|---|---|---|---|
| `sandboxdnac2.cisco.com` | ✅ 200 | **0** | 1 |
| **`sandboxdnac.cisco.com`** | ✅ 200 | **4** | 25 |

Identical credentials. The `2` host authenticates cleanly and is **empty** — a device-inventory integration
verified against it would demonstrate nothing while appearing to work. **This is itself an instance of the
distinction below**, encountered before a line of code was written.

The working sandbox holds 4 × `C9KV-UADP-8P` on IOS-XE `17.12.1prd9`, all Reachable, across 25 sites, and
`POST /network-device` returns **403** — read-only by RBAC, which matches NetClaw's posture exactly.

## The distinction this feature exists to protect

### An empty inventory is not an empty network

This is the same family as specs 083 and 084 — an empty result that means something other than absence — and
it has already bitten once, on `sandboxdnac2`.

A Catalyst Center that returns zero devices may mean: nothing is onboarded; discovery has not run; the
account's RBAC scopes it to a site with no devices; the query hit the wrong appliance; or a filter excluded
everything. Reporting *"no devices"* for any of those is a factual claim the data does not support.

Catalyst Center makes this worse than the Kubernetes case in one specific way: it is a **controller with its
own database**, so an answer reflects *what Catalyst Center last learned*, not what the network is. A device
can be absent from inventory and perfectly operational, or present and long dead.

### "Catalyst Center says" is not "the device is"

`reachabilityStatus` is the controller's most recent polling result, not ground truth. A device shown
Unreachable may be fine and unreachable *from the controller*. This is spec 083's poller discipline and spec
084's vantage-point discipline, in a third setting — and it is why every answer must carry **when Catalyst
Center last observed it**, not merely what it says.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — What does Catalyst Center actually manage? (Priority: P1)

An engineer wants the device inventory with platform, software version, site and reachability — and needs to
know whether the answer is complete.

**Why this priority**: the foundational capability, the one the existing 7-tool server nominally covers, and
where the empty-inventory trap lives.

**Independent Test**: query inventory against the live sandbox; confirm 4 devices with platform and version;
then query the empty appliance and confirm the two answers are *worded differently*.

**Acceptance Scenarios**:

1. **Given** a populated Catalyst Center, **Then** devices are returned with hostname, platform, software
   version, site and reachability.
2. **Given** an appliance with **zero devices**, **Then** the answer says the controller manages no devices —
   distinct from *"no devices exist"* and distinct from *"the controller could not be reached"*.
3. **Given** any inventory answer, **Then** it states **which Catalyst Center answered** and **when the data
   was last observed**.
4. **Given** a device shown Unreachable, **Then** the answer attributes that to the controller's polling and
   does **not** assert the device is down.
5. **Given** an account whose RBAC scopes it to a subset, **Then** the answer says scope may be limited
   rather than presenting a partial inventory as complete.

---

### User Story 2 — Site hierarchy and where things are (Priority: P2)

An engineer wants the site tree and which devices sit where.

**Why this priority**: real and frequently needed, and the sandbox has 25 sites against 4 devices — a
genuinely useful asymmetry to reason about. Lower than US1 because a wrong site answer misleads less than a
wrong inventory answer.

**Acceptance Scenarios**:

1. **Given** a site hierarchy, **Then** sites are returned with their parent relationships.
2. **Given** a site with no devices, **Then** it is reported as empty rather than omitted — a site nobody has
   onboarded to is a finding.
3. **Given** 25 sites and 4 devices, **Then** the answer does not imply the remaining sites are broken.

---

### User Story 3 — Health and compliance (Priority: P3)

An engineer wants device health, client health and compliance state.

**Why this priority**: valuable, and the largest part of the 515-tool catalogue — but the most likely to
return thin or empty data on a shared sandbox, so it is the least verifiable and the first to cut.

**Acceptance Scenarios**:

1. **Given** health data exists, **Then** it is returned with the time it was computed.
2. **Given** health data is absent, **Then** the answer distinguishes *not collected* from *healthy*.
   **An absent health score is not a passing health score.**

---

### Edge Cases

- **The controller is unreachable** — distinct from empty, and from a credential failure.
- **The token expired.** Catalyst Center tokens are time-limited; expiry must not surface as empty data.
- **The wrong appliance.** Two sandbox hosts share credentials and one is empty. Which appliance answered
  must be visible in the answer.
- **A device in inventory that has been dead for months** — the controller still lists it. Staleness must be
  visible.
- **RBAC-scoped account** — a partial inventory that looks complete.
- **A tool not in the curated set** — refused clearly, naming what *is* available, rather than failing
  obscurely.
- **Version mismatch** — the pinned `release/*` branch targets one Catalyst Center version; a different
  appliance version may make tools fail or vanish.

## Requirements *(mandatory)*

### Curation — the core of this feature

- **FR-001**: The curated tool set MUST be supplied via **`CATALYST_CENTER_BUNDLED_TOOLS_DIR`**. The vendored
  upstream tree MUST NOT be modified.
- **FR-002**: The manifest MUST measure **≤ 5,000 tokens**, with the figure recorded. Default is 64,420.
- **FR-003**: The curated set MUST be **deliberately chosen and individually justified** — each tool
  present because a user story needs it, not because it looked useful. At ~283 tokens/tool the budget is
  ~15 tools; accumulation is not available.
- **FR-004**: Every tool in the curated set MUST be **read-only (GET)**. The two mutating tools MUST be
  excluded, and their exclusion recorded.
- **FR-005**: A test MUST assert the curated count and total, so an upstream bump or a careless addition that
  inflates the surface **fails loudly** rather than silently consuming context.
- **FR-006**: A request for a tool outside the curated set MUST be refused with a message naming what *is*
  available.

### The empty-inventory distinction

- **FR-007**: An empty inventory MUST NOT be reported as an empty network. **Zero devices means the
  controller manages none** — a statement about Catalyst Center, not about the network.
- **FR-008**: **Unreachable controller**, **credential failure**, **expired token** and **empty result** MUST
  be four distinguishable outcomes.
- **FR-009**: Every answer MUST state **which Catalyst Center answered**. Two sandbox hosts share credentials
  and differ in content; production estates have several controllers.
- **FR-010**: Every answer MUST carry **when the controller last observed the data**, distinct from when the
  query ran.
- **FR-011**: `reachabilityStatus` MUST be attributed to the controller's polling. An answer MUST NOT assert
  a device is down because Catalyst Center cannot reach it.
- **FR-012**: Where the account's RBAC may scope results, the answer MUST say scope may be limited rather
  than presenting a partial inventory as complete.
- **FR-013**: An absent health or compliance score MUST NOT be reported as a passing one.
- **FR-014**: A site with no devices MUST be reported as empty, not omitted.

### Adoption and isolation

- **FR-015**: The server MUST be pinned to a specific `release/<version>` branch and commit, recorded with
  the Catalyst Center version it targets.
- **FR-016**: That `main` carries **no code** MUST be recorded, so nobody clones the default branch and
  concludes the project is empty.
- **FR-017**: The **version coupling** MUST be documented — the branch pins a target appliance version, and
  19 tools are excluded as `unsupported_release`.
- **FR-018**: `fastmcp>=2.0.0` is **unbounded** and resolves to 3.x, conflicting with five servers pinning
  `<3`. It MUST therefore run **in its own container**, and that reason MUST be recorded so nobody
  "simplifies" it onto the host interpreter.
- **FR-019**: The container MUST be proven not to perturb the host interpreter: the five `<3`-pinned servers
  MUST still resolve afterwards.
- **FR-020**: Licence (**Apache-2.0**) MUST be recorded, with the vendoring posture.
- **FR-021**: The **HTTP-on-7001** transport MUST be handled explicitly at registration — every other
  NetClaw MCP server is stdio.

### Replacing the existing coverage

- **FR-022**: The existing `catalyst-center-mcp` MUST be **retired**, and the reasons recorded: 7 tools,
  unbounded `fastmcp>=0.1.0`, untracked, and **never registered in `config/openclaw.json`**.
- **FR-023**: `devnet-catalyst-search` (documentation search) is **unaffected** and MUST be preserved — it
  answers a different question.
- **FR-024**: Any skill referring to the old server MUST be repointed, and no reference to the retired server
  may remain.

### Security posture

- **FR-025**: A **least-privilege, read-only Catalyst Center account** MUST be documented as the supported
  deployment. The server enforces no authorization of its own.
- **FR-026**: Credentials MUST come from the environment, never a literal in any committed file.
- **FR-027**: That the server **does not enforce read-only** MUST be recorded as a known limitation, together
  with the two controls that do (curation, and account RBAC).
- **FR-028**: TLS verification MUST be configurable and its default recorded. The sandbox uses a
  self-signed certificate; disabling verification against production must be a conscious act.

### Dependencies and audit

- **FR-029**: Installation MUST use the repository's helpers; never bare `pip`/`pip3`, never bare
  `python3 -m venv` (spec 077, and both have failed on this host).
- **FR-030**: No shared dependency version may move (spec 076).
- **FR-031**: Whether per-call audit exists MUST be **established, not assumed** — spec 084's Complexity
  Tracking was wrong about exactly this, and a task existed to catch it.

### Artifact coherence (Principle XI)

- **FR-032**: All surfaces MUST be updated: registration; `catalog.sh` entry **and** curated profile
  membership; `install-steps.sh`; **both** HUD entries; `README.md` and `SOUL.md` including counts **and** a
  SOUL capability section; skills; `.env.example`; `TOOLS.md`; a server `README.md`; `.gitignore`.
- **FR-033**: `reconcile-mcp.py` MUST exit 0 across all four surfaces.
- **FR-034**: `verify-inventory-counts.py` MUST exit 0 with updated counts — noting the retirement means the
  MCP count may not simply increment.

### Boundaries

- **FR-035**: Against `pyats` / `multivendor-cli`: those read **the device**; this reads **what the
  controller believes**. When they disagree, the device is right and that MUST be stated.
- **FR-036**: Against `devnet-catalyst-search`: that searches **documentation**; this queries **an
  appliance**.
- **FR-037**: Against `netbox` / `nautobot`: those are **intended** state; this is **discovered** state.
  A device in Catalyst Center and not in NetBox is a reconciliation finding, not an error.

### Honest verification

- **FR-038**: On completion, the feature MUST state per capability what was **exercised against the live
  sandbox** versus what merely ran.
- **FR-039**: The **empty-appliance case MUST be exercised** against `sandboxdnac2`, since it is a free,
  real instance of the trap this feature exists to protect.
- **FR-040**: Anything not exercised MUST be marked unverified or cut. US3 is the likeliest cut.

### Key Entities

- **Controller answer** — a result plus which appliance produced it and when it last observed the data.
  Never a bare list.
- **Curated tool set** — the chosen subset, each entry justified, all read-only, measured against the ceiling.
- **Absence** — distinguishable causes: controller manages none · discovery not run · RBAC-scoped · wrong
  appliance · filter excluded all · controller unreachable · credential failure.
- **Reachability observation** — what the controller's polling last saw, at a stated time. Not device truth.

## Success Criteria *(mandatory)*

- **SC-001**: Device inventory retrieved from the live sandbox returns the **4 known devices** with platform
  `C9KV-UADP-8P` and version `17.12.1prd9`.
- **SC-002**: The **empty appliance** produces a different answer from the populated one, verified by
  wording, and neither reads as "no devices exist".
- **SC-003**: Unreachable controller, credential failure and empty result are three distinguishable outcomes.
- **SC-004**: Every answer names which Catalyst Center answered.
- **SC-005**: Every answer carries the controller's last-observed time, distinct from query time.
- **SC-006**: No answer asserts a device is down on the strength of `reachabilityStatus`.
- **SC-007**: Site hierarchy returns the 25 sandbox sites with parents; an empty site is shown, not omitted.
- **SC-008**: An absent health score is not reported as passing.
- **SC-009**: The curated manifest measures **≤ 5,000 tokens**, recorded, against a 64,420-token default.
- **SC-010**: Every curated tool is GET; the two mutating tools are absent and their exclusion recorded.
- **SC-011**: A test fails if the curated count or manifest size grows beyond the recorded values.
- **SC-012**: A tool outside the curated set is refused with a message naming what is available.
- **SC-013**: The vendored tree is byte-identical to the pinned upstream commit.
- **SC-014**: The container does not perturb the host interpreter — the five `<3`-pinned servers still
  resolve.
- **SC-015**: The old `catalyst-center-mcp` is retired with reasons recorded, and no reference remains.
- **SC-016**: `devnet-catalyst-search` still resolves.
- **SC-017**: No credential appears in any committed file.
- **SC-018**: `reconcile-mcp.py` exits 0; `verify-inventory-counts.py` exits 0; `trace-skill.py` resolves
  for every skill.
- **SC-019**: `SOUL.md` gains a capability section covering the empty-inventory and controller-vs-device
  distinctions — not merely a count change.
- **SC-020**: The candidate comparison, the 515→curated decision, and the version coupling are recorded in a
  shipped artifact.
- **SC-021**: A per-capability table distinguishes **exercised against the live sandbox** from **executed
  without error**.

## Assumptions

- **`catc-mcp-oss` `release/2.3.7.11` is the adoption target**, run in its own container, curated via
  `CATALYST_CENTER_BUNDLED_TOOLS_DIR` to ~15 read-only tools.
- **`sandboxdnac.cisco.com` is the verification appliance** — 4 devices, 25 sites, POST 403.
  `sandboxdnac2.cisco.com` is retained deliberately as the **empty-appliance test case**.
- **The sandbox credentials are public DevNet credentials**, not secrets — but they still go in the
  environment, never in a committed file.
- **Read-only by curation and RBAC**, since the server enforces neither. No write path is exposed.
- **No new persistent state.** The controller holds everything.

## Out of Scope

- **Any Catalyst Center mutation** — provisioning, templates, software image push, compliance remediation.
  The two mutating tools are excluded from the curated set.
- **The other ~500 tools.** Deliberately excluded; adding one is a decision with a token cost, not a
  convenience.
- **Assurance deep-dive, ThousandEyes-via-Catalyst, energy management** — large parts of the catalogue that
  no user story here needs.
- **Documentation search** — `devnet-catalyst-search` owns that and is unaffected.
- **Intended-state reconciliation** — `netbox`/`nautobot` own intent; this reports discovered state.
- **Meraki** — the operator's second requested item, deliberately a separate spec so its official server can
  be measured on its own terms.
