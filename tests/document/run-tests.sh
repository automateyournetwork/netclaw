#!/usr/bin/env bash
# Contract tests for document-mcp — spec 082 (roadmap R18).
#
# Bash + stdlib only, following tests/bgp-intel/run-tests.sh and, before it,
# tests/reconcile/run-tests.sh (spec 075). No new test framework.
#
# EVERY TEST HERE RUNS WITH NO NETWORK AND NO CREDENTIALS. Each suite writes into its
# own temp directory via _harness.sandbox() and cleans up after itself; nothing lands in
# workspace/output/.
#
# But note what appliance-free testing does NOT buy. Spec 080 had 24 passing tests while
# shipping a tool that returned three nulls, because its suites asserted on the ENVELOPE
# and never on the CONTENT. This feature's entire output IS content, so the suites below
# reopen every generated .docx/.xlsx/.pptx/.pdf with the same library a reader's
# application would use and assert on what is inside it — including one assertion
# against raw worksheet XML, which is the only thing that catches openpyxl turning a
# leading `=` into a live formula.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

FAILED=0
run() {
    local name="$1" path="$2"
    echo
    echo "=============================================================="
    echo "  $name"
    echo "=============================================================="
    python3 "$path" || { FAILED=$((FAILED + 1)); return 1; }
}

run "tagged values — the three shapes, refusals (FR-001/002/005c/007, SC-002/003)"  tests/document/test_tagged_values.py
run "output paths  — O_EXCL, never overwrite (FR-016..020, SC-012/013/014)"          tests/document/test_output_paths.py
run "sanitize      — untrusted text is not a formula (FR-026, SC-015)"               tests/document/test_sanitize.py
run "provenance    — REOPENED files carry stamp + sources (FR-006..010, SC-009/010)" tests/document/test_provenance.py
run "no fabricate  — gaps explicit, bounds stated, templates refused (FR-001..005)"  tests/document/test_no_fabrication.py
run "pdf forms     — named fields, unfilled + unmatched (FR-024/024a/024b, SC-008)"  tests/document/test_pdf_forms.py
run "surface       — read-only guard + <= 5,000 token ceiling (FR-033/038a, SC-025)" tests/document/test_manifest_size.py

echo
echo "=============================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "  ALL SUITES PASSED"
    exit 0
fi
echo "  $FAILED SUITE(S) FAILED"
exit 1
