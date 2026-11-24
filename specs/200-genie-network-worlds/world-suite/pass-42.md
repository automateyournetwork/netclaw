# World-suite pass42 — world5: disconnected camera landmark

2026-11-23. Assigned pass42/world5, source_refinement. One bounded partial
T018/T028 source/verification unit; no checkbox closes,15/30 remain complete.

Camera guidance now depends on measured physical-link presence. Linked cohorts
keep the existing nearest-connection/both-endpoints view. Disconnected cohorts
start with the first measured device in view as the navigation landmark, with
an explicit instruction not to add connections. Their event remains null.
No synthetic topology is substituted for the sealed real snapshot.

Regression covers one and two disconnected devices across all five styles,
measured device claims, zero link claims, null events, unchanged inputs and
private-only flags. Linked cohorts retain their camera and original event target.
The new disconnected regression fails against old source (4 pass/1 fail); red.log
is retained. Supported Node world-designs.test.mjs + live.test.mjs:49/49 pass, zero failures/skips (77.94s).

Read-only verification passes all1,011 sealed files and builds five private drafts
with identical provenance for4devices/3links. All five outbound hashes exactly
match pass41: the real linked cohort was not affected by this edge case. No raw
facts, topology or projection text is emitted/exported. Only counts/status/hashes
are retained in snapshot-check.json. No generated world or visual review occurred.

The existing29-file source closure already includes world-designs.mjs; no module
was added. Changed source invalidates previous exact paid packets even though
these real projection hashes did not change. Coordinator must review fresh bytes.

Spec Kit prerequisites and requirements15/15, quality43/43 pass; optional Git hooks
skipped. Private evidence: .spec200-local/tests/world-pass-42/ contains red.log,
tests.log, snapshot-check.json, source-hashes.json, next-defect.json and native
GAIT start/end/log. GAIT reuses the current sticky root/audit branch.

No provider/device/SSH/CML/pyATS calls, dotenv reads, private export, authority/
allowance/acceptance/PROGRESS changes, owner-runtime changes, agents/loops, branch
changes, Git commits or publication.198at856bbc88 and199AWS preserved. Actual
Google navigation/event/drift/terminal/usage, selected Risk/member execution and
human T029 acceptance remain open. Hosted3–5 require actual1/2 technical success.

Next concrete defect: interaction metadata always promises “one text event” even
when outbound.event is null. Independent synthetic zero-link probe reproduces5/5
contradictions in next-defect.json. Make local interaction guidance conditional;
verify how the local inspector presents it, without inventing an event or changing
the synthetic-only hosted boundary. This is not a defect in real linked-event data.
