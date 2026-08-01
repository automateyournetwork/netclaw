#!/usr/bin/env bash
# SuzieQ poller freshness probe (Phase 12, T164).
#
# Queries the sqPoller table via the REST API and pushes the newest timestamp
# to Prometheus Pushgateway as suzieq_poller_newest_timestamp_seconds.
#
# The SuzieQPollerStale alert fires when this metric is >10 minutes old,
# indicating the poller has stopped collecting.
#
# Run as a cron job or sidecar every 60s:
#   */1 * * * * /path/to/freshness-probe.sh
#
# Requires: curl, jq
# Env: SUZIEQ_API_KEY, SUZIEQ_REST_URL (default http://suzieq-rest:8000),
#      PUSHGATEWAY_URL (default http://pushgateway:9091)
set -uo pipefail

SUZIEQ_REST_URL="${SUZIEQ_REST_URL:-http://suzieq-rest:8000}"
PUSHGATEWAY_URL="${PUSHGATEWAY_URL:-http://pushgateway:9091}"
API_KEY="${SUZIEQ_API_KEY:-change-me}"

# Query sqPoller for the newest timestamp across all services/hosts
RESPONSE=$(curl -sf "${SUZIEQ_REST_URL}/api/v2/sqPoller/show?access_token=${API_KEY}&columns=timestamp&view=latest" 2>/dev/null)

if [[ -z "$RESPONSE" ]]; then
  echo "WARN: SuzieQ REST unreachable or returned empty" >&2
  exit 0  # Don't push — absence of metric triggers SuzieQPollerProbeAbsent
fi

# Extract newest timestamp (epoch ms) from the JSON array
NEWEST_MS=$(echo "$RESPONSE" | jq -r '[.[].timestamp // 0] | max' 2>/dev/null)

if [[ -z "$NEWEST_MS" || "$NEWEST_MS" == "null" || "$NEWEST_MS" == "0" ]]; then
  echo "WARN: No valid timestamps in sqPoller response" >&2
  exit 0
fi

# Convert ms to seconds
NEWEST_S=$(echo "scale=3; $NEWEST_MS / 1000" | bc 2>/dev/null || echo "$((NEWEST_MS / 1000))")

# Push to Pushgateway
cat <<EOF | curl -sf --data-binary @- "${PUSHGATEWAY_URL}/metrics/job/suzieq-freshness" >/dev/null 2>&1
# HELP suzieq_poller_newest_timestamp_seconds Newest record timestamp in the SuzieQ lake (epoch seconds)
# TYPE suzieq_poller_newest_timestamp_seconds gauge
suzieq_poller_newest_timestamp_seconds ${NEWEST_S}
EOF

echo "Pushed suzieq_poller_newest_timestamp_seconds=${NEWEST_S} ($(date -d @${NEWEST_S%.*} '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || date -r ${NEWEST_S%.*} '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || echo 'unknown'))"
