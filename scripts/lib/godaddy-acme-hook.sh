#!/usr/bin/env bash
# lego exec-provider hook for GoDaddy new-style Personal Access Tokens (feature 060).
#
# GoDaddy's newer PATs (gd_pat_...) authenticate with `Authorization: Bearer`,
# which lego's built-in `godaddy` provider does NOT support (it uses the legacy
# sso-key KEY:SECRET header). This hook lets an operator with a PAT use the
# domain-verified path anyway:
#
#   export GODADDY_PAT=gd_pat_xxxxxxxx
#   export EXEC_PATH="$PWD/scripts/lib/godaddy-acme-hook.sh"
#   lego --dns exec --domains netclaw.automateyournetwork.ca --email you@x --accept-tos run
#
# lego invokes:  $EXEC_PATH present|cleanup <fqdn> <token-unused> <txt-value>
# (present adds the _acme-challenge TXT; cleanup removes it).
set -euo pipefail

ACTION="${1:?present|cleanup}"
FQDN="${2:?challenge fqdn}"          # e.g. _acme-challenge.netclaw.automateyournetwork.ca.
VALUE="${4:-${3:-}}"                 # lego passes (fqdn, token, value); value is arg 3 in some versions
: "${GODADDY_PAT:?set GODADDY_PAT to your gd_pat_ token}"

API="https://api.godaddy.com/v1"
FQDN="${FQDN%.}"                     # strip trailing dot

# Split the FQDN into the registered domain (last two labels) + record name.
DOMAIN="$(echo "$FQDN" | awk -F. '{print $(NF-1)"."$NF}')"
NAME="${FQDN%.$DOMAIN}"              # e.g. _acme-challenge.netclaw
[ "$NAME" = "$FQDN" ] && NAME="@"

hdr=(-H "Authorization: Bearer ${GODADDY_PAT}" -H "Content-Type: application/json")

case "$ACTION" in
  present)
    curl -s -o /dev/null -w "%{http_code}" --max-time 30 "${hdr[@]}" -X PUT \
      "$API/domains/$DOMAIN/records/TXT/$NAME" \
      -d "[{\"data\":\"${VALUE}\",\"ttl\":600}]" | grep -q '^2' \
      || { echo "godaddy present failed for $NAME.$DOMAIN" >&2; exit 1; }
    ;;
  cleanup)
    # Restore to an empty TXT at that name (GoDaddy has no per-value delete;
    # replacing with a single placeholder then it expires is the safe pattern).
    curl -s -o /dev/null --max-time 30 "${hdr[@]}" -X DELETE \
      "$API/domains/$DOMAIN/records/TXT/$NAME" || true
    ;;
  *) echo "unknown action $ACTION" >&2; exit 1 ;;
esac
