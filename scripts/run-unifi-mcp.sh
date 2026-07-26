#!/usr/bin/env bash
# Launch UniFi MCP with UNIFI_* from Border ~/.openclaw/.env or netclaw/.env
# (robust parse — no bash source of full .env).
set -euo pipefail
ENV_CANDIDATES=(
  "${OPENCLAW_ENV_FILE:-}"
  "${HOME}/.openclaw/.env"
  "/home/ubuntu/netclaw/.env"
  "${N2N_MEMBER_ENV_FILE:-}"
)
ENV_FILE=""
for f in "${ENV_CANDIDATES[@]}"; do
  [ -n "$f" ] && [ -f "$f" ] && ENV_FILE="$f" && break
done
if [ -z "$ENV_FILE" ]; then
  echo "run-unifi-mcp: no env file with UNIFI_* found" >&2
  exit 1
fi
eval "$(python3 - "$ENV_FILE" <<'PY'
import shlex, sys
from pathlib import Path
path = Path(sys.argv[1])
want = ("UNIFI_HOST", "UNIFI_API_KEY", "UNIFI_SITE", "UNIFI_VERIFY_SSL")
found = {k: None for k in want}
for line in path.read_text().splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    if k not in want:
        continue
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    found[k] = v
# Prefer first file only; caller can pass better file first
for k, v in found.items():
    if v is not None:
        print(f"export {k}={shlex.quote(v)}")
missing = [k for k, v in found.items() if v is None and k in ("UNIFI_HOST", "UNIFI_API_KEY")]
if missing:
    raise SystemExit(f"missing required keys in {path}: {missing}")
PY
)"
# Defaults
export UNIFI_SITE="${UNIFI_SITE:-default}"
export UNIFI_VERIFY_SSL="${UNIFI_VERIFY_SSL:-false}"
exec /home/ubuntu/.local/bin/uv run --directory /home/ubuntu/mcp-servers/unifi-mcp python -m unifi_mcp
