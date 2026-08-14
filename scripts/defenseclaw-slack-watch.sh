#!/usr/bin/env bash
# Continuously re-assert the DefenseClaw Slack passthrough patch.
#
# Why a watcher and not just ExecStartPre: the ExecStartPre guard
# (defenseclaw-slack-guard.sh) was verified working on 2026-08-06 and then
# silently started losing. Proof from 2026-08-10: the guard patched the file at
# 10:55:35, and the file's mtime was 10:55:36.87 — DefenseClaw re-extracts its
# ENTIRE vendored extension directory during gateway startup, i.e. *after*
# ExecStartPre has already run. A pre-start hook therefore cannot win: whatever
# it writes is overwritten ~1.4s later, every single start.
#
# The consequence is invisible and expensive. The gateway loads
# dist/fetch-interceptor.js into memory once at startup and never re-reads it,
# so patching the file afterwards changes nothing until the next restart —
# while the agent keeps running, keeps composing heartbeats, and every Slack
# delivery 403s with nothing retrying and no health surface showing it.
#
# So this polls tightly through the startup window and re-applies the patch the
# instant re-extraction lands, before the plugin imports the module. It cannot
# break DefenseClaw's own install the way making the file immutable might: it
# only ever adds a domain back to KNOWN_SAFE_DOMAINS via the anchored,
# idempotent guard script, and never blocks or fails a write.
#
# After the startup window it keeps polling cheaply, so a `defenseclaw upgrade`
# at any hour is also caught rather than waiting for the next restart.

set -uo pipefail

GUARD="${DEFENSECLAW_SLACK_GUARD:-$HOME/.openclaw/bin/defenseclaw-slack-guard.sh}"
TARGET="${DEFENSECLAW_INTERCEPTOR:-$HOME/.openclaw/extensions/defenseclaw/dist/fetch-interceptor.js}"
TAG="[slack-watch]"

# Tight polling only for the startup race; slow polling forever after, so this
# costs effectively nothing at steady state.
FAST_WINDOW_S="${SLACK_WATCH_FAST_WINDOW_S:-180}"
FAST_INTERVAL="${SLACK_WATCH_FAST_INTERVAL:-0.2}"
SLOW_INTERVAL="${SLACK_WATCH_SLOW_INTERVAL:-5}"

if [[ ! -x "$GUARD" ]]; then
    echo "$TAG ERROR: guard script not executable at $GUARD — nothing to enforce" >&2
    exit 1
fi

echo "$TAG watching $TARGET (fast ${FAST_INTERVAL}s for ${FAST_WINDOW_S}s, then ${SLOW_INTERVAL}s)"

started=$(date +%s)
reapplied=0

while true; do
    now=$(date +%s)
    elapsed=$(( now - started ))
    if (( elapsed < FAST_WINDOW_S )); then
        interval="$FAST_INTERVAL"
    else
        interval="$SLOW_INTERVAL"
    fi

    # Only act when the entry is actually gone. grep on a missing file is a
    # non-match, which is correct: the guard handles the not-yet-extracted case.
    if [[ -f "$TARGET" ]] && ! grep -q '"slack\.com"' "$TARGET" 2>/dev/null; then
        reapplied=$(( reapplied + 1 ))
        echo "$TAG caught a wipe (${elapsed}s after start, occurrence #${reapplied}) — re-applying"
        "$GUARD" 2>&1 | sed "s/^/$TAG /"
    fi

    sleep "$interval"
done
