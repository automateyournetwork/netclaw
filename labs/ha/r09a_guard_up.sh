#!/bin/bash
# R09A (spec 183): bring up the DefenseClaw sidecar and the OpenClaw chat agent INSIDE the node sandbox. Idempotent.
# Run by the node runner (`CTL/run-script`, lab-only) so it inherits the OpenShell provider placeholder environment.
# Needs: /sandbox/guard-config.yaml (the derived node guard config, `python -m labs.ha.r09a_defenseclaw render`).
# Never prints a key: ANTHROPIC_API_KEY here is an opaque OpenShell placeholder resolved only by the supervisor at egress.
set -u
export HOME=/sandbox PATH=/opt/nc182/node/bin:/opt/nc182/openclaw/node_modules/.bin:/usr/local/bin:$PATH
cd /sandbox
[ -f /sandbox/.gwtoken ] || { head -c 18 /dev/urandom | od -An -tx1 | tr -d ' \n' > /sandbox/.gwtoken; chmod 600 /sandbox/.gwtoken; }
export DEFENSECLAW_GATEWAY_TOKEN="$(cat /sandbox/.gwtoken)" DEFENSECLAW_LLM_KEY="$ANTHROPIC_API_KEY"
[ -f /sandbox/.defenseclaw/audit.db ] || defenseclaw init --non-interactive --yes --skip-install >/dev/null 2>&1
if [ ! -f /sandbox/.openclaw/openclaw.json ]; then
  openclaw onboard --non-interactive --accept-risk --auth-choice apiKey --anthropic-api-key "$ANTHROPIC_API_KEY" --flow manual \
    --gateway-auth token --gateway-token "ocgw-$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')" --gateway-bind loopback --gateway-port 18789 \
    --skip-channels --skip-skills --skip-health --skip-daemon --skip-search --skip-ui >/dev/null 2>&1
fi
defenseclaw setup guardrail --connector openclaw --mode action --non-interactive >/dev/null 2>&1
cp /sandbox/guard-config.yaml /sandbox/.defenseclaw/config.yaml
openclaw models set anthropic/claude-sonnet-4-6 >/dev/null 2>&1
openclaw config set models.providers.anthropic '{"api":"anthropic-messages","baseUrl":"https://api.anthropic.com","models":[{"id":"claude-sonnet-4-6","name":"claude-sonnet-4-6"}]}' --strict-json >/dev/null 2>&1
defenseclaw-gateway stop >/dev/null 2>&1; sleep 2
defenseclaw-gateway start >/dev/null 2>&1; sleep 8
defenseclaw-gateway status 2>&1 | grep -E "Sidecar|guardrail" | head -3
echo guard-up-done
