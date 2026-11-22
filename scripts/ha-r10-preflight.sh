#!/usr/bin/env bash
# Spec 198: read-only Azure preflight. Creates nothing. Exit 0 only on GO.
here="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$here/labs/ha/r10_preflight.py" "$@"
