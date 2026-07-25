#!/usr/bin/env bash
# Apply NetClaw model SoT from .env → live OpenClaw + gateway env.
#
# Operator guide: docs/MODELS.md
#
# Source of truth (preferred write target = NETCLAW_DIR/.env):
#   1) $NETCLAW_ENV_FILE
#   2) $NETCLAW_DIR/.env          (repo — preferred operator SoT)
#   3) ~/.openclaw/.env           (filled for missing keys on read)
#
# Variables:
#   NETCLAW_BRAIN_MODEL          Interactive main / agents.defaults (provider/model)
#   NETCLAW_ALERT_TRIAGE_MODEL   T2 hooks + agents.list[alert] (provider/model)
#   NETCLAW_ALERT_FALLBACK_MODEL Optional fallback for alert agent
#   OLLAMA_BASE_URL / OLLAMA_API_KEY  Passed through to gateway.systemd.env
#
# Recommended Anthropic pair (when ANTHROPIC_API_KEY is funded):
#   --brain anthropic/claude-sonnet-5
#   --alert anthropic/claude-haiku-4-5-20251001
#
# Usage:
#   ./scripts/netclaw-apply-models.sh show
#   ./scripts/netclaw-apply-models.sh apply [--no-restart]
#   ./scripts/netclaw-apply-models.sh set --brain ollama/deepseek-v4-flash:cloud \
#       --alert ollama/deepseek-v4-flash:cloud [--fallback ollama/glm-5.2:cloud]
#   ./scripts/netclaw-apply-models.sh preset local|cloud-flash|split
#
set -euo pipefail

NETCLAW_DIR="${NETCLAW_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
OPENCLAW_JSON="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_HOME/openclaw.json}"
GATEWAY_ENV="${OPENCLAW_GATEWAY_ENV:-$OPENCLAW_HOME/gateway.systemd.env}"
SOT_ENV="${NETCLAW_ENV_FILE:-$NETCLAW_DIR/.env}"
OPENCLAW_DOTENV="$OPENCLAW_HOME/.env"
RESTART=1

cmd="${1:-show}"
shift || true

# parse trailing flags for apply/set/preset
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-restart) RESTART=0; shift ;;
    --restart) RESTART=1; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

need_python() { command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }; }

# Safe KEY=value extract (no shell source — .env files often contain unquoted tokens)
_env_get() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 0
  python3 - "$file" "$key" <<'PY'
import re, sys
from pathlib import Path
path, key = Path(sys.argv[1]), sys.argv[2]
if not path.is_file():
    sys.exit(0)
# last assignment wins
val = None
for line in path.read_text(errors="replace").splitlines():
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    if s.startswith("export "):
        s = s[7:].strip()
    if "=" not in s:
        continue
    k, v = s.split("=", 1)
    k = k.strip()
    if k != key:
        continue
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    val = v
if val is not None:
    print(val)
PY
}

load_env_merge() {
  # Prefer SoT (repo .env) over ~/.openclaw/.env for model keys
  local k
  for k in NETCLAW_BRAIN_MODEL NETCLAW_ALERT_TRIAGE_MODEL NETCLAW_ALERT_FALLBACK_MODEL \
           OLLAMA_BASE_URL OLLAMA_API_KEY NETCLAW_MODEL; do
    local v=""
    v="$(_env_get "$OPENCLAW_DOTENV" "$k" || true)"
    local v2=""
    v2="$(_env_get "$SOT_ENV" "$k" || true)"
    [[ -n "$v2" ]] && v="$v2"
    if [[ -n "$v" ]]; then
      export "$k=$v"
    fi
  done
  # Convenience: bare NETCLAW_MODEL fills brain if brain unset
  if [[ -z "${NETCLAW_BRAIN_MODEL:-}" && -n "${NETCLAW_MODEL:-}" ]]; then
    export NETCLAW_BRAIN_MODEL="$NETCLAW_MODEL"
  fi
}

normalize_hint() {
  cat <<'EOF'
Model ids should be provider/model, e.g.:
  ollama/deepseek-v4-flash:cloud
  ollama/voytas26/openclaw-qwen3vl-8b-opt
  anthropic/claude-sonnet-5
Bare names without a provider are prefixed with ollama/ by the apply step.
EOF
}

