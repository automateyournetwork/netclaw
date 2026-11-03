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
    fields = {'schemaVersion', 'role', 'hostname', 'source', 'home', 'python', 'node', 'caddy', 'role_contract',
              'hud_config', 'secret_config', 'network_config', 'expires_at'}
    need(isinstance(config, dict) and set(config) == fields, 'host_fields_invalid')
    need(type(config['schemaVersion']) is int and config['schemaVersion'] == 1, 'host_schema_invalid')
    need(config['role'] in ('border', 'member'), 'role_invalid')
    need(config['hostname'] == 'r04-gcp-montreal.lobsternet.automateyournetwork.com', 'reviewed_hostname_required')
    optional = {'node', 'caddy', 'hud_config'} if config['role'] == 'member' else set()
    need(all(config[name] is None for name in optional), 'member_has_no_hud')
    for name in fields - {'schemaVersion', 'role', 'hostname', 'expires_at'} - optional:
        value = config[name]
        need(isinstance(value, str) and re.fullmatch(r'/[A-Za-z0-9_./-]+', value) and str(Path(value)) == value and '..' not in Path(value).parts, 'literal_absolute_path_required')
        need(value.startswith('/opt/netclaw-r04/') if name in {'source', 'python', 'node', 'caddy'} else value.startswith('/var/lib/netclaw-r04/'), 'isolated_root_required')
    need(config['home'] == '/var/lib/netclaw-r04/claw', 'fixed_home_required')
    need(config['network_config'] == '/var/lib/netclaw-r04/network/config.json', 'root_network_config_required')
    configs = [config[name] for name in ('role_contract', 'hud_config', 'secret_config', 'network_config') if config[name] is not None]
    need(len(set(configs)) == len(configs), 'separate_config_paths_required')
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
SyslogIdentifier=netclaw-r04
'''


def render(config):
    c = validate(config)
    base = c['source'] + '/labs/cloud/gcp/r04'
    guard_program = f'/usr/bin/python3 -I -S -B {base}/host_guard.py'
    guard = f'{guard_program} --config {c["network_config"]} --state-dir /var/lib/netclaw-r04/network'
    order = '''Requires=netclaw-r04-guard.service netclaw-r04-expiry.timer
BindsTo=netclaw-r04-guard.service
After=network-online.target netclaw-r04-guard.service
'''
    files = {}
    files['netclaw-r04-baseline.service'] = f'''[Unit]
Description=R04 configuration-free closed output before network setup
DefaultDependencies=no
After=local-fs.target
Before=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
UMask=0077
RuntimeDirectory=netclaw-r04-guard
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
ExecStart={guard_program} baseline
ExecStop={guard_program} close
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/run/netclaw-r04-guard
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
    files['netclaw-r04-guard.service'] = f'''[Unit]
Description=R04 one-use finite egress allowance (restart closes output)
Requires=netclaw-r04-baseline.service
BindsTo=netclaw-r04-baseline.service
Wants=network-online.target
After=network-online.target netclaw-r04-baseline.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
UMask=0077
RuntimeDirectory=netclaw-r04-guard
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
ExecStart={guard} activate
ExecStop={guard_program} close
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/netclaw-r04/network /run/netclaw-r04-guard
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
    files['netclaw-r04-secret.service'] = f'''[Unit]
Description=R04 exact-version role-scoped secret projection
{order}
Before=netclaw-r04-federation.service netclaw-r04-hud.service

[Service]
Type=oneshot
RemainAfterExit=yes
{sandbox('netclaw-r04', c['home'], memory='128M')}
ExecStart=/usr/bin/env -i HOME={c['home']} PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S -B {base}/project_secret.py --config {c['secret_config']}
ReadWritePaths={c['home']}/netclaw-federation
'''
    files['netclaw-r04-federation.service'] = f'''[Unit]
Description=R04 strict control-only Border federation
{order}
Requires=netclaw-r04-secret.service
After=netclaw-r04-secret.service

[Service]
Type=simple
{sandbox('netclaw-r04', c['home'])}
ExecStart=/usr/bin/env -i HOME={c['home']} PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S -B {c['source']}/scripts/protected-role.py --contract {c['role_contract']} run
ReadWritePaths={c['home']}/n2n {c['home']}/netclaw-federation
IPAddressDeny=169.254.0.0/16\nIPAddressDeny=fd20:ce::254/128\nIPAddressDeny=fe80::/10

[Install]
WantedBy=multi-user.target
'''
    files['netclaw-r04-hud.service'] = f'''[Unit]
Description=R04 protected production HUD
{order}
Requires=netclaw-r04-federation.service
After=netclaw-r04-federation.service

[Service]
Type=simple
{sandbox('netclaw-r04', c['home'])}
ExecStart=/usr/bin/env -i HOME={c['home']} PATH=/usr/bin:/bin LANG=C.UTF-8 {c['node']} {c['source']}/ui/netclaw-visual/protected-server.mjs --config {c['hud_config']}
IPAddressDeny=any
IPAddressAllow=localhost

