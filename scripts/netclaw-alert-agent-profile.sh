#!/usr/bin/env bash
# Apply / show the thin alert orchestrator agent (067 Phase 9 T106).
#
# Interactive `main` keeps the full MCP set. Auto T2 investigations (hook:alert)
# run as agent id `alert` with an explicit tools.allow list so schema tax stays
# low. Deep work escalates to domain Risk members (pyATS / secops / guardian),
# not by loading every MCP on the border.
#
# Usage:
#   ./scripts/netclaw-alert-agent-profile.sh show
#   ./scripts/netclaw-alert-agent-profile.sh apply [--no-restart]
#   ./scripts/netclaw-alert-agent-profile.sh validate
#
set -euo pipefail

OPENCLAW_JSON="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"
EXAMPLE="$(cd "$(dirname "$0")/.." && pwd)/deploy/convergence/config/alert-agent.example.json"
BACKUP_DIR="${OPENCLAW_BACKUP_DIR:-$HOME/.openclaw}"
RESTART=1

cmd="${1:-show}"
shift || true
for arg in "$@"; do
  case "$arg" in
    --no-restart) RESTART=0 ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

need_python() {
  command -v python3 >/dev/null || { echo "python3 required" >&2; exit 1; }
}

show() {
  need_python
  echo "Config: $OPENCLAW_JSON"
  python3 - "$OPENCLAW_JSON" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    print("(missing openclaw.json)")
    sys.exit(0)
d = json.loads(p.read_text())
agents = d.get("agents") or {}
lst = agents.get("list") or []
print("agents.list:")
if not lst:
    print("  (empty — single-agent mode; hooks use main with full tools)")
else:
    for a in lst:
        if not isinstance(a, dict):
            continue
        aid = a.get("id")
        tools = a.get("tools") or {}
        allow = tools.get("allow") or tools.get("alsoAllow") or []
        profile = tools.get("profile")
        print(f"  - id={aid} default={a.get('default')} profile={profile} allow_n={len(allow)}")
        if aid == "alert" and allow:
            for t in allow:
                print(f"      allow: {t}")
hooks = d.get("hooks") or {}
print("hooks.allowedAgentIds:", hooks.get("allowedAgentIds"))
for m in hooks.get("mappings") or []:
    if not isinstance(m, dict):
        continue
    path = (m.get("match") or {}).get("path")
    if path in ("alert", "reconcile") or m.get("agentId"):
        print(f"  mapping path={path} agentId={m.get('agentId')} name={m.get('name')}")
PY
  if command -v openclaw >/dev/null 2>&1; then
    echo "--- openclaw agents list ---"
    openclaw agents list 2>/dev/null || true
  fi
}