show() {
  load_env_merge
  need_python
  echo "SoT env file: $SOT_ENV"
  echo "OpenClaw json: $OPENCLAW_JSON"
  echo "Gateway env:   $GATEWAY_ENV"
  echo
  echo "Env (SoT):"
  echo "  NETCLAW_BRAIN_MODEL=${NETCLAW_BRAIN_MODEL:-(unset)}"
  echo "  NETCLAW_ALERT_TRIAGE_MODEL=${NETCLAW_ALERT_TRIAGE_MODEL:-(unset)}"
  echo "  NETCLAW_ALERT_FALLBACK_MODEL=${NETCLAW_ALERT_FALLBACK_MODEL:-(unset)}"
  echo "  OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-(unset)}"
  echo "  OLLAMA_API_KEY=${OLLAMA_API_KEY:+(set)}"
  echo
  python3 - "$OPENCLAW_JSON" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    print("openclaw.json missing")
    sys.exit(0)
d = json.loads(p.read_text())
def_m = ((d.get("agents") or {}).get("defaults") or {}).get("model") or {}
print("Live openclaw.json:")
print(f"  agents.defaults.model.primary = {def_m.get('primary')}")
for a in (d.get("agents") or {}).get("list") or []:
    if not isinstance(a, dict):
        continue
    print(f"  agents.list[{a.get('id')}].model = {a.get('model')}")
for m in (d.get("hooks") or {}).get("mappings") or []:
    if not isinstance(m, dict):
        continue
    path = (m.get("match") or {}).get("path")
    if path in ("alert", "reconcile"):
        print(f"  hooks.mappings[{path}].model = {m.get('model')}  agentId={m.get('agentId')}")
PY
}

upsert_env_file() {
  local file="$1"
  shift
  mkdir -p "$(dirname "$file")"
  touch "$file"
  python3 - "$file" "$@" <<'PY'
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
# remaining: KEY=value pairs
pairs = []
for arg in sys.argv[2:]:
    if "=" not in arg:
        continue
    k, v = arg.split("=", 1)
    pairs.append((k, v))
text = path.read_text() if path.is_file() else ""
for k, v in pairs:
    if v is None:
        continue
    line = f"{k}={v}"
    pat = re.compile(rf"^{re.escape(k)}\s*=.*$", re.M)
    if pat.search(text):
        text = pat.sub(line, text)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
path.write_text(text)
print(f"  updated {path} ({', '.join(k for k,_ in pairs)})")
PY
}

write_sot() {
  local brain="$1" alert="$2" fallback="${3:-}"
  mkdir -p "$(dirname "$SOT_ENV")"
  local args=(
    "NETCLAW_BRAIN_MODEL=$brain"
    "NETCLAW_ALERT_TRIAGE_MODEL=$alert"
  )
  if [[ -n "$fallback" ]]; then
    args+=("NETCLAW_ALERT_FALLBACK_MODEL=$fallback")
  fi
  # Keep OLLAMA_* if already in environment
  if [[ -n "${OLLAMA_BASE_URL:-}" ]]; then
    args+=("OLLAMA_BASE_URL=$OLLAMA_BASE_URL")
  fi
  if [[ -n "${OLLAMA_API_KEY:-}" ]]; then
    args+=("OLLAMA_API_KEY=$OLLAMA_API_KEY")
  fi
  echo "Writing SoT → $SOT_ENV"
  upsert_env_file "$SOT_ENV" "${args[@]}"
  # Mirror model keys into ~/.openclaw/.env so other tools see them
  if [[ -f "$OPENCLAW_DOTENV" ]] || [[ -d "$OPENCLAW_HOME" ]]; then
    upsert_env_file "$OPENCLAW_DOTENV" "${args[@]}"
  fi
}

