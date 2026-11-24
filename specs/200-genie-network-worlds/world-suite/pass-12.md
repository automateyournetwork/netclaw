# Pass12 — world2 — manager campaign admission

Implemented the handoff's manager migration (partial T013/T020). Google manager
startup requires schema2 and freezes only the four operator authority/review pins.
Local reviews and draft policy use CAMPAIGN_SESSION_POLICY and the exact packet
allowance. New starts reload the original packet, current source and evidence
after awaited native audit, then use admitReviewedCampaign for shared reservation
before the local send marker. Workers get the frozen pins plus PATH.

Original-ID retrieval checks the existing request digest and returns its stored
record without renewed authority, audit or worker launch. Historical review and
session bytes remain unchanged; different payloads still conflict.

Validation:79/79 affected tests (live, manager, campaign-budget, core, worker),
then37/37 final live tests after adding historical recovery coverage; zero skips.
These cover80 distinct tests across the two runs. New manager tests intercept
fork itself, so synthetic reviewed claims never reach a Google worker. Packet,
expiry, evidence and descriptor tampering during audit refuse before any
reservation/marker/worker; missing pins and schema1 startup also refuse. Pin
mutation after launch cannot change child configuration. Source closure stays
29files; no new module. git diff --check passes. Checklists15/15 and43/43 pass.

Private evidence: `.spec200-local/tests/world-pass-12/`, including initial failures.
The synthetic evidence filename service.json collided with the manager service
descriptor; tests now use a separate manager state directory. The failure is
retained, not represented as a production fix. Native GAIT reuses the current
root/branch; final log and source hashes are retained privately.

No provider/device calls, owner dotenv reads, private export, snapshot/control/
allowance/acceptance/PROGRESS edits, runtime changes, agents, git commits or tickets.
No generated frames were available for visual review; live_world_passed=false.
No task checkbox or T029 closes. Actual input/text/service bounds, terminal/billing
reconciliation, worker create ownership and Risk-member qualification remain open.
All earlier live packets are source-stale.

Next bounded defect: provider validation is a read-only check followed by awaited
create. Qualify concurrent/restarted opens of the same create_pending record with
an injected client; enforce a durable one-use transport claim before SDK creation
without replay or releasing ambiguous reservations. This is separate from the
manager's one-worker map and from actual provider-cap qualification.
