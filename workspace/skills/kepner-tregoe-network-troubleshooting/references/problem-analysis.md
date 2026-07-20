# Problem Analysis (PA) — full method

Use PA when there is a **deviation** (observed ≠ expected performance) and the **cause is unknown**.
Both conditions matter: no deviation → nothing to analyze; known cause → go to Decision Analysis.

Core insight: every deviation was produced by a **change**. Locate the change by first drawing a precise
**boundary** around the deviation, because the cause must lie exactly on that boundary. Find the boundary
and the candidate space collapses from "anything" to "only things consistent with this edge".

## The seven steps

1. **State the problem** — one object, one defect. "What is wrong with what." Two defects = two problems.
2. **Specify (IS / IS-NOT)** across WHAT / WHERE / WHEN / EXTENT. ~70% of the work.
3. **Identify distinctions** — what is different/odd/unique about the IS vs. the IS-NOT?
4. **Identify changes** — within each distinction, what changed and when?
5. **Generate possible causes** — from distinctions and changes only.
6. **Test each cause** against the full spec — does it explain the IS *and* the IS-NOT, with fewest assumptions?
7. **Verify** the most probable cause in the real world before fixing.

## Building the specification

Two columns. **IS** = where/when/how the problem appears. **IS-NOT** = the *nearest* comparable place,
time, or object where it could reasonably appear but does not. Choose IS-NOTs that are close (only one or
two variables differ) — distant comparisons teach nothing.

| Dimension | IS — ask | IS-NOT — the sharp comparison |
|---|---|---|
| **WHAT** | Which object has the defect? Which exact defect? | Which similar object could but doesn't? Which other defect could it have but doesn't? |
| **WHERE** | Where geographically / on the topology / in the object? Site, VLAN, interface, peer, zone, layer? | Where else could it appear but doesn't? Which comparable segments are clean? |
| **WHEN** | First seen? Time-of-day/week pattern? Point in a session/lifecycle? Last known-good? | When could it appear but doesn't? Which comparable time is clean? Before what date was it fine? |
| **EXTENT** | How many? How big? What proportion? Trend — stable/growing/shrinking? | How many unaffected? How big could it be but isn't? Not spreading? |

**Gather each cell with tools where possible** (interface counters, session/routing tables, logs, flow
data, config diffs, inventory). The IS-NOT is the part most engineers skip and the part that carries the
answer.

## Distinctions → changes → causes

- **Distinction**: what is peculiar about the IS side. (Site A fails, Site B clean, only difference is
  firmware 7.4.11 vs 7.2.8 → firmware is a distinction.)
- **Change**: within a distinction, what changed and when. (Site A upgraded on the 9th, fault started the
  10th → prime candidate.) Changes anchored to the WHEN boundary are the strongest leads.
- A candidate cause is **admissible only if it traces to a real distinction or change** on the affected side.

## Testing causes (the elimination engine)

For each candidate: *"If this is the cause, does it produce everything that IS and nothing that IS-NOT,
with the fewest assumptions?"*

- Explains IS but contradicts an IS-NOT → **eliminated**.
- Survives only by adding assumptions → ranked below one that survives cleanly.
- Most probable = fits the whole spec, no contradictions, no borrowed assumptions.

## Verify before fixing

Confirm with a log line, counter, table entry, or controlled (ideally read-only) test. Name the exact
check and expected result. Only then propose the fix. Then split: fast **reversible incident fix** now,
**permanent fix** as a separate decision (route to Decision Analysis if there are options).

## Hard cases

- **Multiple / interacting causes**: your best cause explains most of the spec but leaves one boundary
  unexplained and needs an assumption to fit. Don't accept the awkward fit — suspect a second cause
  (often a latent condition + a trigger, e.g. missing shaping + a traffic ramp). Re-specify the
  unexplained boundary as its own sub-problem.
