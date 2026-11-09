#!/usr/bin/env bash
# R09 (spec 182): per-Border network shim + etcd voter. Run as root after r09_vm_finalize.py.
#
# The Border binds the manifest's own iN2N host (the public IP), which GCP does not put on the NIC.
# Alias the public /32 on lo and DNAT the NIC-side iN2N port to it (idempotent, persisted by unit).
set -euo pipefail
S=/var/lib/nc182
public=$(jq -r .public $S/node.json); internal=$(jq -r .internal $S/node.json); idx=$(jq -r .index $S/node.json)
IN2N=7444

cat >/etc/systemd/system/nc182-net.service <<EOF
[Unit]
Description=nc182 public-IP alias and iN2N DNAT
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'ip addr show dev lo | grep -q "$public/32" || ip addr add $public/32 dev lo; iptables -t nat -C PREROUTING -d $internal -p tcp --dport $IN2N -j DNAT --to-destination $public:$IN2N 2>/dev/null || iptables -t nat -A PREROUTING -d $internal -p tcp --dport $IN2N -j DNAT --to-destination $public:$IN2N'
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload; systemctl enable --now nc182-net.service >/dev/null 2>&1

# etcd voter: host network on the internal IP, TLS1.3, client+peer cert auth, WAN-tuned timers.
cluster=$(jq -r '.peers | join(",")' $S/etcd-owned.json)
name=$(jq -r .name $S/etcd-owned.json)
hb=$(jq -r .heartbeat_ms $S/etcd-owned.json); el=$(jq -r .election_ms $S/etcd-owned.json)
install -d -m 0700 -o nc182 -g nc182 $S/etcd-data
uid=$(id -u nc182); gid=$(id -g nc182)
docker rm -f nc182-etcd >/dev/null 2>&1 || true
docker run -d --name nc182-etcd --restart unless-stopped --network host \
  --label netclaw.spec=182 --label netclaw.owner=$name \
  --user $uid:$gid --memory 1g --cap-drop ALL --security-opt no-new-privileges -e GOMEMLIMIT=768MiB \
  -v $S/etcd-voter:/pki:ro -v $S/etcd-data:/data \
  gcr.io/etcd-development/etcd:v3.6.16 /usr/local/bin/etcd --name v$idx --data-dir /data \
  --listen-client-urls https://$internal:2379,https://127.0.0.1:2379 --advertise-client-urls https://$internal:2379 \
  --listen-peer-urls https://$internal:2380 --initial-advertise-peer-urls https://$internal:2380 \
  --initial-cluster "$cluster" --initial-cluster-token $name --initial-cluster-state new \
  --cert-file /pki/server.crt --key-file /pki/server.key --trusted-ca-file /pki/client-ca.crt --client-cert-auth=true \
  --peer-cert-file /pki/peer.crt --peer-key-file /pki/peer.key --peer-trusted-ca-file /pki/peer-ca.crt --peer-client-cert-auth=true \
  --tls-min-version=TLS1.3 --heartbeat-interval $hb --election-timeout $el \
  --quota-backend-bytes 134217728 --auto-compaction-mode periodic --auto-compaction-retention 1m --log-level warn
sleep 2
docker ps --filter name=nc182-etcd --format '{{.Names}} {{.Status}}'
