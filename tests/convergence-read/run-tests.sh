#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
python3 tests/convergence-read/test_connector.py
exec python3 tests/convergence-read/test_members.py
