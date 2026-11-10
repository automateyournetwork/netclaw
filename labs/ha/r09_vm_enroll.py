#!/usr/bin/env python3
"""R09: one-shot execution-member enrollment on a Border VM (run as nc182, Borders stopped).

  sudo -u nc182 /opt/nc182/venv/bin/python -B r09_vm_enroll.py /tmp/member.json

member.json is {"binding": {...}, "certificate": "<pem>"} from `r09_member.py identity` (public material).
Uses the production Authority CAS and OperationLedger.enroll_member as Border 0. enroll_member needs the
leader lease, and campaign refuses while a leader exists, so all Border services must be stopped and the
previous lease expired (> leader_lease_s). The provisioning lease is not renewed: it expires on its own.
No execution is dispatched. Single attempt: a failure is inspected, never retried as a new change.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, '/opt/nc182/source/mcp-servers/protocol-mcp')
from bgp.federation import protected_contract as c  # noqa: E402
from bgp.federation.ha.authority import Authority  # noqa: E402
from bgp.federation.ha.config import verify_manifest  # noqa: E402
from bgp.federation.ha.operations import OperationLedger  # noqa: E402
from bgp.federation.ha.store import EtcdStore  # noqa: E402

S = Path('/var/lib/nc182')
member = json.loads(Path(sys.argv[1]).read_text())
owned = json.loads((S / 'etcd-owned.json').read_text())
anchor = (S / 'identity/root.crt').read_text()
manifest = verify_manifest((S / 'identity/manifest.json').read_bytes(), anchor, expected_key_id=c.key_id(anchor))
password = (S / 'home/netclaw-federation/etcd-password').read_text().strip()
store = EtcdStore(owned['clients'], prefix=owned['prefix'], ca=S / 'etcd-client/client-ca.crt',
                  certificate=S / 'etcd-client/border.crt', private_key=S / 'etcd-client/border.key',
                  username='border0', password=password)
try:
    authority = Authority(store, manifest, manifest.nodes[0]['node_id'])
    if not authority.campaign():
        raise SystemExit('authority_unavailable: a live lease still exists; wait for expiry with all Borders stopped')
    OperationLedger(authority).enroll_member(member['binding'], member['certificate'])
    print(json.dumps({'enrolled': member['binding']['member_id'], 'provisioning_epoch': authority.epoch,
                      'lease_renewed': False, 'execution_dispatches': 0, 'at': time.time()}))
finally:
    store.close()
