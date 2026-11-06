# Spec 176: Read-only Convergence VM Security findings in NetClaw

Created 2026-11-06; branch `176-convergence-vm-security`, on upstream 1.18.6
(`db0c9682`). **Status:** scope proposal. This specification contains no
implementation. It follows the path agreed for spec 161: a separate scope decision
first, then an implementation spec.

## Decision requested

Spec 161 accepted one read-only Convergence integration, retained flow evidence,
and said other observation types need their own scope proposal. Specs 162–167
implemented and qualified it.

This proposal asks for one more observation type: **advisory VM Security findings
from a separately operated Convergence service, shown read-only in NetClaw.** An
operator sees which virtual machines showed a possible port scan, network sweep or
contact with a protected network in the last five minutes, the evidence behind each,
and how complete the observation was.

**Maintainer decision:** does this bounded VM Security view belong in NetClaw, as an
extension of the existing optional `convergence-read` component?

The rest of the Convergence roadmap is context only. This proposal does not ask for
firewall or IDS summaries, guest heartbeats, raw hypervisor snapshots, case
workflows or any enforcement.

## What the service already does

Convergence's hypervisor observer runs on a Proxmox VE node, outside the guests. It
records each VM's network interfaces and samples guest-egress packet metadata. Its
analysis looks at the last 300 seconds and reports three advisory patterns per VM:

| Pattern | Default rule | Shown as |
|---|---|---|
| `port_scan` | 20 or more TCP destination ports on one address | Possible port scanning |
| `network_sweep` | 20 or more destination addresses on one TCP port | Possible network sweep |
| `protected_network_contact` | A monitored VM reached an operator-listed protected range | Protected network contact |

