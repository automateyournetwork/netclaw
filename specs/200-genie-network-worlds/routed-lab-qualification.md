# Owner-requested routed CML lab — 2026-11-22

The owner explicitly expanded the earlier six-port discovery request to a routed
lab across R1, R2, SW1 and SW2. This supersedes the previous pending port-enable
question. It does not authorize hosted private-data export or establish Google
world acceptance. Exact addresses, wiring, configuration, credentials and raw
evidence remain in ignored private storage.

## Applied design and current evidence

- R1/R2 use a /31 point-to-point transit and separate /32 loopbacks. OSPF process
  200, area 0 carries the transit and loopbacks, with passive-by-default operation.
- AS65000 iBGP peers between loopbacks, using next-hop-self and explicit local
  export/remote import prefix filters. Each peer advertises its two VLAN networks.
- R1/SW1 provide router-on-stick VLAN10/20; R2/SW2 provide VLAN30/40. Actual CML
  PC-facing ports receive the corresponding access VLANs. Trunks have explicit
  VLAN allowlists, unused native VLAN999 and DTP disabled.
- Existing Rapid-PVST is retained. Each switch is root for its local data VLANs
  at priority4096. Host access ports and the routing-only uplinks use PortFast
  and BPDU Guard. This uplink policy is specific to router-on-stick; it is not a
  policy for an inter-switch trunk. No BPDU filtering is configured.
- CDP/LLDP operate on the data ports. Management interface configuration and its
  discovery exclusions are unchanged. The pre-existing management default route
  is retained; no static data routes were added.

Actual post-change evidence passed 78 checks: management and unrelated
configuration preservation; exact reciprocal CDP/LLDP endpoint pairs on the three
inter-device links; OSPF FULL; two received iBGP prefixes per peer; remote VLAN
routes installed through BGP; loopback routes through OSPF; trunk/access VLANs;
and STP roots, forwarding and configured protections. Eight five-packet probes
all returned 100%, including local and cross-site reachability to the running PC1.

All four native save attempts succeeded once after fresh running-baseline
comparisons. Actual startup readbacks confirm persistence. The first comparison
flagged an existing storage representation difference: running configuration
contains the certificate inline; startup configuration references its NVRAM file.
Each startup certificate block exactly matches its own pre-save baseline, while
all remaining configuration matches verified running state after display/timestamp
normalization. This exception is explicit in `persistence-verdict.json`; no
certificate or trust setting was changed to make the comparison pass.

PC2–PC4 were not running in the inspected CML state. Their bootstrap addressing
matches the chosen VLANs, but bootstrap is intended state and switch carrier-up
is not host reachability. Their host acceptance remains open. No CML node lifecycle
operation was performed.

## Change records and retained failure

The selected endpoints were explicitly registered in an isolated Local/Lab HTTP
API policy. The existing repository change-policy/execution service checked
actual baseline and rollback artifacts and issued APPLY PHASE before native MCP
writes. Existing owner runtime policies were not altered. The foreground
coordinator transported real native tool reports; this is not a fresh NetClaw
agent/provider acceptance demonstration.

1. Initial record `759a7696-f743-45ce-82ac-3ca4cfd182c3`: the installed IOL-L2
   rejected `spanning-tree portfast edge trunk` on SW1. Native scoped rollback
   restored its full normalized running configuration and VLAN database to the
   actual baseline. No other device was configured. The API timed out and its
   **uncertain** status is preserved; independent readback reconciliation records
   the actual completed rollback and absence of an outstanding writer.
2. Corrected record `99f8ab49-5143-4406-87b5-63170d017749`: compatible legacy
   PortFast syntax and a shorter VLAN name were frozen in a new reviewed plan.
   All four candidates completed once, with fresh baseline comparison before each
   push. The bounded report ended **blocked pending verification/persistence**
   before its HTTP response deadline. The writer had exited; no candidate was
   replayed. Subsequent actual postchecks passed as documented above.
3. Save-only record `b8dd6992-891f-4fc7-82fa-fcaf7e440f2e`: actual verified running
   and original startup configurations form the new baseline. Its API-issued
   APPLY PHASE authorizes one native save per device after another running-state
   comparison, followed by actual startup readback. The API recorded **completed**
   after persistence verification. Its temporary policy was disabled and owned
   service stopped. The initial and corrected-apply historical statuses are
   retained unchanged; completed verification/persistence is linked separately.

Native calls use the installed pyATS/Genie/Unicon runtime, existing strict SSH
pins, isolated private testbeds and no implicit setup configuration. There is no
raw SSH configuration fallback or expanded collector write scope.

## Evidence and collection contract

Private evidence roots are `.spec200-local/routed-lab/` (initial failure and
verified rollback), `.spec200-local/routed-lab-v2/` (corrected apply and behavior)
and `.spec200-local/routed-lab-save/` (persistence). Directories/files are0700/0600.
`core-verdict.json` retains checks and source hashes; native results and raw logs
remain local. API states are retained as observed, not rewritten to make history
look successful.

Actual bounded waves include28 core reads, eight probes plus four pre-save startup
reads, four additional running-baseline comparisons before saving, four startup
readbacks and24 final protocol/counter requests. The last wave completed24/24:
18 parsed, four raw-only (router prefix lists and switch trunk STP details), and
two empty raw results for the switch err-disabled query. Empty raw output is not
silently promoted to a parsed zero. Separate full interface status and STP
evidence retain their own conclusions. Both routers explicitly report OSPF
point-to-point and BGP Established; both switches report zero inconsistent STP
ports. Actual raw trunk detail reports BPDU Guard enabled.

All four devices have two parsed interface-counter samples, with at least10s
between the first logical request finishing and the second starting. Observed
input/output/CRC error counters are zero where supplied. Request intervals do
not establish exact counter acquisition instants or qualified device/interface
continuity, so derived rates and utilization remain unavailable. The private
`final-recollection-summary.json` retains field values, source hashes, intervals
and parser outcomes. No counters were cleared and no perpetual polling remains.

The [complete command table](collection-commands.md) includes OSPF, BGP, routing,
router-on-stick, VLAN/trunk/access, STP, discovery, counters, endpoint correlations,
configuration audit and bounded probes. It is a role-scoped catalog, not a claim
that every listed command has been executed or that the six-read source collector
has already been expanded. Frozen batch manifests identify actual requests.
Native parser fallback can execute again; logical-request counts do not prove
capture-once behavior. Counter samples alone do not establish valid rates.

The next product step remains the reviewed synthetic direct Google-world trial.
The API client and planning skill contract are retained; an execution MCP,
installed skill, generated navigable world and fictional event acceptance are
still unqualified. No local renderer is reinstated by this network work.
