#!/bin/bash
# R09A (spec 183): (re)create the `netclaw-node` sandbox on a Border VM and start it. Run ON the VM (ssh), not locally.
#   bash ha-r09a-node-recreate.sh <node-internal-ip> <policy-sha256>
# Needs: ~/stage/nc182 (identity bundle + bin/r09a_node_run.py), /tmp/policy.yaml (labs/ha/r09a_policy.py output),
#        provider `nc183-anthropic` already created, image nc183-node:4 built.
# Then: upload /sandbox/guard-config.yaml and run labs/ha/r09a_guard_up.sh through the runner hook (see RESUME.md).
export PATH=$HOME/.local/bin:$PATH
# Findings baked in: `forward start -d` output must go to a FILE (a pipe hangs); the host 443 redirect is scoped to the node IP.
NODE_IP=$1; POLSHA=$2
for p in 7443 7444 8443; do timeout 20 openshell forward stop $p netclaw-node >/dev/null 2>&1; done
for pid in $(ps aux | grep '[o]penshell ssh-proxy' | awk '{print $2}'); do kill $pid 2>/dev/null; done
openshell sandbox delete netclaw-node 2>&1 | tail -1
for i in $(seq 1 30); do openshell sandbox list 2>&1 | grep -q netclaw-node || break; sleep 2; done
# public HTTPS: host 443 -> forwarded ingress 8443, scoped to this node address only (idempotent)
sudo iptables -t nat -C PREROUTING -d "$NODE_IP"/32 -p tcp --dport 443 -j REDIRECT --to-ports 8443 2>/dev/null || sudo iptables -t nat -A PREROUTING -d "$NODE_IP"/32 -p tcp --dport 443 -j REDIRECT --to-ports 8443
echo "$POLSHA" > ~/stage/nc182/policy.sha256
setsid nohup openshell sandbox create --name netclaw-node --from nc183-node:4 --policy /tmp/policy.yaml --provider nc183-anthropic --no-tty -- bash -c 'while [ ! -f /sandbox/nc182/START ]; do sleep 1; done; exec /opt/nc182/venv/bin/python -B /sandbox/nc182/bin/r09a_node_run.py' > /tmp/create.log 2>&1 < /dev/null &
for i in $(seq 1 40); do openshell sandbox list 2>&1 | grep -q Ready && break; sleep 2; done
openshell sandbox list
timeout 120 openshell sandbox upload netclaw-node ~/stage/nc182 /sandbox 2>&1 | tail -1
for p in $NODE_IP:7443 0.0.0.0:7444 0.0.0.0:8443; do timeout 30 openshell forward start -d $p netclaw-node > /tmp/fwd.log 2>&1 < /dev/null; done
timeout 30 openshell sandbox exec -n netclaw-node -- touch /sandbox/nc182/START
openshell forward list
echo DONE