apply_json_and_gateway() {
  load_env_merge
  need_python

  local brain="${NETCLAW_BRAIN_MODEL:-}"
  local alert="${NETCLAW_ALERT_TRIAGE_MODEL:-}"
  local fallback="${NETCLAW_ALERT_FALLBACK_MODEL:-}"

  if [[ -z "$brain" && -z "$alert" ]]; then
    echo "Neither NETCLAW_BRAIN_MODEL nor NETCLAW_ALERT_TRIAGE_MODEL is set in $SOT_ENV" >&2
    normalize_hint >&2
    exit 1
  fi
  # defaults: if only one set, use for both
  brain="${brain:-$alert}"
  alert="${alert:-$brain}"

  if [[ ! -f "$OPENCLAW_JSON" ]]; then
    echo "Missing $OPENCLAW_JSON" >&2
    exit 1
  fi

  local ts bak
  ts="$(date +%Y%m%d%H%M%S)"
  bak="${OPENCLAW_HOME}/openclaw.json.bak-models-${ts}"
  cp -a "$OPENCLAW_JSON" "$bak"
  echo "Backup: $bak"

  BRAIN="$brain" ALERT="$alert" FALLBACK="$fallback" OPENCLAW_JSON="$OPENCLAW_JSON" python3 <<'PY'
import json, os, re
from pathlib import Path

def normalize(mid: str) -> str:
    mid = (mid or "").strip().strip('"').strip("'")
    if not mid:
        return mid
    if mid.startswith("${") and mid.endswith("}"):
        return mid  # leave template
    if "/" in mid:
        return mid
    # bare anthropic-ish
    if mid.startswith("claude") or mid.startswith("anthropic."):
        return f"anthropic/{mid}"
    return f"ollama/{mid}"

brain = normalize(os.environ["BRAIN"])
alert = normalize(os.environ["ALERT"])
fallback = normalize(os.environ.get("FALLBACK") or "")
path = Path(os.environ["OPENCLAW_JSON"])
d = json.loads(path.read_text())

agents = d.setdefault("agents", {})
defaults = agents.setdefault("defaults", {})
model = defaults.setdefault("model", {})
if not isinstance(model, dict):
    model = {}
    defaults["model"] = model
model["primary"] = brain
if "fallbacks" not in model or model["fallbacks"] is None:
    model["fallbacks"] = []

lst = agents.get("list")
if not isinstance(lst, list):
    lst = []
    agents["list"] = lst

def upsert_agent(aid, **fields):
    for i, a in enumerate(lst):
        if isinstance(a, dict) and a.get("id") == aid:
            a.update(fields)
            lst[i] = a
            return
    lst.append({"id": aid, **fields})

# Ensure main exists when list is used
if lst and not any(isinstance(a, dict) and a.get("id") == "main" for a in lst):
    lst.insert(0, {"id": "main", "default": True, "name": "Main"})

# alert agent model (thin tools profile may already exist)
alert_model = {"primary": alert, "fallbacks": [fallback] if fallback else []}
found_alert = False
for a in lst:
    if isinstance(a, dict) and a.get("id") == "alert":
        a["model"] = alert_model
        found_alert = True
        break
if not found_alert and lst:
    # list mode without alert — only set defaults; hooks still get model
    pass
elif not found_alert and not lst:
    pass

hooks = d.setdefault("hooks", {})
mappings = hooks.get("mappings")
if not isinstance(mappings, list):
    mappings = []
    hooks["mappings"] = mappings
alert_map = None
for m in mappings:
    if isinstance(m, dict) and (m.get("match") or {}).get("path") == "alert":
        alert_map = m
        break
if alert_map is None:
    alert_map = {
        "match": {"path": "alert"},
        "action": "agent",
        "wakeMode": "now",
        "name": "NetClaw Alert Triage",
        "sessionKey": "hook:alert:{{alerts[0].fingerprint}}",
        "messageTemplate": (
            "A monitoring alert has fired on the home network. Follow the "
            "alert-triage skill to investigate and report. Alert details:\n\n"
            "{{alerts[0].annotations.investigation_prompt}}"
        ),
        "timeoutSeconds": 900,
    }
    mappings.insert(0, alert_map)
alert_map["model"] = alert
# Prefer thin agent id when present
if any(isinstance(a, dict) and a.get("id") == "alert" for a in lst):
    alert_map["agentId"] = "alert"
    allowed = hooks.get("allowedAgentIds")
    if not isinstance(allowed, list):
        allowed = ["main"]
    if "alert" not in allowed:
        allowed = list(allowed) + ["alert"]
    hooks["allowedAgentIds"] = allowed

path.write_text(json.dumps(d, indent=2) + "\n")
print(f"Wrote {path}")
print(f"  brain (defaults) = {brain}")
print(f"  alert (hook)     = {alert}")
if fallback:
    print(f"  alert fallback   = {fallback}")
PY

  # gateway.systemd.env — what the running gateway actually sees
  local gargs=(
    "NETCLAW_BRAIN_MODEL=$brain"
    "NETCLAW_ALERT_TRIAGE_MODEL=$alert"
  )
  [[ -n "$fallback" ]] && gargs+=("NETCLAW_ALERT_FALLBACK_MODEL=$fallback")
  [[ -n "${OLLAMA_BASE_URL:-}" ]] && gargs+=("OLLAMA_BASE_URL=$OLLAMA_BASE_URL")
  [[ -n "${OLLAMA_API_KEY:-}" ]] && gargs+=("OLLAMA_API_KEY=$OLLAMA_API_KEY")
  echo "Syncing gateway env → $GATEWAY_ENV"
  upsert_env_file "$GATEWAY_ENV" "${gargs[@]}"

  if command -v openclaw >/dev/null 2>&1; then
    if ! openclaw config validate 2>&1; then
      echo "ERROR: config invalid — restoring $bak" >&2
      cp -a "$bak" "$OPENCLAW_JSON"
      exit 1
    fi
  fi

  if [[ "$RESTART" -eq 1 ]]; then
    if systemctl --user cat openclaw-gateway.service >/dev/null 2>&1; then
      echo "Restarting openclaw-gateway…"
      systemctl --user daemon-reload 2>/dev/null || true
      systemctl --user restart openclaw-gateway.service
      sleep 2
      systemctl --user is-active openclaw-gateway.service || true
    else
      echo "openclaw-gateway.service not found — restart gateway manually" >&2
    fi
  else
    echo "Skipped restart (--no-restart). Run: systemctl --user restart openclaw-gateway.service"
  fi
  show
}

