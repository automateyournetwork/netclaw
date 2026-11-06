#!/usr/bin/env python3
"""Render isolated ordinary Border units for review; never install or start them."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re


def validate(config):
    if (not isinstance(config, dict) or set(config) != {'schemaVersion', 'role', 'expires_at'}
            or type(config['schemaVersion']) is not int or config['schemaVersion'] != 1
            or config['role'] not in ('a', 'b')):
        raise ValueError('exact_r06_host_configuration_required')
    expiry = config['expires_at']
    if not isinstance(expiry, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', expiry):
        raise ValueError('expiry_invalid')
    dt.datetime.strptime(expiry, '%Y-%m-%dT%H:%M:%SZ')
    return config


def sandbox(user, home, memory):
    return f'''User={user}
Group={user}
UMask=0077
Environment=HOME={home}
Environment=PATH=/opt/netclaw-r06/bin:/opt/netclaw-r06/venv/bin:/usr/bin:/bin
Environment=LANG=C.UTF-8
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=PYTHONNOUSERSITE=1
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
ProtectClock=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
LockPersonality=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
CapabilityBoundingSet=
AmbientCapabilities=
TasksMax=192
LimitNOFILE=2048
MemoryMax={memory}
CPUQuota=80%
TimeoutStartSec=120
TimeoutStopSec=30
Restart=no
StandardOutput=null
StandardError=journal
IPAddressDeny=169.254.0.0/16
IPAddressDeny=fd20:ce::254/128
IPAddressDeny=fe80::/10
BindReadOnlyPaths=/etc/netclaw-r06/resolv.conf:/etc/resolv.conf
'''


def render(config):
    c = validate(config)
    source = '/opt/netclaw-r06/source'
    signer = '/var/lib/netclaw-r06-signer'
    gateway = '/var/lib/netclaw-r06-gateway'
    edge = '/var/lib/netclaw-r06-edge'
    base = source + '/labs/cloud/gcp/r06'
    guard_program = f'/usr/bin/python3 -I -S -B {base}/host_guard.py'
    guard = f'{guard_program} --config /etc/netclaw-r06/network.json --state-dir /var/lib/netclaw-r06-network'
    files = {}
    # HUD model/settings/history calls use the selected native CLI as well as
    # the gateway's HTTP endpoint. Keep this launcher pinned to these binaries.
    files['openclaw'] = '#!/bin/sh\nexec /opt/netclaw-r06/bin/node /opt/netclaw-r06/openclaw/openclaw.mjs "$@"\n'
    order = '''Requires=netclaw-r06-guard.service netclaw-r06-expiry.timer
BindsTo=netclaw-r06-guard.service
After=network-online.target netclaw-r06-guard.service
'''
    def service(name, description, user, home, memory, command, extra='', dependencies=''):
        files[name] = f'''[Unit]
Description=R06 {description}
{order}{dependencies}
[Service]
Type=simple
{sandbox(user, home, memory)}{extra}
ExecStart={command}

[Install]
WantedBy=multi-user.target
'''
    service('netclaw-r06-federation.service', 'ordinary full Border (strict eN2N)',
            'netclaw-r06-signer', signer, '512M',
            f'/opt/netclaw-r06/venv/bin/python -u {source}/mcp-servers/protocol-mcp/bgp-daemon-v2.py',
            f'WorkingDirectory={source}\nEnvironmentFile=/etc/netclaw-r06/federation.env\nReadWritePaths={signer}\nInaccessiblePaths={gateway} {edge}\n')
    service('netclaw-r06-gateway.service', 'native operator and external agent profiles',
            'netclaw-r06-gateway', gateway, '1536M',
            '/opt/netclaw-r06/bin/node /opt/netclaw-r06/openclaw/openclaw.mjs gateway run',
            f'WorkingDirectory={gateway}/operator\nEnvironmentFile=/etc/netclaw-r06/gateway.env\n'
            f'EnvironmentFile={gateway}/netclaw-federation/provider.env\nReadWritePaths={gateway}\n'
            f'InaccessiblePaths={signer} {edge}\nEnvironment=NODE_OPTIONS=--max-old-space-size=1024\n',
            'Requires=netclaw-r06-secret.service\nAfter=netclaw-r06-secret.service\n')
    service('netclaw-r06-workspace.service', 'ordinary conversation backend',
            'netclaw-r06-gateway', gateway, '1024M',
            f'/opt/netclaw-r06/bin/node {source}/ui/netclaw-visual/server.js',
            f'WorkingDirectory={source}/ui/netclaw-visual\nEnvironmentFile=/etc/netclaw-r06/workspace.env\n'
            f'ReadWritePaths={gateway}\nInaccessiblePaths={signer} {edge}\nIPAddressDeny=any\nIPAddressAllow=localhost\n'
            'Environment=NODE_OPTIONS=--max-old-space-size=256\n'
            'Environment=NETCLAW_GATEWAY_CATALOG_TIMEOUT_MS=60000\n'
            'Environment=NETCLAW_GATEWAY_HISTORY_TIMEOUT_MS=60000\n'
            'Environment=NETCLAW_GATEWAY_SETTINGS_TIMEOUT_MS=120000\n')
    service('netclaw-r06-hud.service', 'ordinary cloud workspace boundary',
            'netclaw-r06-signer', signer, '256M',
            f'/opt/netclaw-r06/bin/node {source}/ui/netclaw-visual/protected-server.mjs --config /etc/netclaw-r06/hud.json',
            f'InaccessiblePaths={gateway} {edge}\nIPAddressDeny=any\nIPAddressAllow=localhost\n')
    service('netclaw-r06-caddy.service', 'HTTPS edge', 'netclaw-r06-edge', edge, '256M',
            '/opt/netclaw-r06/bin/caddy run --config /etc/netclaw-r06/Caddyfile --adapter caddyfile',
            f'ReadWritePaths={edge}\nInaccessiblePaths={signer} {gateway}\n')
    files['netclaw-r06-caddy.service'] = files['netclaw-r06-caddy.service'].replace(
        'CapabilityBoundingSet=\nAmbientCapabilities=\n',
        'CapabilityBoundingSet=CAP_NET_BIND_SERVICE\nAmbientCapabilities=CAP_NET_BIND_SERVICE\n')
    service('netclaw-r06-secret.service', 'exact-version provider-only projection',
            'netclaw-r06-gateway', gateway, '128M',
            f'/usr/bin/python3 -I -S -B {base}/project_secret.py --config {gateway}/secret-projection.json',
            f'ReadWritePaths={gateway}/netclaw-federation\nInaccessiblePaths={signer} {edge}\n')
    # Only this bounded projection process can fetch its own SA's exact secret.
    # The long-running applications retain inherited metadata denial.
    files['netclaw-r06-secret.service'] = files['netclaw-r06-secret.service'].replace(
        'Type=simple', 'Type=oneshot\nRemainAfterExit=yes').replace(
        'IPAddressDeny=169.254.0.0/16\nIPAddressDeny=fd20:ce::254/128\nIPAddressDeny=fe80::/10\n', '')
    for name, action, dependencies in (
            ('baseline', f'{guard_program} baseline', 'DefaultDependencies=no\nAfter=local-fs.target\nBefore=network-pre.target\nWants=network-pre.target\n'),
            ('guard', f'{guard} activate', 'Requires=netclaw-r06-baseline.service\nBindsTo=netclaw-r06-baseline.service\nAfter=network-online.target netclaw-r06-baseline.service\n'),
            ('expiry', f'{guard_program} close', '')):
        files[f'netclaw-r06-{name}.service'] = f'''[Unit]
Description=R06 {name} network boundary
{dependencies}
[Service]
Type=oneshot
RemainAfterExit=yes
User=root
UMask=0077
RuntimeDirectory=netclaw-r06-guard
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
ExecStart={action}
ExecStop={guard_program} close
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/run/netclaw-r06-guard /var/lib/netclaw-r06-network
CapabilityBoundingSet=CAP_NET_ADMIN
PrivateTmp=yes
TimeoutStartSec=30
TimeoutStopSec=15
Restart=no
StandardOutput=null
StandardError=journal
'''
    files['netclaw-r06-expiry.timer'] = f'''[Unit]
Description=R06 fixed network expiry
[Timer]
OnCalendar={c['expires_at'].replace('T', ' ').replace('Z', ' UTC')}
AccuracySec=1s
RandomizedDelaySec=0
Persistent=true
Unit=netclaw-r06-expiry.service
[Install]
WantedBy=timers.target
'''
    files['networkd-r06-guard.conf'] = '[Unit]\nRequires=netclaw-r06-baseline.service\nBindsTo=netclaw-r06-baseline.service\nAfter=netclaw-r06-baseline.service\n'
    files['resolv.conf'] = 'nameserver 8.8.8.8\noptions attempts:1 timeout:2\n'
    files['journald-r06.conf'] = '[Journal]\nStorage=volatile\nRuntimeMaxUse=32M\nRateLimitIntervalSec=30s\nRateLimitBurst=1000\n'
    host = f'r06-{c["role"]}-gcp-montreal.lobsternet.automateyournetwork.com'
    files['Caddyfile'] = '''{
    admin off
    persist_config off
    auto_https disable_redirects
    default_bind ADDRESS
    servers {
        protocols h1 h2
        strict_sni_host on
        max_header_size 16KiB
        timeouts {
            read_header 10s
            read_body 30s
            write 330s
            idle 5s
        }
    }
}
http://HOSTNAME {
    respond 404
}
https://HOSTNAME {
    tls {
        issuer acme {
            dir https://acme-v02.api.letsencrypt.org/directory
            disable_tlsalpn_challenge
        }
    }
    @websocket header Upgrade websocket
    respond @websocket 403
    request_body {
        max_size 72KiB
    }
    reverse_proxy 127.0.0.1:13003 {
        header_up -Forwarded
        header_up -X-Forwarded-*
        header_up -X-Real-IP
        header_up -X-Goog-*
        header_up -X-Remote-User
        header_up -X-Auth-Request-*
        transport http {
            dial_timeout 5s
            response_header_timeout 325s
        }
    }
}
'''.replace('HOSTNAME', host).replace('ADDRESS', '10.177.0.2' if c['role'] == 'a' else '10.177.1.2')
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    files = render(json.loads(Path(args.config).read_text()))
    output = Path(args.output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, content in files.items():
        path = output / name
        path.write_text(content)
        path.chmod(0o600)


if __name__ == '__main__':
    main()
