# Mac closeout → Border session: the one thing left is FR-017

**Snapshot: 2026-08-11.** `git pull` this branch to get this file. This is the
last handoff from the Mac side — everything else in spec 103 is closed. What
follows is the one remaining item, framed so it can be picked up and finished
without re-reading the whole spec history.

## Everything else is done — don't re-verify it

- **US1** (queue replay), **US2** (channel stability, both real bugs fixed and
  live-verified — 995s held, 16s auto-recovery), and real APNs/FCM push are
  all done and confirmed working, per BORDER-STATUS.md's own "all three
  delivery tiers live" summary.
- **US3** (background refresh) and **US4** (watch heartbeat surface) are
  code-complete, unit-tested, and deployed. Neither got a final live-fire /
  on-screen confirmation — every blocker in the way was Apple tooling friction
  (Xcode's GUI signing cache, a stuck one-time watch-pairing glitch), not a
  defect in the code itself. See spec.md's "Already Landed" section for the
  full accounting. Closed as done; re-open only if real usage surfaces an
  actual defect.

## FR-017: retire an abandoned edge enrollment without hand-editing the database

**The requirement** (spec.md): *"The operator MUST be able to retire an
abandoned edge enrollment without editing the database by hand."*

**Why this now has two concrete motivating cases, not one theoretical one:**
the spec's own Edge Cases section already noted six stale rows from earlier
re-enrollments. This branch's own testing added at least one more —
`risk/1785078347014` was abandoned mid-session when a forced app
uninstall/reinstall (done to unstick an unrelated watch-companion transfer
bug) wiped the phone's persisted `EnrollmentStore`, requiring a fresh
`./scripts/netclaw risk token --edge ...` + QR re-scan, which mints a **new**
`member_id` per MOBILE-ONBOARDING.md's documented behavior. The old member_id
is now exactly the kind of abandoned row FR-017 describes.

**What "retire" should mean**, based on the existing edge-case language and
how the rest of this feature treats these rows:

1. Remove/deactivate the abandoned `member` row so it stops being enrolled
   (mirrors `./scripts/netclaw risk remove <member_id>`, which MOBILE-
   ONBOARDING.md documents for the *lost/stolen phone* case — check whether
   that same command already satisfies FR-017 as-is, or whether it needs a
   variant/flag for "abandoned, not necessarily compromised").
2. Confirm pushes are never queued for a retired enrollment (spec's own edge
   case: *"Pushes must not be queued for abandoned enrollments"*) — check
   `edge_queue.py`'s enqueue path actually checks member state before writing
   a row, not just at delivery time.
3. Decide what happens to that member's *existing* queued rows at the moment
   of retirement — drop them, or let them expire via the existing TTL/depth
   cap (FR-004)? Either is defensible; just make it explicit rather than
   implicit.

**A concrete list of currently-abandoned rows to test against** (don't treat
this as exhaustive — a fresh `./scripts/netclaw risk members` will show the
real current state):

- `risk/1785077389894` — spec's own noted abandoned enrollment (last seen Jul
  28, per BORDER-FINDINGS.md).
- `risk/1785078347014` — abandoned today (2026-08-11), for the reason above.
- Whatever else has accumulated from the "six such rows" the spec's Edge Cases
  section originally referenced.

## What would help back from the Border side

Once FR-017 is implemented and you're satisfied, spec 103 has nothing left
open on either side. A short confirmation here (or in a fresh status doc) that
FR-017 is done is all that's needed to close the branch out entirely.
