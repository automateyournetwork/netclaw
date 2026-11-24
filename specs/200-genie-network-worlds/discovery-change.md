# Discovery and routed CML lab

The owner authorized and expanded the earlier six-port request. The routed lab
is applied and behavioral checks pass. See [current qualification](routed-lab-qualification.md)
for persistence, actual reciprocal neighbors, retained failures and host limits.
The pre-change shutdown/empty-neighbor findings below are historical.


## Owner correction and actual device recheck — 2026-11-22

Supersedes the Python-only reachability conclusions above. Native curl/nc reached
CML and all four endpoints while the selected Python socket probe returned errno65.
The native result was already documented as a platform caveat in TOOLS.md; it was
missed. A Python probe alone must not be used to declare the lab inaccessible.
Certificate-verified authenticated CML returned ready=true, version 2.10.0+build.13.
Fresh selected native pyATS MCP attempt03 completed 16/16 baseline/status requests
across R1/R2/SW1/SW2 with strict existing SSH pins and no configuration setup.

All four `show cdp` results report CDPv2 enabled; all four `show lldp` results
report active/enabled. Running configurations plus authenticated controller wiring
identify Ethernet0/0 as management. All four management ports already contain
`no cdp enable`, `no lldp transmit`, `no lldp receive`. No configuration change is
needed for the owner's protocol/exclusion request, and no configuration was applied.

Ethernet0/1–0/3 on all four devices are administratively shut down. CML has three
inter-device links; its intended wiring is not observed CDP/LLDP adjacency.
A concrete six-port no-shutdown delta and shutdown rollback are prepared privately
in discovery-change/data-links-review.json. Owner choice is pending. Existing
change-control requirements still apply before any write; management and unrelated
host-facing ports are excluded from that candidate.

Fresh recollection completed 24/24 logical native show-tool requests: version,
interface summary, LLDP detail, CDP detail and two interface-counter samples per
device separated by at least 10 seconds. All LLDP tables report zero entries.
CDP detail returned raw-only output; preserve parser failure/fallback provenance.
The native wrapper may execute again after parse failure, so this is not a claim
of 24 wire commands, capture-once collector qualification or valid derived rates.
Private baselines/topology/output: .spec200-local/discovery-change/attempt-03/,
cml-current/, recollection-01/ and correction-summary.json. No private Google upload.

The owner rejected local-rendered worlds. Active SVG/3D pages/routes and their
renderer-only tests are archived under .spec200-local/rejected-renderer/; the old
preview process is stopped. Retained API/media/fact code passes 53/53 serial Node
checks with actual Chrome and zero skips. This differs from the historical 60-test
suite because seven rejected-renderer tests were retired, not passed or concealed.
No actual Google world, installed skill or execution MCP is claimed. The old paid
packet is stale and unauthorized; current acceptance is defined in
[direction-correction.md](direction-correction.md).


## Historical attempts (retained)

# Owner-requested discovery configuration — pending connectivity

On2026-11-22 the owner explicitly requested enabling CDP/LLDP on R1,R2,SW1,SW2,
excluding management ports,and recollecting. This supersedes the earlier absence
of device-change intent for this scoped request;existing change-control rules apply.

No device configuration has been applied. Native selected-runtime inventory
listed all four aliases. Fresh running-config baselines failed before a usable
SSH prompt;direct bounded TCP checks then found all four SSH endpoints and the
CML controller unreachable. The controller probe returned errno65,No route to host,
with the route usingen0. Controller/node down state is not inferred from reachability.
The owner has been asked whether network/VPN/controller addressing changed.

The ordinary NetClaw connector returned an internal error. Existing running local
HUD change-policy endpoints were inspected read-only:neither selected API had
Local/Lab enabled or any authorized endpoints. Do not apply a configuration through
another route to bypass this gate. First restore reachability,capture genuine
baseline,and identify management interfaces using actual config/addressing plus
controller wiring. Then prepare exact deltas/rollback and the supported Local/Lab
record/authorization. Never guess management ports from names or enable discovery
on them transiently. Keep collector grants read-only.

Baselines use native pyATS MCP tools,not rawSSH helpers. The selected server's
explicit run_stdio_async path is qualified despite outdated fleet skill wording
that describes only the managed HTTP entrypoint. SDK2.3CallToolResult uses is_error,
not isError. An initial temporary testbed merge omitted inherited global credentials;
corrected by retaining the existing private credentials per device. Neither failed
client setup nor failed transport is device execution success. No secrets printed.

Private evidence and failed attempts:.spec200-local/discovery-change/ and attempt-02/.
Only metadata and hashes may leave that private boundary;raw configuration/topology
must remain local. No actual baseline/config/neighbor proof exists for this request.
Loop control device_operations is coordinator-only while this operation is pending;
source/offline passes continue. No source commit,release or cloud lifecycle action.

Relevant primary command references:
- https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/application-services/b-application-services/m_ce-lldp-multivend.html
- https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/syst-mgmt/b-system-management/m_nm-cdp-discover-xe.html

A bounded TCP-only recheck at2026-11-22T19:55:12Z still returned errno65,
No route to host,for the controller and all four selected endpoints. No SSH
session,device command or configuration retry was issued. Private evidence:
.spec200-local/discovery-change/reachability-recheck-03.json. Reachability remains
the prerequisite for a new baseline attempt; earlier failures are retained.

A further bounded TCP-only check at2026-11-22T20:53:47Z returned the same errno65
for the controller and all four endpoints. No SSH/device/config retry occurred.
Private evidence:.spec200-local/discovery-change/reachability-recheck-04.json.
The requested CDP/LLDP change and actual recollection remain unexecuted.

Final coordinator TCP-only check at2026-11-22T21:49:42Z still returned errno65,
No route to host,for the controller and all four endpoints. No device commands
or configuration were issued. Evidence: .spec200-local/discovery-change/reachability-final.json.
