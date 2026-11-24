#!/usr/bin/env bash
# Spec 198 member tooling for one HA group (hosted Sonnet only, no local model).
#   R10_RUN_ID=<id> GROUP=<tag> GEN=<gen dir> bash scripts/ha-r10-members.sh build <flavor:name>...   # e.g. netbox:az1 subnet:azsn1
#   R10_RUN_ID=<id> GROUP=<tag> bash scripts/ha-r10-members.sh start <name>...                       # run on this Mac, dialing the group's Borders
#   R10_RUN_ID=<id> bash scripts/ha-r10-members.sh stop                                               # only this run's members
# build writes $EV/members/<name>.json (identity for enroll-members). Secrets come from ~/.openclaw/.env and .env at run time only.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"; cd "$here"
verb="${1:?build|start|stop}"; shift || true
RUN="${R10_RUN_ID:-}"; EV="${EV:-$HOME/.local/share/netclaw/r10-run-$RUN}"; PY="${R10_PY:-python3}"
export PYTHONPATH="$here/mcp-servers/protocol-mcp:$here"
case "$verb" in
  build)
    : "${RUN:?R10_RUN_ID}"; GEN="${GEN:?GEN (group generation dir)}"; mkdir -p "$EV/members"; chmod 700 "$EV/members"
    NVENV="${R10_NETBOX_ENV:-}"; [ -n "$NVENV" ] || NVENV="$(ls -d "$HOME"/.local/share/netclaw/r10-run-*/member-*/netbox-python/venv 2>/dev/null | head -1)"
    NT="$(python3 scripts/write-env.py --get ~/.openclaw/.env NETBOX_TOKEN)"; NU="$(python3 scripts/write-env.py --get ~/.openclaw/.env NETBOX_URL)"
    AK="$(python3 scripts/write-env.py --get "${R10_ENV_FILE:-$here/.env}" ANTHROPIC_API_KEY)"
    one() { local flavor="${1%%:*}" n="${1##*:}" M="$EV/member-${1##*:}"; R() { "$PY" labs/ha/r09_member.py "$@"; }
      R identity --root "$M" --deployment "$GEN" --flavor "$flavor" >/dev/null 2>&1 && R freeze --root "$M" >/dev/null 2>&1 && R python-env --root "$M" >/dev/null 2>&1 || { echo "$n: base step failed"; return 1; }
      case "$flavor" in
        netbox) [ -n "$NVENV" ] || { echo "no NetBox MCP env (set R10_NETBOX_ENV or build one with: r09_member.py netbox-env --build --yes-network)"; return 1; }
                R netbox-env --root "$M" --env "$NVENV" >/dev/null 2>&1 && NETBOX_TOKEN="$NT" ANTHROPIC_API_KEY="$AK" R artifacts --root "$M" --netbox-url "$NU" >/dev/null 2>&1;;
        subnet|pyats) ANTHROPIC_API_KEY="$AK" R artifacts --root "$M" >/dev/null 2>&1;;
        *) echo "$n: flavor $flavor refused (hosted flavors only: netbox, subnet, pyats)"; return 1;;
      esac
      R materialize --root "$M" >/dev/null 2>&1 && R validate --root "$M" 2>&1 | grep -c '"valid"' | sed "s/^/$n valid=/"
      cp "$M/identity/member.json" "$EV/members/$n.json"; chmod 600 "$EV/members/$n.json"; }
    pids=(); for spec in "$@"; do one "$spec" & pids+=($!); done; rc=0; for p in "${pids[@]}"; do wait "$p" || rc=1; done; exit $rc;;
  start)
    : "${RUN:?R10_RUN_ID}"
    for n in "$@"; do M="$EV/member-$n"; P="$(python3 -c "import json;print(json.load(open('$M/contract.json'))['python'])")"; H="$(python3 -c "import json;print(json.load(open('$M/contract.json'))['home'])")"
      (cd "$H" && env -i PATH=/usr/bin:/bin:/usr/local/bin HOME="$H" nohup "$P" -I -B "$M/source/scripts/protected-role.py" --contract "$M/contract.json" run > "$EV/member-$n.log" 2>&1 &); done; echo "started $#";;
  stop) : "${RUN:?R10_RUN_ID}"; "$PY" "$here/labs/ha/r10_processes.py" --root "$EV";;
  *) echo "unknown verb" >&2; exit 2;;
esac
