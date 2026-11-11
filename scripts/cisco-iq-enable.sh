#!/usr/bin/env bash
# Cisco IQ remote MCP administration (spec 191, issue #346). No logic lives here.
#   enable | update | rotate | disable | status | diagnose | policy-check
# Run with -h for usage. The API key is read from stdin (--key-stdin) or a hidden
# prompt; it is never accepted as an argument and never printed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/cisco_iq.py" "$@"
