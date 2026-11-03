#!/usr/bin/env python3
"""Render reviewable host files; never installs units, starts services or fetches secrets."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re


class Refused(ValueError):
    pass


def need(value, code):
    if not value:
        raise Refused(code)


def validate(config):
    fields = {'schemaVersion', 'hostname', 'source', 'home', 'python', 'node', 'caddy', 'role_contract',
              'hud_config', 'secret_config', 'network_config', 'expires_at'}
    need(isinstance(config, dict) and set(config) == fields, 'host_fields_invalid')
    need(type(config['schemaVersion']) is int and config['schemaVersion'] == 1, 'host_schema_invalid')
    need(config['hostname'] == 'r03-gcp-montreal.lobsternet.automateyournetwork.com', 'reviewed_hostname_required')
    for name in fields - {'schemaVersion', 'hostname', 'expires_at'}:
        value = config[name]
        need(isinstance(value, str) and re.fullmatch(r'/[A-Za-z0-9_./-]+', value) and str(Path(value)) == value and '..' not in Path(value).parts, 'literal_absolute_path_required')
        need(value.startswith('/opt/netclaw-r03/') if name in {'source', 'python', 'node', 'caddy'} else value.startswith('/var/lib/netclaw-r03/'), 'isolated_root_required')
    need(config['home'] == '/var/lib/netclaw-r03/claw', 'fixed_home_required')
    need(config['network_config'] == '/var/lib/netclaw-r03/network/config.json', 'root_network_config_required')
    need(len({config[name] for name in ('role_contract', 'hud_config', 'secret_config', 'network_config')}) == 4, 'separate_config_paths_required')
    need(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', config['expires_at']), 'expiry_invalid')
    dt.datetime.strptime(config['expires_at'], '%Y-%m-%dT%H:%M:%SZ')
    return config


def sandbox(user, home, *, memory='512M'):
    return f'''User={user}
Group={user}
UMask=0077
Environment=HOME={home}
Environment=PATH=/usr/bin:/bin
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
TasksMax=128
LimitNOFILE=1024
MemoryMax={memory}
CPUQuota=50%
TimeoutStartSec=90
TimeoutStopSec=30
Restart=no
StandardOutput=null
StandardError=journal
SyslogIdentifier=netclaw-r03
'''


def render(config):
    c = validate(config)
    base = c['source'] + '/labs/cloud/gcp/r03'
    guard_program = f'/usr/bin/python3 -I -S -B {base}/host_guard.py'
    guard = f'{guard_program} --config {c["network_config"]} --state-dir /var/lib/netclaw-r03/network'
    order = '''Requires=netclaw-r03-guard.service netclaw-r03-expiry.timer
BindsTo=netclaw-r03-guard.service
After=network-online.target netclaw-r03-guard.service
'''
    files = {}
    files['netclaw-r03-baseline.service'] = f'''[Unit]
Description=R03 configuration-free closed output before network setup
DefaultDependencies=no
After=local-fs.target
Before=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
UMask=0077
RuntimeDirectory=netclaw-r03-guard
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
ExecStart={guard_program} baseline
ExecStop={guard_program} close
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/run/netclaw-r03-guard
NoNewPrivileges=yes
CapabilityBoundingSet=CAP_NET_ADMIN
PrivateTmp=yes
TimeoutStartSec=30
TimeoutStopSec=15
Restart=no
StandardOutput=null
StandardError=journal

[Install]
WantedBy=network-pre.target
'''
    files['netclaw-r03-guard.service'] = f'''[Unit]
Description=R03 one-use finite egress allowance (restart closes output)
Requires=netclaw-r03-baseline.service
BindsTo=netclaw-r03-baseline.service
Wants=network-online.target
After=network-online.target netclaw-r03-baseline.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
UMask=0077
RuntimeDirectory=netclaw-r03-guard
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
ExecStart={guard} activate
ExecStop={guard_program} close
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/netclaw-r03/network /run/netclaw-r03-guard
NoNewPrivileges=yes
CapabilityBoundingSet=CAP_NET_ADMIN
PrivateTmp=yes
TimeoutStartSec=30
TimeoutStopSec=15
Restart=no
StandardOutput=null
StandardError=journal

[Install]
WantedBy=multi-user.target
'''
    files['netclaw-r03-secret.service'] = f'''[Unit]
Description=R03 exact-version cloud-only operator secret projection
{order}
Before=netclaw-r03-federation.service netclaw-r03-hud.service

[Service]
Type=oneshot
RemainAfterExit=yes
{sandbox('netclaw-r03', c['home'], memory='128M')}
ExecStart=/usr/bin/env -i HOME={c['home']} PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S -B {base}/project_secret.py --config {c['secret_config']}
ReadWritePaths={c['home']}/netclaw-federation
'''
    files['netclaw-r03-federation.service'] = f'''[Unit]
Description=R03 strict control-only Border federation
{order}
Requires=netclaw-r03-secret.service
After=netclaw-r03-secret.service

[Service]
Type=simple
{sandbox('netclaw-r03', c['home'])}
ExecStart=/usr/bin/env -i HOME={c['home']} PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S -B {c['source']}/scripts/protected-role.py --contract {c['role_contract']} run
ReadWritePaths={c['home']}/n2n {c['home']}/netclaw-federation
IPAddressDeny=169.254.169.254/32

[Install]
WantedBy=multi-user.target
'''
    files['netclaw-r03-hud.service'] = f'''[Unit]
Description=R03 protected production HUD
{order}
Requires=netclaw-r03-federation.service
After=netclaw-r03-federation.service

[Service]
Type=simple
{sandbox('netclaw-r03', c['home'])}
ExecStart=/usr/bin/env -i HOME={c['home']} PATH=/usr/bin:/bin LANG=C.UTF-8 {c['node']} {c['source']}/ui/netclaw-visual/protected-server.mjs --config {c['hud_config']}
IPAddressDeny=any
IPAddressAllow=localhost

[Install]
WantedBy=multi-user.target
'''
    # Only the HTTPS edge gets the narrow bind-low-ports capability. It has a
    # separate UID/home and no access to the Border's private installation.
    edge_sandbox = sandbox('netclaw-r03-edge', '/var/lib/netclaw-r03-edge', memory='256M').replace(
        'CapabilityBoundingSet=\nAmbientCapabilities=\n',
        'CapabilityBoundingSet=CAP_NET_BIND_SERVICE\nAmbientCapabilities=CAP_NET_BIND_SERVICE\n')
    files['netclaw-r03-caddy.service'] = f'''[Unit]
Description=R03 named HTTPS edge (separate UID)
{order}
Requires=netclaw-r03-hud.service
After=netclaw-r03-hud.service

[Service]
Type=simple
{edge_sandbox}
ExecStart=/usr/bin/env -i HOME=/var/lib/netclaw-r03-edge PATH=/usr/bin:/bin LANG=C.UTF-8 {c['caddy']} run --config /etc/netclaw-r03/Caddyfile --adapter caddyfile
ReadWritePaths=/var/lib/netclaw-r03-edge
InaccessiblePaths=/var/lib/netclaw-r03
IPAddressDeny=169.254.169.254/32

[Install]
WantedBy=multi-user.target
'''
    files['netclaw-r03-expiry.service'] = f'''[Unit]
Description=Close R03 host output at the fixed qualification expiry

[Service]
Type=oneshot
User=root
UMask=0077
RuntimeDirectory=netclaw-r03-guard
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
ExecStart={guard_program} close
NoNewPrivileges=yes
CapabilityBoundingSet=CAP_NET_ADMIN
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/run/netclaw-r03-guard
'''
    calendar = c['expires_at'].replace('T', ' ').replace('Z', ' UTC')
    files['netclaw-r03-expiry.timer'] = f'''[Unit]
Description=R03 absolute expiry (does not replace GCE STOP/teardown)

[Timer]
OnCalendar={calendar}
AccuracySec=1s
RandomizedDelaySec=0
Persistent=true
Unit=netclaw-r03-expiry.service

[Install]
WantedBy=timers.target
'''
    files['Caddyfile'] = '''{
    admin off
    persist_config off
    log {
        format filter {
            request delete
            resp_headers delete
            wrap json
        }
    }
    default_bind 10.172.0.2
    auto_https disable_redirects
    servers {
        protocols h1 h2
        strict_sni_host on
        max_header_size 16KiB
        timeouts {
            read_header 10s
            read_body 30s
            write 30s
            idle 5s
        }
    }
}

http://HOSTNAME {
    redir https://HOSTNAME{uri} 308
}

https://HOSTNAME {
    tls {
        issuer acme {
            dir https://acme-v02.api.letsencrypt.org/directory
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
            response_header_timeout 30s
        }
    }
}
'''.replace('HOSTNAME', c['hostname'])
    files['journald-r03.conf'] = '[Journal]\nStorage=volatile\nRuntimeMaxUse=32M\nRateLimitIntervalSec=30s\nRateLimitBurst=1000\n'
    # Install as a drop-in ONLY on the verified dedicated Ubuntu networkd host.
    # This is a required boot dependency, unlike network-pre.target's soft Wants.
    files['networkd-r03-guard.conf'] = '[Unit]\nRequires=netclaw-r03-baseline.service\nBindsTo=netclaw-r03-baseline.service\nAfter=netclaw-r03-baseline.service\n'
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
        with path.open('x') as stream:
            stream.write(content)
        path.chmod(0o600)


if __name__ == '__main__':
    main()
