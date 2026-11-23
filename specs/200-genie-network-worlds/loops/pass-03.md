# Pass03 — process-bounded capture and offline parsing

Status:progress. Worked T016 and per-pass T030; no full task closed.14/30 remains.

Changed scripts/genie-worlds/collector.py and tests/genie-worlds/collector_test.py;
added contracts/collector.md; updated tasks.md,verification.md,resume.md,HANDOFF.md
and daily memory. Replaced cooperative threads with fresh selected-interpreter
processes, bounded scheduling, group termination, atomic private capture evidence,
shared raw-byte admission and capture-loss unknown handling without retry.

Actual tests:
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p collector_test.py -v`:12/12 final,Python3.12.12. Includes hanging child, descendants, global timeout, two-worker/per-device bounds, independent progress, no recapture, private evidence and raw/unknown distinctions.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/core.test.mjs`:7/7.
- `git diff --check`:passed.

Initial collector test6/7 found premature second read while a device was hung;
fixed serial-device scheduling. Failure retained. No UI changes/browser rerun.
Evidence .spec200-local/pass-03/{collector-tests.txt,collector-tests-final-v5.txt,
core-tests.txt,diff-check.txt,gait-start.json,gait-end.json,gait-log.json,
evidence-manifest.json}. Final collector log SHA256:
e10484af0c6e0ab5ad6f41f7586b4eebaef11d952d6c656b2a9fa22373c03e6f.

Native GAIT start f5f0494e; final receipt/log retained in same private root. Control
hash unchanged. No authority/acceptance/trial-packet edits, paid/provider/device/
cloud/install/other-checkout work, source commit, tickets or external messages.

Remaining: native existing-read-policy adapter and frozen source/snapshot/trust
binding; detailed profile/counters/identity normalization; actual local graph input;
Google/native/owner acceptance. POSIX subprocess fixtures do not qualify native
pyATS or prove remote command termination. No fresh inventory claim; connector
absent from discovery. No task gate weakened.

Exact next step: inspect selected native read-policy entry point and implement a
capture-once/offline-parse adapter behind it with no setup commands/retries/raw SSH
fallback. If external dependency blocks that, implement T017 counter continuity
and identity normalization using synthetic tests. See HANDOFF and collector contract.