apply() {
  need_python
  if [[ ! -f "$OPENCLAW_JSON" ]]; then
    echo "Missing $OPENCLAW_JSON" >&2
    exit 1
  fi
  if [[ ! -f "$EXAMPLE" ]]; then
    echo "Missing example $EXAMPLE" >&2
    exit 1
  fi

  ts="$(date +%Y%m%d%H%M%S)"
  bak="${BACKUP_DIR}/openclaw.json.bak-alert-agent-${ts}"
  cp -a "$OPENCLAW_JSON" "$bak"
  echo "Backup: $bak"

  python3 - "$OPENCLAW_JSON" "$EXAMPLE" <<'PY'
import json, os, sys
from pathlib import Path

cfg_path = Path(sys.argv[1])
ex_path = Path(sys.argv[2])
d = json.loads(cfg_path.read_text())
ex = json.loads(ex_path.read_text())
agent = dict(ex["agent"])
# Expand ${HOME} in workspace
ws = agent.get("workspace") or ""
if isinstance(ws, str) and "${HOME}" in ws:
    agent["workspace"] = ws.replace("${HOME}", os.path.expanduser("~"))

agents = d.setdefault("agents", {})
lst = agents.get("list")
if not isinstance(lst, list):
    lst = []
    agents["list"] = lst

# Ensure main exists as default when introducing multi-agent list
has_main = any(isinstance(a, dict) and a.get("id") == "main" for a in lst)
if not has_main:
    defaults = agents.get("defaults") or {}
    main_entry = {
        "id": "main",
        "default": True,
        "name": "Main",
    }
    if defaults.get("workspace"):
        main_entry["workspace"] = defaults["workspace"]
    # Preserve unrestricted tools on main (omit tools key)
    lst.insert(0, main_entry)

# Upsert alert agent
found = False
for i, a in enumerate(lst):
    if isinstance(a, dict) and a.get("id") == "alert":
        # Keep unknown fields; replace tools + name + workspace from seed
        merged = dict(a)
        merged["id"] = "alert"
        merged["name"] = agent.get("name", "Alert Orchestrator")
        if agent.get("workspace"):
            merged["workspace"] = agent["workspace"]
        merged["tools"] = agent["tools"]
        lst[i] = merged
        found = True
        break
if not found:
    lst.append(agent)

# Ensure only one default: main
for a in lst:
    if isinstance(a, dict):
        if a.get("id") == "main":
            a["default"] = True
        elif a.get("default"):
            a.pop("default", None)

# Hooks: allow alert + route alert mapping
hooks = d.setdefault("hooks", {})
allowed = hooks.get("allowedAgentIds")
if not isinstance(allowed, list):
    allowed = ["main"]
if "alert" not in allowed:
    allowed = list(allowed) + ["alert"]
if "main" not in allowed:
    allowed = ["main"] + list(allowed)
hooks["allowedAgentIds"] = allowed

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
alert_map["agentId"] = "alert"
# Hook sessions have no chat channel — disable outbound delivery (diary/Discord
# are owned by alert-receiver + guardian-claw). Prevents "Channel is required".
alert_map["deliver"] = False
if int(alert_map.get("timeoutSeconds") or 0) < 900:
    alert_map["timeoutSeconds"] = 900

cfg_path.write_text(json.dumps(d, indent=2) + "\n")
print(f"Wrote {cfg_path}")
print("  agents.list: main (default, full tools) + alert (thin allowlist)")
print("  hooks.mappings[alert].agentId = alert, deliver=false")
print("  hooks.allowedAgentIds includes alert")
PY

  if command -v openclaw >/dev/null 2>&1; then
    if ! openclaw config validate 2>&1; then
      echo "ERROR: config invalid — restoring backup" >&2
      cp -a "$bak" "$OPENCLAW_JSON"
      exit 1
    fi
  fi

  if [[ "$RESTART" -eq 1 ]]; then
    if systemctl --user is-active openclaw-gateway.service >/dev/null 2>&1 \
      || systemctl --user cat openclaw-gateway.service >/dev/null 2>&1; then
      echo "Restarting openclaw-gateway (user)…"
      systemctl --user restart openclaw-gateway.service
      sleep 2
      systemctl --user is-active openclaw-gateway.service || true
    else
      echo "openclaw-gateway.service not found under user systemd — restart gateway manually" >&2
    fi
  else
    echo "Skipped restart (--no-restart). Restart gateway for agent list to take effect."
  fi
  show
}

validate() {
  need_python
  if command -v openclaw >/dev/null 2>&1; then
    openclaw config validate
  fi
  python3 - "$OPENCLAW_JSON" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
lst = (d.get("agents") or {}).get("list") or []
alert = next((a for a in lst if isinstance(a, dict) and a.get("id") == "alert"), None)
if not alert:
    print("FAIL: agents.list has no id=alert")
    sys.exit(1)
allow = (alert.get("tools") or {}).get("allow") or []
if not any("prometheus" in str(x) for x in allow):
    print("FAIL: alert tools.allow missing prometheus-mcp__*")
    sys.exit(1)
fat = ("pyats-mcp", "cml-mcp", "github-mcp", "nautobot-mcp", "drawio-mcp")
# Explicit allowlist — fat servers must not appear as allow entries
for a in allow:
    for f in fat:
        if f in str(a):
            print(f"FAIL: thin profile allows fat server {f} via {a}")
            sys.exit(1)
hooks = d.get("hooks") or {}
if "alert" not in (hooks.get("allowedAgentIds") or []):
    print("FAIL: hooks.allowedAgentIds missing alert")
    sys.exit(1)
ok = False
deliver_ok = False
for m in hooks.get("mappings") or []:
    if isinstance(m, dict) and (m.get("match") or {}).get("path") == "alert":
        if m.get("agentId") == "alert":
            ok = True
        if m.get("deliver") is False:
            deliver_ok = True
if not ok:
    print("FAIL: hooks.mappings alert path agentId != alert")
    sys.exit(1)
if not deliver_ok:
    print("FAIL: hooks.mappings alert path must set deliver=false (no chat channel on hooks)")
    sys.exit(1)
print("OK: thin alert agent profile present and hooked (deliver=false)")
PY
}

case "$cmd" in
  show) show ;;
  apply) apply ;;
  validate) validate ;;
  *)
    echo "Usage: $0 {show|apply|validate} [--no-restart]" >&2
    exit 2
    ;;
esac
