#!/usr/bin/env bash
# Fresh Spec199 AWS host only. No provider credential or runtime identity here.
set -euo pipefail
umask 077
export DEBIAN_FRONTEND=noninteractive
: "${NC199_INSTANCE_ID:?exact owned instance ID}"
: "${NC199_RUN_ID:?frozen run ID}"
[[ "$NC199_RUN_ID" =~ ^nc199-[a-f0-9]{12}$ ]]
[[ "$NC199_INSTANCE_ID" =~ ^i-[a-f0-9]{17}$ ]]
test "$(id -u)" = 0
test "$(uname -m)" = x86_64
. /etc/os-release
test "$ID" = ubuntu && test "$VERSION_ID" = 24.04
token=$(curl -fsS --max-time 5 -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')
actual=$(curl -fsS --max-time 5 -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/meta-data/instance-id)
unset token
test "$actual" = "$NC199_INSTANCE_ID"
systemctl is-active --quiet netclaw-199-deadline.timer
test ! -e /var/lib/netclaw199-owner
printf '%s\n%s\n' "$NC199_RUN_ID" "$NC199_INSTANCE_ID" >/var/lib/netclaw199-owner
apt-get update -qq
apt-get install -y -qq ca-certificates curl iptables jq tar xz-utils python3 chrony >/var/log/nc199-apt.log
abi=$(python3 - <<'PY'
import ctypes
print(ctypes.CDLL(None,use_errno=True).syscall(444,None,0,1))
PY
)
test "$abi" -ge 3
printf 'kernel=%s landlock_abi=%s\n' "$(uname -r)" "$abi"
# Use AWS local time service rather than a public NTP dependency.
printf 'server 169.254.169.123 prefer iburst minpoll 4 maxpoll 4\n' >/etc/chrony/sources.d/netclaw199.sources
systemctl restart chrony
curl -fsSL --proto '=https' --tlsv1.2 https://get.docker.com -o /var/tmp/nc199-docker-install.sh
sha256sum /var/tmp/nc199-docker-install.sh
sh /var/tmp/nc199-docker-install.sh >/var/log/nc199-docker-install.log 2>&1
test "$(docker --version | sed -E 's/Docker version ([0-9]+).*/\1/')" -ge 28
systemctl enable --now docker
usermod -aG docker ubuntu
loginctl enable-linger ubuntu
systemctl restart "user@$(id -u ubuntu).service"

# Release asset and hash observed from the official v0.1.7 release. No latest fallback.
curl -fsSL --proto '=https' --tlsv1.2 \
  https://github.com/ai-openshell/openshell/releases/download/v0.1.7/openshell_0.1.7-1_amd64.deb \
  -o /var/tmp/nc199-openshell.deb
printf '%s\n' 'c0bbac200db9a4cf691b0bc6dd23e1cf03c0e8156dd71f368ae6bf8e48405fe6  /var/tmp/nc199-openshell.deb' | sha256sum -c -
apt-get install -y -qq /var/tmp/nc199-openshell.deb >/var/log/nc199-openshell-install.log 2>&1
test "$(dpkg-query -W -f='${Version}' openshell | cut -d- -f1)" = 0.1.7
install -d -m 0700 -o ubuntu -g ubuntu /home/ubuntu/.config /home/ubuntu/.config/openshell
printf 'OPENSHELL_COMPUTE_DRIVER=docker\n' >/home/ubuntu/.config/openshell/gateway.env
chown ubuntu:ubuntu /home/ubuntu/.config/openshell/gateway.env
as_operator() { sudo -u ubuntu -H env XDG_RUNTIME_DIR="/run/user/$(id -u ubuntu)" "$@"; }
as_operator systemctl --user daemon-reload
as_operator systemctl --user enable --now openshell-gateway
as_operator openshell doctor check
as_operator openshell gateway add https://127.0.0.1:17670 --local --name node
as_operator openshell gateway select node

cat >/etc/systemd/system/netclaw-199-metadata-block.service <<'UNIT'
[Unit]
Description=Spec199 block AWS metadata from containers
After=docker.service
Requires=docker.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'iptables -N DOCKER-USER 2>/dev/null || true; iptables -C DOCKER-USER -d 169.254.169.254 -j REJECT 2>/dev/null || iptables -I DOCKER-USER 1 -d 169.254.169.254 -j REJECT'
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now netclaw-199-metadata-block.service
iptables -C DOCKER-USER -d 169.254.169.254 -j REJECT
# The frozen launch request disables the IPv6 metadata endpoint; no IPv6 address is assigned.
docker --version
as_operator openshell --version
as_operator systemctl --user is-active openshell-gateway
systemctl list-timers netclaw-199-deadline.timer --no-pager
chronyc tracking
