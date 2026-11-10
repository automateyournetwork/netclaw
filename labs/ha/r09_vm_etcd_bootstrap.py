#!/usr/bin/env python3
"""R09: one-shot etcd RBAC + authority bootstrap, run once on the first Border VM as nc182.

Uses the bootstrap-only admin material in /var/lib/nc182/etcd-bootstrap (deleted afterwards by the caller).
Single attempt per write: a partial bootstrap is inspected, never blindly retried (R08 rule).
"""
import base64
import json
import os
import ssl
import sys
import time
from pathlib import Path

sys.path.insert(0, '/opt/nc182/source/mcp-servers/protocol-mcp')
import httpx  # noqa: E402

S = Path(os.environ.get('NC_STATE', '/var/lib/nc182'))  # sandbox nodes set NC_STATE=/sandbox/nc182
B = S / 'etcd-bootstrap'
owned = json.loads((B / 'owned.json').read_text())
credentials = json.loads((B / 'credentials.json').read_text())
_node = json.loads((S / 'node.json').read_text())
internal = os.environ.get('NC_ETCD_HOST') or _node.get('iname') or _node['internal']  # sandbox nodes must use DNS names (OpenShell refuses IP literals)

context = ssl.create_default_context(cafile=str(B / 'client-ca.crt'))
context.minimum_version = ssl.TLSVersion.TLSv1_3
context.load_cert_chain(B / 'admin.crt', B / 'admin.key')
url = f"https://{internal}:{os.environ.get('NC_ETCD_PORT', '12379')}/v3/"


def request(client, path, value):
    response = client.post(url + path, json=value)
    if response.status_code != 200 or 'error' in response.json():
        raise SystemExit(f'etcd_bootstrap_refused:{path}:{response.status_code}:{response.text[:200]}')
    return response.json()


with httpx.Client(verify=context, timeout=5, trust_env=False, follow_redirects=False) as client:
    deadline = time.monotonic() + 120
    while True:
        try:
            request(client, 'kv/range', {'key': base64.b64encode(b'initial-read').decode(), 'serializable': False})
            break
        except (httpx.HTTPError, SystemExit):
            if time.monotonic() >= deadline:
                raise SystemExit('etcd_readiness_timeout')
            time.sleep(1)
    prefix = owned['prefix'].encode()
    end = prefix[:-1] + bytes([prefix[-1] + 1])
    request(client, 'auth/user/add', {'name': 'root', 'password': credentials['root']})
    request(client, 'auth/user/grant', {'user': 'root', 'role': 'root'})
    request(client, 'auth/role/add', {'name': 'ncfed-cluster'})
    request(client, 'auth/role/grant', {'name': 'ncfed-cluster', 'perm': {
        'permType': 'READWRITE', 'key': base64.b64encode(prefix).decode(), 'range_end': base64.b64encode(end).decode()}})
    for i in range(sum(1 for k in credentials if k.startswith('border'))):  # 2 Borders in R09A, 3 in R09
        request(client, 'auth/user/add', {'name': f'border{i}', 'password': credentials[f'border{i}']})
        request(client, 'auth/user/grant', {'user': f'border{i}', 'role': 'ncfed-cluster'})
    request(client, 'auth/enable', {})
print(json.dumps({'rbac': 'enabled', 'scope': owned['prefix']}))

# Authority bootstrap through the production implementation, as Border 0.
from bgp.federation import protected_contract as c  # noqa: E402
from bgp.federation.ha.authority import Authority  # noqa: E402
from bgp.federation.ha.config import verify_manifest  # noqa: E402
from bgp.federation.ha.store import EtcdStore  # noqa: E402

identity = S / 'identity'
anchor = (identity / 'root.crt').read_text()
manifest = verify_manifest((identity / 'manifest.json').read_bytes(), anchor, expected_key_id=c.key_id(anchor))
store = EtcdStore(owned['clients'], prefix=owned['prefix'], ca=S / 'etcd-client/client-ca.crt',
                  certificate=S / 'etcd-client/border.crt', private_key=S / 'etcd-client/border.key',
                  username='border0', password=credentials['border0'])
try:
    authority = Authority(store, manifest, manifest.nodes[0]['node_id'])
    authority.bootstrap(create=True)
    print(json.dumps({'authority': 'bootstrapped', 'node': manifest.nodes[0]['node_id']}))
finally:
    store.close()
