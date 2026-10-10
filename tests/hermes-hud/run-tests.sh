#!/usr/bin/env bash
set -euo pipefail
HERMES_TEST_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$HERMES_TEST_ROOT"
node scripts/hud-node-version.mjs
python3 -m unittest discover -s tests/hermes-hud -v
python3 -m unittest discover -s tests/unit -p 'test_hud_runtime_selection.py' -v
# Real pinned-agent acceptance is separate and must not be confused with mocks.
