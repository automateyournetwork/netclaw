#!/usr/bin/env bash
# Keeps a GoDaddy A record pointing at this host's current public IP.
#
# Why this exists: the NCFED edge (phone) listener is reached by domain name,
# and enrolled phones store that name — so on a residential connection, an ISP
# IP rotation silently breaks every enrolled device. The failure surfaces on the
# phone as "Failed host lookup"/timeout with nothing wrong on the Border, which
# is genuinely hard to diagnose from the app side.
#
# Only rewrites the record when the IP actually differs, so the normal case
# costs one HTTPS GET and touches nothing.
#
#   GODADDY_PAT   required   gd_pat_… token (Bearer auth, same one the ACME
#                            DNS-01 hook uses — see scripts/lib/godaddy-acme-hook.sh)
#   DDNS_DOMAIN   required   registered domain, e.g. example.com
#   DDNS_NAME     required   record name, e.g. netclaw  ("@" for the apex)
#   DDNS_TTL      optional   default 600
#
# Exit 0 = record correct (changed or already fine). Exit non-zero = could not
# determine the IP or the API rejected the update.
set -uo pipefail

API="https://api.godaddy.com/v1"
TTL="${DDNS_TTL:-600}"
: "${GODADDY_PAT:?set GODADDY_PAT}"
: "${DDNS_DOMAIN:?set DDNS_DOMAIN}"
: "${DDNS_NAME:?set DDNS_NAME}"

log() { printf '%s ddns: %s\n' "$(date -Is)" "$*"; }

# Several providers, because a single one being down or rate-limiting shouldn't
# look like an IP change. Anything that isn't a plausible IPv4 is discarded.
current_ip() {
    local ip
    for url in https://api.ipify.org https://ifconfig.me/ip https://icanhazip.com; do
        ip="$(curl -fsS --max-time 10 "$url" 2>/dev/null | tr -d '[:space:]')"
        if [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
            printf '%s' "$ip"; return 0
        fi
    done
    return 1
}

published_ip() {
    curl -fsS --max-time 15 \
        -H "Authorization: Bearer ${GODADDY_PAT}" -H "Accept: application/json" \
        "$API/domains/${DDNS_DOMAIN}/records/A/${DDNS_NAME}" 2>/dev/null \
      | python3 -c 'import json,sys
try:
    r=json.load(sys.stdin)
    print(r[0]["data"] if isinstance(r,list) and r else "")
except Exception:
    print("")'
}

wanted="$(current_ip)" || { log "ERROR could not determine public IP from any provider"; exit 1; }
have="$(published_ip)"

if [ "$wanted" = "$have" ]; then
    log "ok ${DDNS_NAME}.${DDNS_DOMAIN} already = ${wanted}"
    exit 0
fi

log "updating ${DDNS_NAME}.${DDNS_DOMAIN}: '${have:-<unset>}' -> ${wanted}"
code="$(curl -fsS --max-time 20 -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer ${GODADDY_PAT}" -H "Content-Type: application/json" \
    -X PUT "$API/domains/${DDNS_DOMAIN}/records/A/${DDNS_NAME}" \
    -d "[{\"data\":\"${wanted}\",\"ttl\":${TTL}}]" 2>/dev/null)" || code="000"

case "$code" in
    2*) log "updated ${DDNS_NAME}.${DDNS_DOMAIN} -> ${wanted} (ttl ${TTL})" ;;
    *)  log "ERROR GoDaddy PUT returned HTTP ${code}"; exit 1 ;;
esac
