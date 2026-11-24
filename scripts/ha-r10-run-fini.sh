#!/usr/bin/env bash
# Spec 198: unload the run's watchdog. Only after zero owned cloud resources are observed.
set -euo pipefail
run="${1:?run id}"; label="com.netclaw.r10-$run-cleanup"
n="$(az resource list --tag "run-id=$run" --query 'length(@)' -o tsv)"
[ "$n" = "0" ] || { echo "refused: $n resources still carry run-id=$run" >&2; exit 3; }
if [ -n "${R10_GCP_PROJECT:-}" ]; then
  g="$(gcloud compute instances list --project "$R10_GCP_PROJECT" --filter "labels.run-id=$run" --format='value(name)' | wc -l | tr -d ' ')"
  a="$(gcloud compute addresses list --project "$R10_GCP_PROJECT" --filter "labels.run-id=$run" --format='value(name)' | wc -l | tr -d ' ')"
  [ "$g$a" = "00" ] || { echo "refused: $g GCP instances and $a addresses still carry run-id=$run" >&2; exit 3; }
fi
launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
mv "$HOME/Library/LaunchAgents/$label.plist" "$HOME/.local/share/netclaw/r10-run-$run/cleanup.plist.disabled" 2>/dev/null || true
echo "watchdog $label unloaded"
