#!/bin/bash
# R10 (spec 198): (re)create the `netclaw-node` sandbox for the FULL-STACK runner. Run ON the VM (ssh), not locally.
#   bash ha-r10-node-recreate.sh <node-internal-ip> <policy-sha256> [image]
# Differences from ha-r09a-node-recreate.sh: image nc183-node:r10 and the runner is r10_node_run.py (frozen explicit
# full-stack runner: protected role, guarded gateway, workspace backend, HTTPS ingress; no uploaded-script hook).
# Needs ~/stage/nc182 (labs/ha/r10_payload.py output), /tmp/policy.yaml, provider nc183-anthropic.
export PATH=$HOME/.local/bin:$PATH
NODE_IP=$1; POLSHA=$2; IMAGE=${3:-nc183-node:r10}
for p in 7443 7444 7445 8443; do timeout 20 openshell forward stop $p netclaw-node >/dev/null 2>&1; done
for pid in $(ps aux | grep '[o]penshell ssh-proxy' | awk '{print $2}'); do kill $pid 2>/dev/null; done
openshell sandbox delete netclaw-node 2>&1 | tail -1
for i in $(seq 1 30); do openshell sandbox list 2>&1 | grep -q netclaw-node || break; sleep 2; done
sudo iptables -t nat -C PREROUTING -d "$NODE_IP"/32 -p tcp --dport 443 -j REDIRECT --to-ports 8443 2>/dev/null || sudo iptables -t nat -A PREROUTING -d "$NODE_IP"/32 -p tcp --dport 443 -j REDIRECT --to-ports 8443
echo "$POLSHA" > ~/stage/nc182/policy.sha256
setsid nohup openshell sandbox create --name netclaw-node --from "$IMAGE" --policy /tmp/policy.yaml --provider nc183-anthropic --no-tty -- bash -c 'while [ ! -f /sandbox/nc182/START ]; do sleep 1; done; exec /opt/nc182/venv/bin/python -B /sandbox/nc182/bin/r10_node_run.py' > /tmp/create.log 2>&1 < /dev/null &
for i in $(seq 1 60); do openshell sandbox list 2>&1 | grep -q Ready && break; sleep 2; done
openshell sandbox list
timeout 120 openshell sandbox upload netclaw-node ~/stage/nc182 /sandbox 2>&1 | tail -1
for p in $NODE_IP:7443 0.0.0.0:7444 0.0.0.0:7445 0.0.0.0:8443; do timeout 30 openshell forward start -d $p netclaw-node > /tmp/fwd.log 2>&1 < /dev/null; done
timeout 30 openshell sandbox exec -n netclaw-node -- touch /sandbox/nc182/START
openshell forward list
echo DONE
