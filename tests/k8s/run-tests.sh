#!/usr/bin/env bash
# Contract tests for k8s-mcp — spec 084 (roadmap R14).
#
# STATIC  — runs anywhere. Does NetClaw's config force read-only and deny Secrets? Is the
#           kubeconfig explicit rather than ambient? Do the skills carry a followable
#           preflight, or only a warning?
# LIVE    — needs K8S_TEST_KUBECONFIG (+ K8S_TEST_LIMITED_KUBECONFIG for the centrepiece).
#           Does the silent narrowing reproduce? Does the mandated credential avoid it?
#
# The live suite matters more here than usual: this feature exists because the adopted
# server converts an honest 403 into a plausible short list, and a claim that important
# is reproduced in our own suite rather than cited to a source file.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1
export PYTHONPATH="$REPO_ROOT/tests/k8s:${PYTHONPATH:-}"
FAILED=0
run() { echo; echo "=============================================================="; echo "  $1"; \
        echo "=============================================================="; python3 "$2" || FAILED=$((FAILED+1)); }

run "config    — read-only forced, Secrets denied, kubeconfig explicit (FR-019..022)" tests/k8s/test_config_forced.py
run "skills    — a followable preflight, six absences, boundaries (SC-002/004/020)"   tests/k8s/test_skill_procedure.py
run "manifest  — 7 tools, <= 5,000 tokens, checksum matches (FR-037, SC-018)"          tests/k8s/test_manifest_size.py

if [ -n "${K8S_TEST_KUBECONFIG:-}" ]; then
    run "LIVE      — the narrowing reproduces; credential avoids it (SC-003/022)"      tests/k8s/test_live_k8s.py
else
    echo; echo "=============================================================="
    echo "  LIVE — SKIPPED (set K8S_TEST_KUBECONFIG, and K8S_TEST_LIMITED_KUBECONFIG)"
    echo "  Static tests prove the config and skills are right."
    echo "  Only the live suite proves the server actually behaves as described."
    echo "=============================================================="
fi
echo; echo "=============================================================="
[ "$FAILED" -eq 0 ] && { echo "  ALL SUITES PASSED"; exit 0; }
echo "  $FAILED SUITE(S) FAILED"; exit 1
