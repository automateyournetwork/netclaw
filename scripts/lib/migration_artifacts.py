"""Private migration artifacts and consumer of API-issued apply capabilities.

No grant issuer or configuration permission is exposed here. The trusted root is
selected by component-launch, never a tool argument. Same-user filesystem access
is outside this boundary: these files do not sandbox their local owner.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'mcp-servers/netconverter-mcp'))
from artifacts import Refused, directory, publish_file, read_file

LIMIT = 2 * 1024 * 1024
TOOL = 'pyats_configure_device'


def digest(data): return hashlib.sha256(data).hexdigest()
def pack(data): return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9-]{32,36}', value): raise Refused('invalid_artifact_reference')
    return value


class PrivateMigration:
    def __init__(self, root, harness=None):
        self.root = Path(root)
        with directory(self.root, create=True, private=True): pass
        self.installation = digest(str(self.root).encode())
        self.harness = harness or uuid.uuid4().hex

    def read(self, relative):
        data, _ = read_file(self.root / relative, limit=4 * LIMIT)
        return json.loads(data)

    def publish(self, data, role='evidence'):
        ref = uuid.uuid4().hex
        target = self.root / 'artifacts' / (ref + '.artifact')
        publish_file(target, data, mode=0o400)
        return {'artifact_ref': ref, 'path': str(target), 'sha256': digest(data), 'bytes': len(data), 'role': role}

    def log_path(self):
        target=self.root/'logs'/(uuid.uuid4().hex+'.log')
        publish_file(target,b'')
        return str(target)

    def inventory(self, fingerprint, devices):
        receipt = {'schema': 1, 'installation': self.installation, 'harness': self.harness,
                   'pid': os.getpid(), 'observed': time.time(), 'testbed': fingerprint, 'devices': devices}
        target = self.root / 'inventories' / (self.harness + '.json')
        temporary = target.with_name(uuid.uuid4().hex + '.tmp')
        publish_file(temporary, pack(receipt)); os.replace(temporary, target)
        return receipt

    def claim(self, grant_ref, artifact_ref, current, device):
        """Verify actual context, then durably consume BEFORE any network write."""
        envelope = self.read('grants/' + ident(grant_ref) + '.json')
        raw = base64.b64decode(envelope['payload'], validate=True)
        key, _ = read_file(self.root / 'api-signing.key', limit=32)
        if len(key) != 32 or not hmac.compare_digest(hmac.new(key, raw, hashlib.sha256).hexdigest(), envelope['signature']):
            raise Refused('invalid_apply_signature')
        claim = json.loads(raw)
        now = time.time()
        if not (claim['schema'] == 1 and claim['nonce'] == grant_ref and claim['tool'] == TOOL and
                claim['installation'] == self.installation and claim['harness'] == self.harness and
                claim['testbed'] == current['testbed'] and claim['issued'] <= now < claim['expires'] <= claim['issued'] + 300 and
                claim['endpoint'] == device and device in current['devices']):
            raise Refused('apply_context_changed_or_expired')
        record = self.read('records/' + ident(claim['record']) + '/record.json')
        policy = self.read('policy.json')
        candidate = claim['candidate']
        if (record['id'] != claim['task'] or record['phase'] != 'apply' or record['status'] != 'running' or
                record['requestHash'] != claim['requestHash'] or record['revision'] != claim['revision'] or
                record.get('applyRevision') != claim['applyRevision'] or record.get('migration') != claim['migration'] or
                grant_ref not in record.get('applyGrants', []) or not policy.get('enabled') or
                policy['revision'] != claim['revision'] or candidate['artifact_ref'] != artifact_ref or
                candidate != record['migration']['candidate'] or record['artifacts'] != claim['artifacts']):
            raise Refused('apply_record_changed_or_closed')
        identity = {k: device[k] for k in ('id', 'host', 'port', 'protocol')}
        if (claim['profile'] != record['migration']['profile'] or len(record['devices']) != 1 or
                any(record['devices'][0].get(k) != v for k,v in identity.items()) or
                {(a['device'],a['kind']) for a in claim['artifacts']} != {(device['id'],'baseline'),(device['id'],'rollback')} or
                len(claim['artifacts']) != 2):
            raise Refused('apply_scope_or_evidence_changed')
        if not any(all(d.get(k) == v for k, v in identity.items()) for d in policy['devices']):
            raise Refused('endpoint_no_longer_authorized')
        for entry in claim['artifacts']:
            d = next((d for d in record['devices'] if d['id'] == entry['device']), None)
            if not d: raise Refused('missing_baseline_binding')
            target = Path(d[entry['kind'] + 'Path'])
            if target.parent != self.root / 'records' / record['id']: raise Refused('baseline_outside_record')
            raw_artifact, _ = read_file(target, limit=4 * LIMIT)
            if len(raw_artifact) != entry['bytes'] or digest(raw_artifact) != entry['sha256']:
                raise Refused('baseline_or_rollback_changed')
            if entry['kind']=='baseline':
                receipt_raw,_=read_file(Path(str(target)+'.receipt.json'),limit=65536)
                receipt=json.loads(receipt_raw);captured=receipt.get('artifact',{})
                if (receipt.get('schema')!=1 or receipt.get('record')!=record['id'] or
                    receipt.get('installation')!=self.installation or receipt.get('harness')!=self.harness or
                    receipt.get('testbed')!=current['testbed'] or
                    any(receipt.get('endpoint',{}).get(k)!=device[k] for k in ('id','host','port','protocol')) or
                    captured.get('role')!='running-configuration' or captured.get('bytes')!=len(raw_artifact) or
                    captured.get('sha256')!=digest(raw_artifact)):
                    raise Refused('collected_baseline_changed')
                original,_=read_file(self.root/'artifacts'/(ident(captured['artifact_ref'])+'.artifact'),limit=LIMIT)
                if len(original)!=len(raw_artifact) or digest(original)!=digest(raw_artifact):
                    raise Refused('collected_baseline_changed')
        raw_candidate, _ = read_file(self.root / 'candidates' / (ident(artifact_ref) + '.cfg'), limit=LIMIT)
        if len(raw_candidate) != candidate['bytes'] or digest(raw_candidate) != candidate['sha256']:
            raise Refused('candidate_changed')
        text = raw_candidate.decode('utf8')
        if '\x00' in text or not text.strip(): raise Refused('invalid_candidate_text')
        # Junos block-format imports need a distinct qualified load path. Never
        # feed arbitrary blocks/commit/rollback/shell syntax to configure().
        if device['os'] == 'junos':
            if ';' in text or '|' in text or any(line.strip() and not line.strip().startswith('set ') for line in text.splitlines()):
                raise Refused('junos_set_format_without_command_separators_required')
        publish_file(self.root / 'attempts' / (grant_ref + '.json'), pack({'state': 'unknown', 'claim': claim, 'at': now}))
        return text

    def collection(self, output, device, *, change_ref=None, current=None):
        """No caller-chosen output path. Optional baseline is tied to PREPARE."""
        data = output.encode()
        if not 8 <= len(data) <= LIMIT: raise Refused('invalid_collection_size')
        artifact = self.publish(data, 'running-configuration')
        if change_ref:
            record = self.read('records/' + ident(change_ref) + '/record.json')
            if record['phase'] != 'prepare' or record['status'] != 'running': raise Refused('collection_requires_prepare')
            matched = next((d for d in record['devices'] if all(d.get(k) == device[k] for k in ('id','host','port','protocol'))), None)
            if not matched: raise Refused('collection_endpoint_mismatch')
            migration=record.get('migration')
            if migration and (not current or migration['harness']!=self.harness or
                              migration['installation']!=self.installation or migration['testbed']!=current['testbed']):
                raise Refused('collection_inventory_mismatch')
            expected = self.root / 'records' / record['id']
            for field in ('baselinePath',):
                path = Path(matched[field])
                if path.parent != expected: raise Refused('baseline_outside_record')
                publish_file(path, data)
                if migration:
                    receipt={'schema':1,'record':record['id'],'installation':self.installation,
                             'harness':self.harness,'testbed':current['testbed'],
                             'endpoint':device,'artifact':artifact}
                    publish_file(Path(str(path)+'.receipt.json'),pack(receipt),mode=0o400)
            # Keep rollback planning separate: a captured config is not evidence
            # that replaying it restores deleted/changed device state.
        return artifact


class Rehearsal:
    """Append-only creation/evidence ledger; never adopts names or deletes labs."""
    def __init__(self, root, run_id):
        self.root = Path(root) / 'rehearsals' / ident(run_id)
        with directory(self.root, create=True, private=True): pass

    def begin(self, provider, scope, assertions):
        if not provider or not scope or not assertions or len(pack([provider,scope,assertions])) > 65536:
            raise Refused('bounded_rehearsal_scope_required')
        publish_file(self.root / 'manifest.json', pack({'provider':provider,'scope':scope,'assertions':assertions,'retention':'retain'}))

    def attempt(self, tool, arguments_hash):
        read_file(self.root / 'manifest.json', limit=65536)
        if not re.fullmatch('[a-f0-9]{64}', arguments_hash) or not tool: raise Refused('invalid_creation_attempt')
        ref = uuid.uuid4().hex
        publish_file(self.root / (ref + '-attempt.json'), pack({'tool':tool,'arguments_hash':arguments_hash,'state':'unknown'}))
        return ref

    def reconcile(self, attempt, provider_id, ownership):
        read_file(self.root / (ident(attempt) + '-attempt.json'))
        if ownership != {'run_id': self.root.name, 'attempt_id': attempt} or not provider_id:
            raise Refused('unproven_resource_ownership')
        publish_file(self.root / (attempt + '-resource.json'), pack({'provider_id':provider_id,'ownership':ownership,'retention':'retain'}))

    def evidence(self, assertion, verdict, evidence_class, artifact):
        read_file(self.root / 'manifest.json', limit=65536)
        if verdict not in ('passed','failed','blocked','not_run','unknown') or evidence_class not in ('controlled-peer','static-model','live-virtual','live-device'):
            raise Refused('invalid_evidence_verdict')
        if len(pack([assertion,artifact])) > 65536: raise Refused('evidence_metadata_too_large')
        publish_file(self.root / (uuid.uuid4().hex + '-evidence.json'), pack({'assertion':assertion,'verdict':verdict,'class':evidence_class,'artifact':artifact}))
