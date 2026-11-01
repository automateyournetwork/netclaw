#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
: "${CONVERGENCE_TEST_SERVICE_CHECKOUT:?Set the pinned external service checkout}"
: "${CONVERGENCE_TEST_EVIDENCE_DIR:?Set a private evidence directory}"
exec python3 tests/convergence-read-integration/run-tests.py --service-checkout "$CONVERGENCE_TEST_SERVICE_CHECKOUT" --evidence-dir "$CONVERGENCE_TEST_EVIDENCE_DIR"
