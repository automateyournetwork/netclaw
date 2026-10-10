#!/usr/bin/env bash
# Rebuild the HUD from this checkout; preserve runtime configuration and Canvas storage.
set -euo pipefail
HUD_UPGRADE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUD_UPGRADE_APPLY=false
HUD_UPGRADE_INSTALL=false
usage() {
  cat <<'HELP'
Usage: scripts/upgrade-hud.sh [--check | --apply] [--install-deps] [--repo PATH]
  --check         Check source, prerequisites and installed dependencies (default).
  --apply         Regenerate references and build all four HUD entry points.
  --install-deps  Run npm ci from the lockfile before building; requires --apply.
  --repo PATH     Use another existing NetClaw checkout.
  -h, --help      Show this help.

This upgrades the HUD assets from the selected checkout only. It does not git pull,
change .env/security modes, migrate browser storage, start/restart services, or
upgrade federation members. Keep the same UI hostname/port to retain browser data.
The common whole-installation upgrade utility remains separate planned work.
HELP
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) HUD_UPGRADE_APPLY=false ;;
    --apply) HUD_UPGRADE_APPLY=true ;;
    --install-deps) HUD_UPGRADE_INSTALL=true ;;
    --repo) [[ $# -ge 2 ]] || { echo 'Missing --repo path' >&2; exit 2; }; HUD_UPGRADE_ROOT="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
if [[ "$HUD_UPGRADE_INSTALL" == true && "$HUD_UPGRADE_APPLY" != true ]]; then
  echo '--install-deps requires --apply; check mode never installs packages.' >&2
  exit 2
fi
HUD_UPGRADE_ROOT="$(cd "$HUD_UPGRADE_ROOT" && pwd)"
HUD_UPGRADE_UI="$HUD_UPGRADE_ROOT/ui/netclaw-visual"
for command in node npm python3 git; do
  command -v "$command" >/dev/null || { echo "Missing prerequisite: $command" >&2; exit 1; }
done
for entry in index.html canvas.html classic.html assessment.html package-lock.json; do
  [[ -f "$HUD_UPGRADE_UI/$entry" ]] || { echo "Missing HUD source: $entry" >&2; exit 1; }
done
[[ -f "$HUD_UPGRADE_ROOT/scripts/build-hud-reference.py" ]] || { echo 'Missing reference generator' >&2; exit 1; }
for helper in hud-node-version.mjs hud-launch.mjs; do
  [[ -f "$HUD_UPGRADE_ROOT/scripts/$helper" ]] || { echo "Missing HUD source: scripts/$helper" >&2; exit 1; }
done
node "$HUD_UPGRADE_ROOT/scripts/hud-node-version.mjs"
node "$HUD_UPGRADE_ROOT/scripts/hud-launch.mjs" status || exit 1
echo 'Runtime selection validated. Hermes companion upgrades require explicit hermes-hud installation; this command never restarts it.'
if [[ "$HUD_UPGRADE_INSTALL" == true ]]; then
  (cd "$HUD_UPGRADE_UI" && npm ci)
fi
(cd "$HUD_UPGRADE_UI" && node --input-type=module -e 'await import("vite"); await import("react"); await import("three");') || {
  echo 'HUD dependencies unavailable. Review --apply --install-deps.' >&2; exit 1;
}
echo "HUD source and prerequisites ready: $HUD_UPGRADE_UI"
if [[ "$HUD_UPGRADE_APPLY" != true ]]; then
  echo 'Check complete. No files or services changed. Use --apply to build this checkout.'
  exit 0
fi
(cd "$HUD_UPGRADE_ROOT" && python3 scripts/build-hud-reference.py)
(cd "$HUD_UPGRADE_UI" && npm run build)
for entry in index.html canvas.html classic.html assessment.html; do
  [[ -s "$HUD_UPGRADE_UI/dist/$entry" ]] || { echo "Build omitted $entry" >&2; exit 1; }
done
echo 'HUD build verified: dashboard, Canvas, classic utilities and assessment entries.'
echo 'Runtime configuration, services and browser storage were not changed.'
echo 'Restart your existing HUD process when ready; verify live sources and Canvas on the same origin.'
echo 'Agent members need their own code update/reconnect to report new MCP/model metadata.'