[Install]
WantedBy=multi-user.target
'''
    # Only the HTTPS edge gets the narrow bind-low-ports capability. It has a
    # separate UID/home and no access to the Border's private installation.
    edge_sandbox = sandbox('netclaw-r04-edge', '/var/lib/netclaw-r04-edge', memory='256M').replace(
        'CapabilityBoundingSet=\nAmbientCapabilities=\n',
        'CapabilityBoundingSet=CAP_NET_BIND_SERVICE\nAmbientCapabilities=CAP_NET_BIND_SERVICE\n')
    files['netclaw-r04-caddy.service'] = f'''[Unit]
Description=R04 named HTTPS edge (separate UID)
{order}
Requires=netclaw-r04-hud.service
After=netclaw-r04-hud.service

[Service]
Type=simple
{edge_sandbox}
ExecStart=/usr/bin/env -i HOME=/var/lib/netclaw-r04-edge PATH=/usr/bin:/bin LANG=C.UTF-8 {c['caddy']} run --config /etc/netclaw-r04/Caddyfile --adapter caddyfile
ReadWritePaths=/var/lib/netclaw-r04-edge
InaccessiblePaths=/var/lib/netclaw-r04
IPAddressDeny=169.254.0.0/16\nIPAddressDeny=fd20:ce::254/128\nIPAddressDeny=fe80::/10

[Install]
WantedBy=multi-user.target
'''
    files['netclaw-r04-expiry.service'] = f'''[Unit]
Description=Close R04 host output at the fixed qualification expiry

[Service]
Type=oneshot
User=root
UMask=0077
RuntimeDirectory=netclaw-r04-guard
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
ExecStart={guard_program} close
NoNewPrivileges=yes
CapabilityBoundingSet=CAP_NET_ADMIN
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/run/netclaw-r04-guard
'''
    calendar = c['expires_at'].replace('T', ' ').replace('Z', ' UTC')
    files['netclaw-r04-expiry.timer'] = f'''[Unit]
Description=R04 absolute expiry (does not replace GCE STOP/teardown)

[Timer]
OnCalendar={calendar}
AccuracySec=1s
RandomizedDelaySec=0
Persistent=true
Unit=netclaw-r04-expiry.service

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
    default_bind 10.173.0.2
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
    files['journald-r04.conf'] = '[Journal]\nStorage=volatile\nRuntimeMaxUse=32M\nRateLimitIntervalSec=30s\nRateLimitBurst=1000\n'
    # Install as a drop-in ONLY on the verified dedicated Ubuntu networkd host.
    # This is a required boot dependency, unlike network-pre.target's soft Wants.
    files['networkd-r04-guard.conf'] = '[Unit]\nRequires=netclaw-r04-baseline.service\nBindsTo=netclaw-r04-baseline.service\nAfter=netclaw-r04-baseline.service\n'
    if c['role'] == 'member':
        for name in ('netclaw-r04-hud.service', 'netclaw-r04-caddy.service', 'Caddyfile'):
            files.pop(name)
        unit = files['netclaw-r04-federation.service']
        unit = unit.replace('strict control-only Border federation', 'strict outbound execution member')
        unit = unit.replace('Requires=netclaw-r04-secret.service', 'Requires=netclaw-r04-secret.service docker.service')
        unit = unit.replace('After=netclaw-r04-secret.service', 'After=netclaw-r04-secret.service docker.service')
        unit = unit.replace('MemoryMax=512M', 'MemoryMax=1G')
        unit = unit.replace('[Service]\n', '[Service]\nBindReadOnlyPaths=/etc/netclaw-r04/resolv.conf:/etc/resolv.conf\n')
        unit = unit.replace('Group=netclaw-r04', 'Group=netclaw-r04\nSupplementaryGroups=docker')
        unit = unit.replace(f'ReadWritePaths={c["home"]}/n2n {c["home"]}/netclaw-federation', f'ReadWritePaths={c["home"]}/n2n {c["home"]}/netclaw-federation {c["home"]}/execution')
        files['netclaw-r04-federation.service'] = unit
        files['docker-r04-guard.conf'] = '[Unit]\nRequires=netclaw-r04-guard.service\nBindsTo=netclaw-r04-guard.service\nAfter=netclaw-r04-guard.service\n'
        files['docker-daemon.json'] = json.dumps({'dns': ['8.8.8.8'], 'iptables': True, 'ip6tables': True, 'live-restore': False, 'userland-proxy': False, 'log-driver': 'local', 'log-opts': {'max-size': '10m', 'max-file': '2'}}, sort_keys=True) + '\n'
        files['resolv.conf'] = 'nameserver 8.8.8.8\noptions attempts:1 timeout:2\n'
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
