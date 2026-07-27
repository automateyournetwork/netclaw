#!/usr/bin/env bash
# T142 smoke — every Loki query on the provisioned boards must parse, and the
# label selectors must resolve to real streams.
#
# WHY: the previous panels selected streams with message-content regex, which
# cannot fail loudly — a query that matches nothing looks exactly like a healthy
# quiet network. This script asserts the queries are valid LogQL and reports how
# many streams each one currently resolves to, so "empty" is always attributable.
#
# Usage:  LOKI_URL=http://127.0.0.1:3100 ./deploy/convergence/smoke-log-panels.sh
set -uo pipefail

LOKI_URL="${LOKI_URL:-http://127.0.0.1:3100}"
DASH_DIR="${DASH_DIR:-$(dirname "$0")/grafana/provisioning/dashboards/json}"
WINDOW="${WINDOW:-3600}"

end=$(date +%s)
start=$((end - WINDOW))
fail=0
checked=0

echo "Loki:   $LOKI_URL"
echo "Window: last $((WINDOW / 60))m"
echo

# Extract (board, panel title, expr) for every Loki target.
mapfile -t rows < <(python3 - "$DASH_DIR" <<'PY'
import json, pathlib, sys
for f in sorted(pathlib.Path(sys.argv[1]).glob("*.json")):
    d = json.loads(f.read_text())
    for p in d.get("panels", []):
        for t in p.get("targets", []) or []:
            ds = t.get("datasource") or p.get("datasource") or {}
            uid = ds.get("uid") if isinstance(ds, dict) else ds
            expr = t.get("expr")
            if expr and uid and "loki" in str(uid):
                print("\t".join([f.stem, p.get("title", "?"), expr.replace("\n", " ")]))
PY
)

if [ "${#rows[@]}" -eq 0 ]; then
    echo "FAIL: no Loki targets found in $DASH_DIR"
    exit 1
fi

for row in "${rows[@]}"; do
    board="${row%%$'\t'*}"
    rest="${row#*$'\t'}"
    title="${rest%%$'\t'*}"
    expr="${rest#*$'\t'}"
    checked=$((checked + 1))

    # Metric queries (rate/sum) go to /query; stream selectors go to /series so we
    # can count resolved streams rather than scan lines.
    if [[ "$expr" == *"rate("* || "$expr" == *"count_over_time"* ]]; then
        body=$(curl -sG --max-time 20 "$LOKI_URL/loki/api/v1/query" \
            --data-urlencode "query=$expr" --data-urlencode "time=${end}000000000")
        status=$(printf '%s' "$body" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status","error"))' 2>/dev/null || echo error)
        n=$(printf '%s' "$body" | python3 -c 'import sys,json;print(len(json.load(sys.stdin).get("data",{}).get("result",[])))' 2>/dev/null || echo 0)
        kind="series"
    else
        # Count matching lines rather than asking /series for streams.
        #
        # /series answers from the index at chunk granularity, so a sparse but
        # healthy source can report 0 streams while count_over_time on the same
        # selector returns real lines (observed with an idle openclaw-gateway:
        # 0 streams vs 4 lines). Counting lines exercises the actual query the
        # panel runs, including its line filters.
        wrapped="sum(count_over_time($expr [${WINDOW}s]))"
        body=$(curl -sG --max-time 25 "$LOKI_URL/loki/api/v1/query" \
            --data-urlencode "query=$wrapped" --data-urlencode "time=${end}000000000")
        status=$(printf '%s' "$body" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status","error"))' 2>/dev/null || echo error)
        n=$(printf '%s' "$body" | python3 -c 'import sys,json;r=json.load(sys.stdin).get("data",{}).get("result",[]);print(int(float(r[0]["value"][1])) if r else 0)' 2>/dev/null || echo 0)
        kind="lines"
    fi

    if [ "$status" != "success" ]; then
        echo "FAIL  [$board] $title"
        echo "      query: $expr"
        printf '      loki:  %s\n' "$(printf '%s' "$body" | head -c 200)"
        fail=$((fail + 1))
        continue
    fi

    if [ "$n" -eq 0 ]; then
        echo "EMPTY [$board] $title  (0 $kind — source not deployed or idle)"
    else
        echo "OK    [$board] $title  ($n $kind)"
    fi
done

echo
echo "checked=$checked failed=$fail"
[ "$fail" -eq 0 ] || exit 1
