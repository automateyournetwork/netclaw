#!/usr/bin/env bash
# Convergence telemetry setup wizard (Phase 10 PR2 — T129).
# Thin wrapper around scripts/convergence-telemetry-setup.py
#
# Usage:
#   ./scripts/convergence-telemetry-setup.sh
#   ./scripts/convergence-telemetry-setup.sh --mode nautobot --select all --dry-run
#   ./scripts/convergence-telemetry-setup.sh --mode nautobot --select all --write --apply
#   ./scripts/convergence-telemetry-setup.sh --mode manual --csv 'SW1=10.0.0.1:cisco'
#   ./scripts/convergence-telemetry-setup.sh --mode yaml --import path/to/targets.yml
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/scripts/convergence-telemetry-setup.py"
if [[ ! -f "$PY" ]]; then
  echo "Missing $PY" >&2
  exit 1
fi
exec python3 "$PY" "$@"
