#!/usr/bin/env bash
# Spec 198: tear down EVERY billable asset of one or two R10 runs and confirm it. Idempotent; retries over flaky links.
#   AZ_RUN=<id> GC_RUN=<id> AZ_GROUP=rg-nc198-p3-ha-az GCP_PREFIX=nc198-p3-ha-gc DNS_NAMES="nne1-xxxxxx ew1-... ..." bash scripts/ha-r10-teardown-all.sh
# Order: member processes, Azure group (by name, tag-checked by the watchdog scripts), GCP instances+firewall+disks, DNS A+TXT, ledger, watchdogs, verification.
set -uo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"; cd "$here"; P="${GCP_PROJECT:-netclaw-506315}"; BASE="${DOMAIN_BASE:-automateyournetwork.com}"
bad=0; say() { printf '%s\n' "$*"; }; retry() { local n=$1; shift; for i in $(seq 1 "$n"); do "$@" && return 0; sleep 8; done; return 1; }
pkill -f "protected-role.py --contract" || true
if [ -n "${AZ_GROUP:-}" ]; then
  case "$AZ_GROUP" in rg-nc198-*) ;; *) say "refused: $AZ_GROUP"; exit 2;; esac
  retry 6 az group delete -n "$AZ_GROUP" -y --no-wait >/dev/null 2>&1 && say "azure delete requested: $AZ_GROUP" || { say "AZURE DELETE FAILED"; bad=1; }
fi
if [ -n "${GCP_PREFIX:-}" ]; then
  case "$GCP_PREFIX" in nc198-*) ;; *) say "refused: $GCP_PREFIX"; exit 2;; esac
  for i in 1 2 3 4; do
    for line in $(gcloud compute instances list --project="$P" --filter="name~^$GCP_PREFIX" --format='csv[no-heading](name,zone.basename())' 2>/dev/null); do
      gcloud compute instances delete "${line%%,*}" --zone="${line##*,}" --project="$P" --quiet --delete-disks=all >/dev/null 2>&1; done
    for f in $(gcloud compute firewall-rules list --project="$P" --filter="name~^$GCP_PREFIX" --format='value(name)' 2>/dev/null); do gcloud compute firewall-rules delete "$f" --project="$P" --quiet >/dev/null 2>&1; done
    [ -z "$(gcloud compute instances list --project="$P" --filter="name~^$GCP_PREFIX" --format='value(name)' 2>/dev/null)" ] && break; sleep 8; done
fi
if [ -n "${DNS_NAMES:-}" ]; then
  T="$(python3 scripts/write-env.py --get ~/.openclaw/.env GODADDY_PAT)"
  for n in $DNS_NAMES; do for kind in "A/$n" "TXT/_acme-challenge.$n"; do
    for i in 1 2 3 4; do c=$(curl -s -m 20 -o /dev/null -w '%{http_code}' -X DELETE -H "Authorization: Bearer $T" "https://api.godaddy.com/v1/domains/$BASE/records/$kind"); [ "$c" = 204 ] || [ "$c" = 404 ] && break; sleep 6; done; done; done
fi
for c in nne1 ew1 ase1; do   # close the spend-ledger entries (a still-open entry keeps accruing)
  [ -n "${AZ_GROUP:-}" ] && python3 labs/ha/r10_ledger.py stop "${AZ_PHASE:-p3-ha-az}" "azure-$c" >/dev/null 2>&1
  [ -n "${GCP_PREFIX:-}" ] && python3 labs/ha/r10_ledger.py stop "${GC_PHASE:-p3-ha-gc}" "gcp-$c" >/dev/null 2>&1
done
for r in ${AZ_RUN:-} ${GC_RUN:-}; do
  while [ "$(az group exists -n "${AZ_GROUP:-rg-nc198-none}" 2>/dev/null)" = true ] && [ -n "${AZ_GROUP:-}" ]; do sleep 20; done
  python3 labs/ha/r10_ledger.py status | grep -q '"open_entries": 0' || say "ledger still has open entries (stop them with r10_ledger.py stop <phase> <provider-code>)"
  R10_GCP_PROJECT="$P" bash scripts/ha-r10-run-fini.sh "$r" 2>&1 | tail -1
done
say "--- verification ---"
[ -n "${AZ_GROUP:-}" ] && say "azure group exists: $(az group exists -n "$AZ_GROUP" 2>&1 | tail -1)" && say "azure spec198 resources: $(az resource list --tag netclaw-spec=198 --query 'length(@)' -o tsv 2>&1 | tail -1)"
if [ -n "${GCP_PREFIX:-}" ]; then for k in instances disks addresses; do say "gcp $k matching nc198/nc182: $(gcloud compute $k list --project="$P" --format='value(name)' 2>/dev/null | grep -c -E 'nc198|nc182')"; done
  say "gcp firewall matching: $(gcloud compute firewall-rules list --project="$P" --format='value(name)' 2>/dev/null | grep -c -E 'nc198|nc182')"; fi
if [ -n "${DNS_NAMES:-}" ]; then T="$(python3 scripts/write-env.py --get ~/.openclaw/.env GODADDY_PAT)"; left=0
  for n in $DNS_NAMES; do for kind in "A/$n" "TXT/_acme-challenge.$n"; do r=$(curl -s -m 20 -H "Authorization: Bearer $T" "https://api.godaddy.com/v1/domains/$BASE/records/$kind"); [ "$r" = "[]" ] || { left=$((left+1)); say "DNS record still present or unreadable: $kind"; }; done; done; say "dns records remaining: $left"; fi
say "launchd watchdogs: $(launchctl list | grep -c com.netclaw.r10)   member processes: $(ps aux | grep -c '[p]rotected-role')"
python3 labs/ha/r10_ledger.py status | tail -1
exit $bad