- **Never-worked / greenfield**: no "was fine before" moment. Shift emphasis from WHEN (find the change)
  to WHERE/WHAT (find the difference from a working peer). The IS-NOT becomes an existing working
  instance; the distinction between it and the never-working one is the cause.

Rule of thumb: *deviation from known-good* → hunt the change (WHEN-anchored). *Greenfield* → hunt the
difference from a working peer (WHERE/WHAT-anchored). *One boundary unexplained* → suspect a second cause.

---

# Worked examples

Each shows the specification driving elimination. Compress your own records to the same shape.

## Example 1 — One SaaS app unreachable from one site

**Problem**: Pune branch (VLAN 30) — ERP app `erp.vendor-cloud.com` times out at TCP connect.

| Dim | IS | IS-NOT |
|---|---|---|
| WHAT | TCP connect to that one host times out; name resolves fine | Every other SaaS app works; not a DNS failure |
| WHERE | Only from Pune (local internet breakout via its own firewall) | Not from HQ/Mumbai/VPN (egress via central cluster) |
| WHEN | Since ~09:15 on the 10th, constant | Fine end of day on the 9th |
| EXTENT | 100% of attempts to that one IP from that one site; SYN sent, no SYN-ACK | 0% of other sites; 0% of other destinations from Pune |

Changes in window: (a) vendor rotated the ERP IP overnight; (b) Pune firewall threat/geo feed
auto-updated at 09:00. **Tested**: "app is down" contradicts other-sites-work (eliminated); MTU
blackhole contradicts failure-at-SYN (eliminated); vendor deny-list needs an unproven assumption (weak).
**Most probable**: Pune firewall's updated feed now blocks the new ERP IP — explains Pune-only
(independent egress), single-IP, SYN-dropped-with-DNS-fine, and the 09:00 timing, with zero assumptions.
**Verify**: firewall security log / flow trace shows a deny to the new IP; confirm the IP is in the
updated feed object. Fix (exempt destination / correct categorization) only after the log confirms.

## Example 2 — Intermittent packet loss on a WAN link

**Problem**: DC↔Bengaluru MPLS (WAN1) — bursts of 3–8% loss, minutes long, several times a day.

| Dim | IS | IS-NOT |
|---|---|---|
| WHAT | Packet drops | Zero CRC/input errors; link never goes fully down |
| WHERE | On WAN1 DC↔Bengaluru | LTE backup clean; sibling campuses clean; LAN clean |
| WHEN | Weekday business peaks (10–11, 14:30–15:30) | Never overnight/weekends (despite weekend replication) |
| EXTENT | 3–8% loss when utilization nears ~90% CIR | 0% loss below ~80% CIR; not growing week/week |

Zero-error IS-NOT eliminates physical (optic/fiber/duplex). Weekend-clean IS-NOT eliminates provider
fault. **Most probable**: congestion against CIR with no egress shaping — peaks hit the provider policer
and drop; weekend replication stays under CIR. **Verify**: correlate drops to utilization crossing CIR;
inspect egress queueing/shaping. Fix: shape to CIR with LLQ for voice — not a circuit swap, not a reboot.

## Example 3 — Subset of VLAN devices lose gateway after a change

**Problem**: ~half of VLAN 50 hosts lose off-subnet reachability after a distribution-switch change;
intra-VLAN L2 still works.

| Dim | IS | IS-NOT |
|---|---|---|
| WHAT | Gateway unreachable; L3 first-hop lost | Intra-VLAN L2 works; other VLANs fine |
| WHERE | Hosts using DSW-B as active gateway | DSW-A-active hosts fine; wired VLANs on same pair fine |
| WHEN | Since 22:40, at DSW-B reload in the window | Fine before; DSW-A (unchanged) fine |
| EXTENT | ~50% (the DSW-B share); stable | Other ~50% never lost connectivity |