do_set() {
  local brain="" alert="" fallback=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --brain) brain="$2"; shift 2 ;;
      --alert) alert="$2"; shift 2 ;;
      --fallback) fallback="$2"; shift 2 ;;
      *) echo "Unknown: $1" >&2; exit 2 ;;
    esac
  done
  if [[ -z "$brain" && -z "$alert" ]]; then
    echo "Usage: $0 set --brain PROVIDER/MODEL --alert PROVIDER/MODEL [--fallback …]" >&2
    exit 2
  fi
  load_env_merge
  brain="${brain:-${NETCLAW_BRAIN_MODEL:-}}"
  alert="${alert:-${NETCLAW_ALERT_TRIAGE_MODEL:-}}"
  brain="${brain:-$alert}"
  alert="${alert:-$brain}"
  write_sot "$brain" "$alert" "$fallback"
  apply_json_and_gateway
}

do_preset() {
  local name="${1:-}"
  load_env_merge
  local local_m="ollama/voytas26/openclaw-qwen3vl-8b-opt"
  local flash="ollama/deepseek-v4-flash:cloud"
  local glm="ollama/glm-5.2:cloud"
  case "$name" in
    local)
      write_sot "$local_m" "$local_m" ""
      ;;
    cloud-flash|cloud|flash)
      write_sot "$flash" "$flash" "$glm"
      ;;
    split|split-local-brain)
      # Cheap interactive local + capable cloud investigations
      write_sot "$local_m" "$flash" "$glm"
      ;;
    anthropic|sonnet-haiku)
      # Strong chat + cheaper structured alert triage (needs ANTHROPIC_API_KEY)
      write_sot "anthropic/claude-sonnet-5" "anthropic/claude-haiku-4-5-20251001" ""
      ;;
    *)
      echo "Unknown preset: $name" >&2
      echo "Presets: local | cloud-flash | split | anthropic" >&2
      exit 2
      ;;
  esac
  apply_json_and_gateway
}

case "$cmd" in
  show|status) show ;;
  apply) apply_json_and_gateway ;;
  set) do_set "$@" ;;
  preset) do_preset "$@" ;;
  *)
    echo "Usage: $0 {show|apply|set|preset} …" >&2
    echo "  $0 show" >&2
    echo "  $0 apply [--no-restart]" >&2
    echo "  $0 set --brain ollama/deepseek-v4-flash:cloud --alert ollama/deepseek-v4-flash:cloud" >&2
    echo "  $0 preset cloud-flash|local|split" >&2
    normalize_hint >&2
    exit 2
    ;;
esac
