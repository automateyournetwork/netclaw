# Pass49 — world5: typed source provenance

Bounded partial T018/T028 source refinement, 2026-11-23. The shared sourced
observation check now requires a record-shaped source and an exact 64-character
lowercase hexadecimal string digest. Array-coerced digests, array-shaped source
records and malformed scalar/container provenance cannot yield VLAN or protocol
cues. Historical sources without outcome fields and explicit observed outcomes
remain supported; existing negative-outcome checks and local unknowns remain.

The rejection regression failed before the fix (three unsupported claims instead
of zero); the valid-source regression already passed. Final designs/actual Chrome
18/18 and selected source-review/admission7/7 pass, zero skips. New tests cover16
invalid source/digest shapes across all five styles and preserve supported source
anchors, coverage limits and local facts. Existing browser inspection stays local,
with zero sessions/external requests; this is not generated-world visual proof.

Targeted trusted-manifest and world-facts digest checks pass. All five real draft
outbound hashes match pass48; each retains four protocol and two VLAN anchors.
No sealed writes or full-bundle/lifecycle requalification. Existing29-file source
closure already covers world-designs.mjs; no new module/dependency. Changed source
bytes invalidate older paid packets even though these real draft hashes match.

Private evidence: .spec200-local/tests/world-pass-49/{red.log,tests-browser.log,
source-review.log,real-provenance-check.json,next-defect.json,source-hashes.json,
gait_status-start.json,gait_record_turn-start.json,gait-end-turn.json,gait-log.json}.
Next independently synthetic defect: a sourced VLAN observation for an unselected
device produces one membership claim per style. Bind eligibility to the selected
cohort while preserving valid siblings and original source pointers. No real
snapshot defect is inferred.

Spec Kit prerequisites and requirements15/15, quality43/43 pass. Private test root
is ignored. No task checkbox closes;15/30. Native GAIT reuses the current root and
audit branch; final log retained privately. Initial broad context output was
truncated; scoped reads followed. Three guessed file paths did not exist; lookup
was corrected without changing data. No tickets or new network facts.
No provider/device calls, dotenv reads, private export, authority/PROGRESS edits,
owner runtime changes, agents/loops, branch changes, Git commits or publication.
198at856bbc88 and199AWS preserved. Direct Google proof, reviewed private export,
Risk/member correlation and human T029 remain open. Hosted worlds3–5 still require
coordinator-recorded live1/2 success. live_world_passed=false.
