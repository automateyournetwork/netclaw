# Tasks

- [x] T001 Reproduce and diagnose the member turn failure.
- [x] T002 Runtime fix and tests.
- [x] T003 Diagnose refused bootstrap files; installer repair of legacy links and test.
- [x] T004 Live verification on 2026.10.6 and 2026.10.9, docs, release and PR.
- [x] T005 Fix independently reproduced staging-symlink clobber, verify failure
  preservation and correct release verification wording; independent re-review.
  Hosted checks for the resulting commit are tracked on PR #316 before merge.
- [x] T006 Follow-up (acceptance 2): an `agents.list` entry without a usable `id` is not
  counted as an agent, so a home with one agent `main` and an id-less entry keeps the
  unnamed command. Found in a code review of a backport; tests first.