The clean 50/50-by-gateway-role split is the fingerprint of a first-hop-redundancy (HSRP/VRRP) problem,
not L2 or STP (which would break intra-VLAN too). Change time-locks to the DSW-B reload. **Most
probable**: the change left the VLAN 50 SVI down / reset the FHRP virtual IP, so DSW-B wins active but
can't route ("active but black-holing"). **Verify**: `show` the SVI state and FHRP group on DSW-B vs
DSW-A. Fix the SVI/FHRP config — don't just fail everything to DSW-A (that masks a latent failover bug).

## Example 4 — Intermittent internal DNS resolution failures

**Problem**: Internal clients intermittently fail/slow to resolve internal zone names; external names fine.

| Dim | IS | IS-NOT |
|---|---|---|
| WHAT | SERVFAIL/timeout on internal zone, retry succeeds | External resolution fine; not NXDOMAIN; resolver pings fine |
| WHERE | Clients whose first resolver is DNS-SRV-2 | Clients hitting SRV-1 first are clean (tracks the server) |
| WHEN | Bursts, worse under business load; ~4 days | Rare overnight; fine before ~4 days ago |
| EXTENT | Minority of queries fail first attempt | Never total outage; external 0% failure |

Tracks SRV-2 specifically → server problem, not path/clients. Internal-fails-but-forwarding-works → zone
issue, not server-down. **Most probable**: SRV-2 has a stale/partial internal zone (failed transfer) or
overloaded recursion, SERVFAILing under load until the client retries SRV-1. **Verify**: query SRV-2
directly for internal names; compare zone serial to SRV-1; check transfer/recursion logs. Fix the
transfer — don't "restart DNS" or bump client timeouts (masks it as tolerable slowness).

## Example 5 — One-way traffic after a firewall policy change

**Problem**: A client↔DMZ flow: client→server arrives, server→client return dropped; sessions stall/RST.

| Dim | IS | IS-NOT |
|---|---|---|
| WHAT | One-way: forward ok, return dropped | Not a full block; not DNS/ARP; forward path clean |
| WHERE | Return dropped at the firewall DMZ↔user | Flows not crossing this firewall unaffected |
| WHEN | Since the 15:00 policy change, constant | Fine before; unchanged policies still pass return traffic |
| EXTENT | 100% of this app's return flows; matches changed policy scope | Flows outside the policy's match criteria fine |

Directionality (recorded explicitly) points at stateful-session handling, not routing. Server replies do
leave the server → eliminates server-side gateway problem. **Most probable**: the 15:00 edit broke
stateful session creation (changed service, removed NAT, narrowed match), so return traffic is
un-associated and dropped. Secondary: asymmetric routing to the passive firewall. **Verify**: session
table for the flow + flow debug drop reason on the changed policy.

## Example 6 — Wi-Fi clients dropping in one area

**Problem**: East-wing 3rd-floor clients associate, work briefly, drop; poor throughput while connected.

| Dim | IS | IS-NOT |
|---|---|---|
| WHAT | Assoc succeeds then drops; poor throughput | Auth succeeds (RADIUS accepts); not a "can't see SSID" issue |
| WHERE | East wing near two APs; 5 GHz worse than 2.4 | West wing/other floors clean |
| WHEN | ~1 week; worse afternoons; clustered drops | Fine two weeks ago; overnight clean |
| EXTENT | All client types in that zone; tied to a specific AP's channel changes | Only the east-wing pair; not site-wide |

Auth-succeeds IS-NOT eliminates RADIUS/cert. Location + band + channel-change signature → RF/DFS, not
controller-wide. **Most probable**: new 5 GHz interference / DFS radar hits forcing repeated channel
changes on the east-wing APs, causing drops/retries under load. **Verify**: AP/controller DFS
channel-change events + spectrum/interference report for that zone/time. Fix is RF (channel plan, AP
placement, remediate interference) — not RADIUS, not a reboot.

---

**Discipline reminders**: don't skip the IS-NOT; anchor causes to changes but test the recent change like
any other; count assumptions; verify before fixing; if nothing fits cleanly, the spec is incomplete —
re-specify.
