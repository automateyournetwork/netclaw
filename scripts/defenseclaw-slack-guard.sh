#!/usr/bin/env bash
# Re-assert the Slack passthrough patch in DefenseClaw's vendored dist/.
#
# Why this exists: DefenseClaw's fetch-interceptor false-positives Slack as an
# LLM call, because hasLLMPathSuffix() uses `path.includes(s)` and "/api/chat"
# is in LLM_PATH_SUFFIXES for Ollama. Slack's "/api/chat.postMessage" contains
# it, so the call gets proxied to the guardrail sidecar and comes back 403.
# The fix is one entry in KNOWN_SAFE_DOMAINS. Because that lives in a vendored
# dist/ file, every `defenseclaw upgrade` (and, seen on 2026-08-06, a plain
# extension re-extract at boot) silently wipes it. When it's wiped the agent
# keeps running and keeps composing heartbeats — they just never arrive. That
# failure mode cost ~7h of silence on 2026-08-06 and a full day on 2026-08-05.
#
# Do NOT "fix" this with `defenseclaw setup provider add` instead. Registration
# is what *triggers* interception (shouldIntercept = knownLLM), so it makes the
# problem worse and additionally breaks Socket Mode, whose WebSocket upgrade the
# HTTP-only sidecar answers with 200 instead of 101.
#
# Idempotent. Non-fatal by design: a broken guard must never keep the gateway
# from starting. It shouts into the journal instead, so the next failure is
# visible in `journalctl --user -u openclaw-gateway | grep slack-guard`.

set -uo pipefail

TARGET="${DEFENSECLAW_INTERCEPTOR:-$HOME/.openclaw/extensions/defenseclaw/dist/fetch-interceptor.js}"
TAG="[slack-guard]"

log()  { echo "$TAG $*"; }
warn() { echo "$TAG WARNING: $*" >&2; }
err()  { echo "$TAG ERROR: $*" >&2; }

if [[ ! -f "$TARGET" ]]; then
    warn "interceptor not found at $TARGET — DefenseClaw not installed? nothing to do"
    exit 0
fi

if grep -q '"slack\.com"' "$TARGET"; then
    log "OK — slack.com already in KNOWN_SAFE_DOMAINS"
    exit 0
fi

err "slack.com MISSING from KNOWN_SAFE_DOMAINS — patch was reverted (DefenseClaw upgrade or re-extract). Re-applying; Slack delivery would 403 without this."

if ! grep -q '"login\.microsoftonline\.com",' "$TARGET"; then
    err "anchor 'login.microsoftonline.com' not found — DefenseClaw's safe-domain list changed shape. NOT patching blindly. Slack delivery WILL fail with 403 until this script is updated against the new dist/."
    exit 0
fi

cp -p "$TARGET" "$TARGET.bak-slackguard-$(date +%Y%m%d-%H%M%S)" 2>/dev/null \
    || warn "could not write backup; continuing"

# Insert after the last existing entry rather than rewriting the array, so an
# upstream change to the list's contents doesn't get clobbered.
if sed -i 's|^\(\s*\)"login\.microsoftonline\.com",|\1"login.microsoftonline.com",\n\1// NetClaw: see ~/.openclaw/bin/defenseclaw-slack-guard.sh — /api/chat.postMessage\n\1// contains the Ollama suffix /api/chat and gets proxied -> 403 without this.\n\1"slack.com",|' "$TARGET"; then
    if grep -q '"slack\.com"' "$TARGET"; then
        log "re-applied successfully — slack.com restored to KNOWN_SAFE_DOMAINS"
    else
        err "sed reported success but slack.com is still absent — Slack delivery WILL fail with 403. Patch $TARGET by hand."
    fi
else
    err "sed failed against $TARGET — Slack delivery WILL fail with 403. Patch by hand."
fi

exit 0