Every finding has severity `review`. The service never raises an alert, opens a case
or changes anything because of a finding. The response also carries coverage for
each source: freshness, capture drops, discarded events, snapshot gaps, sampling
and a list of limitations. The service contract is
[`VM-SECURITY-CONTRACT.md`](https://github.com/byrn-baker/netclaw-convergence/blob/024821c842616eb2d4997889064c74c4e7e716c5/services/ids-ingest/VM-SECURITY-CONTRACT.md).

## Why NetClaw, and what it adds

NetClaw can already analyse a capture file (`nsm-mcp`, spec 091), run active scans
(nmap) and query Grafana or Prometheus. None of these answers "which of my VMs is
behaving like a scanner right now, and how sure is that?" from continuous,
hypervisor-side observation. The existing Convergence view answers questions about
traffic volume, not VM behaviour.

The addition is small: one read tool and one panel, behind the connection,
credential and session controls that spec 162 already built and qualified.

## Ownership

| Concern | Owner |
|---|---|
| Hypervisor observer, packet sampling, analysis, retention, policy (protected ranges, allowlists) and the status credential | Convergence service and its operator |
| One read-only tool, response validation and the optional HUD panel | NetClaw `convergence-read` component |
| Endpoint, site and viewer credential on the NetClaw host | Operator; private, server-side, shared with the existing flow tools |
| A labeled synthetic VM Security source for the equipment-free demo | Convergence service (prerequisite, see US3) |
| Tests, fixtures and compatibility documentation in NetClaw | This contribution, maintained by contributor Brian Baker |

## User scenarios and acceptance

### US1: See advisory findings with their limits (P1)

An operator with the integration enabled opens the Convergence view and selects
**VM Security**.

1. For each configured source, the panel shows the node, status (reporting, stale
   or unknown), last contact, observation time and the five-minute window.
2. Each finding shows its pattern title, the VM id, first and last seen, the counts
   behind it (distinct destination ports, addresses, TCP five-tuples) and up to five
   example observations. The service's caveat for the finding is shown with it.
3. The source's assessment is worded as the contract defines it. `review` means
   patterns to look at. `no_patterns_observed` means no pattern in the sampled,
   covered traffic, never "safe" or "healthy". `insufficient_evidence` means the
   source cannot support either statement.
4. Coverage limits are shown next to the assessment: sampling, capture drops and
   discarded events (with "unknown" when a recent change cannot be computed), the
   largest gap between snapshots, VMs without a UUID, and the service's limitation
   text. A finding count that was truncated at 100 says so.
5. VMs that are stopped, unsupported or not observed are listed as coverage, not as
   clean results.

### US2: Distinguish states and keep credentials private (P1)

1. "Not configured", "unauthorized", "unavailable", "incompatible response" and
   "configured, no findings" are distinct states. A failed refresh marks earlier
   data as stale; it never becomes a fresh "no patterns".
2. The endpoint, site and viewer key are the existing `convergence-read` settings.
   No tool or HUD argument can choose another URL, site or path.
3. A response for another site is rejected even if the credential could read it.
4. The tool is read-only and takes no arguments. It cannot start a capture, change
   a policy or allowlist, open a case, send a notification, block traffic or call a
   model.

### US3: Try it without a hypervisor (P1)

Spec 161 required the first integration to be demonstrable on one Linux computer
with Docker and no special equipment. This one must be too.

1. The Convergence service provides a synthetic VM Security source. Its response
   identifies itself as synthetic, and NetClaw shows **Synthetic demonstration**
   above the findings.
2. The demo produces at least one finding of each default pattern and one
   insufficient-evidence source, so every state in US1 can be seen.
3. A real Proxmox VE observer is the only supported live source in this slice.
   Other hypervisors are "not configured", not "no patterns".

### US4: Enable, upgrade and disable predictably (P2)

1. The panel is hidden and the tool returns "disabled" when the integration is
   disabled, exactly as the flow view does today. An older Convergence service
   without the VM Security route yields "incompatible" or "not configured", never
   an error in the flow view.
2. Upgrading NetClaw keeps the existing private settings. No new credential or
   setting is required.

## Functional requirements

- **FR-001:** Add one tool, `convergence_vm_security()`, with no arguments, to the
  existing `convergence-read` component. It calls only `GET /api/security/vms` on
  the configured service, with the configured site.
- **FR-002:** Apply the existing transport rules: verified HTTPS (loopback HTTP only
  by explicit opt-in), no redirects or URL credentials, a 20-second deadline and a
  1 MiB decoded-response limit.
- **FR-003:** Validate the response against the pinned contract before returning
  it: enumerated states and patterns, bounded lists (100 findings, 5 examples each,
  256 VMs), consistent counts, timestamps inside the window, examples attributed to
  a listed VM interface, and the expected site. Anything else is "incompatible".
- **FR-004:** Return only the VM Security assessment. Drop the guest-heartbeat block
  the route also returns; it is outside this slice.
- **FR-005:** Add a HUD route, `GET /api/hud/convergence/vm-security`, behind the
  same trusted-origin and owned-session checks as the flow routes, calling the tool
  through the existing server-side MCP call. Render all service text escaped.
- **FR-006:** Any hand-off to the agent from this panel reuses the existing
  user-initiated hand-off. Nothing investigates automatically.
- **FR-007:** Update the `convergence-observations` skill, `docs/CONVERGENCE.md`,
  catalog counts and tests as the constitution requires.

## Success criteria

On a fresh upstream checkout with the integration configured against a disposable
service, an operator sees the synthetic findings, their evidence and their coverage
limits in the HUD, and every negative state in US2. Automated tests cover wrong
site, malformed and oversized responses, timeout, missing session, cross-origin
requests and a failed refresh. One recorded run against a real Proxmox VE observer
shows a live finding. Linux is the initial platform, as for spec 162.

## Explicit exclusions

No observer, analysis, packet capture, policy editing, allowlist changes, alerts,
cases, notifications, blocking, quarantine or other containment. No guest heartbeat
agent or status, raw hypervisor connection lists, firewall/IDS summaries or security
history. No severity beyond `review`, no attribution of a VM to a customer or owner,
and no claim that the absence of findings means a VM is safe.
