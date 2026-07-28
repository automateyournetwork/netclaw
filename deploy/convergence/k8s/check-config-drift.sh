#!/usr/bin/env bash
# Guard against the K8s config copies drifting from their Docker originals.
#
# WHY THIS EXISTS: base/configs/device.rules.yml carried a "Keep in sync with
# deploy/convergence/prometheus/alerts/device.rules.yml" comment and had drifted
# by 210 diff lines — including alert rules that still selected retired metric
# names. A comment is not a mechanism.
#
# Kustomize refuses to load files outside its kustomization root, and requiring
# operators to pass --load-restrictor LoadRestrictionsNone is worse than a copy,
# so these stay copies with an automated check.
#
# Usage:
#   ./check-config-drift.sh          # report drift, exit 1 if any
#   ./check-config-drift.sh --fix    # copy Docker → K8s, then report what changed
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY="$(cd "${HERE}/.." && pwd)"
FIX=0
[[ "${1:-}" == "--fix" ]] && FIX=1

# k8s copy : docker source
PAIRS=(
  "${HERE}/components/otel-collector/configs/otel-config.yaml:${DEPLOY}/otel/otel-config.yaml"
  "${HERE}/base/configs/device.rules.yml:${DEPLOY}/prometheus/alerts/device.rules.yml"
  "${HERE}/base/configs/home.rules.yml:${DEPLOY}/prometheus/alerts/home.rules.yml"
)

# The copies carry a provenance header the source does not; strip leading comment
# lines that name the source file before comparing.
strip_header() {
  sed '/^# COPY OF /,/^# still matches; the previous copies silently drifted for weeks\.$/d' "$1"
}

drift=0
for pair in "${PAIRS[@]}"; do
  copy="${pair%%:*}"
  src="${pair##*:}"
  rel_copy="${copy#"${DEPLOY}/"}"
  rel_src="${src#"${DEPLOY}/"}"

  if [[ ! -f "$src" ]]; then
    echo "MISSING SOURCE  $rel_src"
    drift=1
    continue
  fi
  if [[ ! -f "$copy" ]]; then
    echo "MISSING COPY    $rel_copy"
    drift=1
    continue
  fi

  if diff -q <(strip_header "$copy") "$src" >/dev/null 2>&1; then
    echo "OK              $rel_copy"
    continue
  fi

  drift=1
  n=$(diff <(strip_header "$copy") "$src" | grep -c '^[<>]' || true)
  echo "DRIFT ($n lines) $rel_copy"
  echo "                 vs $rel_src"
  if [[ "$FIX" -eq 1 ]]; then
    header=$(sed -n '/^# COPY OF /,/^# still matches; the previous copies silently drifted for weeks\.$/p' "$copy")
    { printf '%s\n' "$header"; cat "$src"; } > "$copy"
    echo "                 FIXED (copied source → k8s)"
  else
    diff <(strip_header "$copy") "$src" | head -12 | sed 's/^/                 /'
  fi
done

echo
if [[ "$drift" -eq 0 ]]; then
  echo "No drift."
  exit 0
fi
if [[ "$FIX" -eq 1 ]]; then
  echo "Drift fixed — re-run without --fix to confirm, then rebuild the overlays."
  exit 0
fi
echo "Drift detected. Run with --fix, or reconcile by hand if the K8s copy is right."
exit 1
