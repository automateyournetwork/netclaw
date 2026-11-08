# Required R08 qualification matrix

FIXTURE uses actual authenticated quorum/NCFED transport with controlled effects.
REAL uses the actual selected guard/model/nativeMCP profile and its cumulative
provider/inference/native-tool counters. Control-plane rows run on the same actual
cluster and verify real execution is still fenced or usable as specified;they do
not need to create another effect for every negative. No row may be waived by
labeling it “applicable”. Fault injection must be independently observed.

| Row | Fixture requirement | Required REAL/control evidence |
|---|---|---|
| Leader loss | Each node loss,election,old epoch refusal | Kill actual leader;original result unchanged;distinct new native operation on survivor |
| Minority partition | Directed minority isolation,positive controls | Fresh model AND tool admission through isolated old leader refused;real counters unchanged |
| Asymmetric partition | Both directed cut orientations | Same real admission checks;majority distinct work authorized only once |
| Three-way partition | All three isolated | Model/tool admission refuse on all;zero added real calls |
| Stale leader/member | Paused leader;member never saw new epoch | Delayed old claim/challenge refused at real guard/effect gate;unchanged counters |
| Quorum loss | Two voters lost | Existing status readable;fresh model and tool admissions refuse;no new real calls |
| Clock uncertainty | Forward/backward wall jump,suspend/delayed reply | Actual real-profile gate receives controlled clock discontinuity and refuses before forward/invoke |
| Unknown consensus commit | Drop reply after actual commit | Exact claim recovery only;no new real forward for lost/expired challenge |
| Lost result/ACK | Drop delivery/ACK independently | Original signed native result/durableACK recovered through survivor with same effect counters |
| Member/runner unknown | Process death after dispatch | Original real-profile runner fence survives restart;newID cannot bypass;retain unknown evidence |
| Full restart | All nodes/voters/member restart | Real completed/unknown operation records preserved;GET-only recovery;no replay |
| Retired node returns | Durable retirement then old-key reconnect | Retirednode cannot authorize actual-profile model/tool gates;current cluster status records reason |
| Fenced restore | Actual owned isolation;new generation remains fenced | Real-profile unknown/reservations retained;stale snapshot gap freezes affected capacity;no speculative execution |
| Capacity/storage | Quota/recordlimit/NOSPACE | No new real-profile admission;spent/unknown evidence intact |
| Topology/trust | member/external/unenrolled/role replay negative matrix | Actual iN2Nmember attaches to3Borders;no member-to-member or memberetcd access |
| HUD | Real browser authority/quorum/recovery | Actual signed native operation/ACK;preserve sent marker,stale review refusal |
| VSCode G12 | Native MacCode trust/failover/cold recovery | Same original real result/reference and zero extra calls |
| Mobile G13 | NativeiOSsimulator enrollment/background/cold/failover | Same devicekey/subject,original real result/reference and zero extra calls |

Capture failure-to-detection,new-authority and service-recovery separately;
record300ms injectedRTT envelope and disk/clock bounds. Negative tests call the
same production gates;they must not replace the guard with a synthetic provider.
PhysicaliPhone,newWindows/WSL,actualWAN/regions and additional HA model profiles
remain unqualified,with standalone regression coverage separately recorded.
