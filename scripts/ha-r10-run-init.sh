#!/usr/bin/env bash
# Spec 198: create a bounded R10 run: private evidence dir, cleanup manifest and a launchd watchdog (macOS).
#   ha-r10-run-init.sh <run-id> <hours> [<resource-group>...] [--gcp-project <project> [--gcp-firewall <nc198-name>]...]
# GCP scope: instances and addresses labelled netclaw-spec=198 + run-id=<run-id> (the GCP driver applies both labels when
# R10_RUN_ID is set) and the exact firewall rules named (firewall rules cannot be labelled).
# The watchdog deletes ONLY the listed groups, and only if they carry tags netclaw-spec=198 and run-id=<run-id>,
# after the deadline. Host-dependent fallback, not a provider spending cap. Remove with ha-r10-run-fini.sh.
set -euo pipefail
run="${1:?run id}"; hours="${2:?hours}"; shift 2
groups=(); gproj=""; gfw=()
while [ "$#" -gt 0 ]; do case "$1" in
  --gcp-project) gproj="${2:?project}"; shift 2;;
  --gcp-firewall) case "${2:?name}" in nc198-*) gfw+=("$2");; *) echo "refused: firewall $2 is not nc198-" >&2; exit 2;; esac; shift 2;;
  *) case "$1" in rg-nc198-*) groups+=("$1");; *) echo "refused: $1 is not an rg-nc198- group" >&2; exit 2;; esac; shift;;
esac; done
[ "${#groups[@]}" -gt 0 ] || [ -n "$gproj" ] || { echo "at least one resource group or --gcp-project" >&2; exit 2; }
set -- "${groups[@]+"${groups[@]}"}"
here="$(cd "$(dirname "$0")/.." && pwd)"
ev="$HOME/.local/share/netclaw/r10-run-$run"; mkdir -p "$ev"; chmod 700 "$ev"
[ ! -e "$ev/watchdog-manifest.json" ] && [ ! -L "$ev/watchdog-manifest.json" ] || { echo "refused: run preparation already spent; choose a fresh run identity" >&2; exit 3; }
[ ! -e "$HOME/Library/LaunchAgents/com.netclaw.r10-$run-cleanup.plist" ] || { echo "refused: watchdog identity already exists" >&2; exit 3; }
sub=""; azbin=""; if [ "${#groups[@]}" -gt 0 ]; then sub="$(az account show --query id -o tsv)"; azbin="$(command -v az)"; fi
export R10_WD_GCP_PROJECT="$gproj" R10_WD_GCLOUD="$(command -v gcloud || true)" R10_WD_FIREWALLS="${gfw[*]-}"
python3 - "$ev/watchdog-manifest.json" "$run" "$hours" "$sub" "$azbin" "$@" <<'PY'
import json, os, sys, time
path, run, hours, sub, az = sys.argv[1:6]
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, 'w') as f:
    manifest = {'run_id': run, 'deadline_at': time.time() + float(hours) * 3600, 'subscription_id': sub, 'az': az,
                'azure_groups': sys.argv[6:]}
    if os.environ.get('R10_WD_GCP_PROJECT'):
        manifest['gcp'] = {'project': os.environ['R10_WD_GCP_PROJECT'], 'gcloud': os.environ['R10_WD_GCLOUD'],
                           'firewalls': os.environ.get('R10_WD_FIREWALLS', '').split()}
    json.dump(manifest, f)
PY
label="com.netclaw.r10-$run-cleanup"; plist="$HOME/Library/LaunchAgents/$label.plist"
cat > "$plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
<key>Label</key><string>$label</string>
<key>ProgramArguments</key><array><string>/opt/homebrew/bin/python3</string><string>$here/labs/ha/r10_watchdog.py</string><string>$ev/watchdog-manifest.json</string></array>
<key>RunAtLoad</key><true/>
<key>StartInterval</key><integer>60</integer>
<key>StandardOutPath</key><string>$ev/watchdog.stdout.log</string>
<key>StandardErrorPath</key><string>$ev/watchdog.stderr.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$plist"
echo "run $run: deadline in ${hours}h, groups: ${*:-none}${gproj:+, gcp project $gproj}, evidence: $ev"
