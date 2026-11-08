"""Coordinator-only REAL fenced-restore driver (spec 179). Default-off, additive.

Wraps the proven primitives of the fixture (`fenced_restore_fixture`, `restore_verify`,
`HostIsolation`, `recovery.install_restored/activate_restored`) around ONE real run root.
It never prepares/approves an operation, never reserves budget, never starts a model, Border
or member, and never deletes anything. Importing or `plan` is inert; every other phase is
explicit, one-shot (exclusive claim, no retry) and requires its predecessor and the reviewed
restore-plan hash. The restore happens in-process against the production Authority/
OperationLedger gates: a REAL operator-level fresh admission is impossible on this run root
anyway (the unknown operation retains the budget slot).

Run from the run's frozen source directory with the reviewed Python:
    python -B -m labs.ha.real_restore <phase> --root <run-root> [--plan-sha256 <hash>] ...
See labs/ha/REAL-FENCED-RESTORE.md for the complete procedure and evidence rules.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from urllib.parse import quote

from .real_budget import Budget, RehearsalRefused, canonical, digest, need, private_directory, read_private, write_new

PHASES = ('prepare', 'capture', 'snapshot', 'gap', 'isolate', 'exports', 'start-new', 'install', 'counters')
TERMINAL = ('completed', 'failed', 'refused')
ROLES = ('border0', 'border1', 'border2', 'member')
MAX_EXPORT_FILES = 256
BACKUPS = ('homes/member/n2n/federation.db', 'homes/member/netclaw-federation/runtime/inference.sqlite',
           'homes/member/netclaw-federation/runtime/ollama-runner.sqlite',
           'homes/member/netclaw-federation/ha-member/ha-admission.sqlite3',
           'homes/border0/n2n/federation.db', 'homes/border1/n2n/federation.db', 'homes/border2/n2n/federation.db')


def _paths():
    """Make the frozen source's production helpers importable (lazy, never at import)."""
    root = Path(__file__).resolve().parents[2]
    for extra in (root, root / 'mcp-servers/protocol-mcp', root / 'scripts/lib'):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))


def docker_read(args):
    result = subprocess.run(['docker', *args], capture_output=True, timeout=20)
    need(result.returncode == 0 and len(result.stdout) <= 4 * 1024 * 1024, 'owned_inventory_unavailable')
    return result.stdout


def real_running_voters(expected, owner, docker=docker_read):
    """Global voter cap for a REAL run root.

    Unlike the fixture's inventory this tolerates the run's own model container (owner label
    `<name>-model`) and reviewed peer proxies. Any other running spec179 resource is refused.
    """
    ids = docker(['ps', '--filter', 'label=netclaw.spec=179', '--format', '{{.ID}}']).decode().split()
    rows = json.loads(docker(['inspect', *ids])) if ids else []
    voters = []
    for row in rows:
        labels = row['Config'].get('Labels') or {}
        need(labels.get('netclaw.spec') == '179', 'voter_inventory_changed')
        from .etcd_lab import IMAGE
        if row['Config']['Image'] == IMAGE and '/usr/local/bin/etcd' in (row['Config'].get('Cmd') or []):
            voters.append(row['Id'])
        else:
            need(labels.get('netclaw.role') == 'peer-proxy'
                 or (labels.get('netclaw.owner') or '').startswith(owner) and row['Name'].lstrip('/').endswith('-model'),
                 'unreviewed_running_r08_resource')
    need(len(voters) <= 3 and set(voters) == set(expected), 'global_voter_bound_or_identity_changed')
    return rows


def real_stale_gap(stale, later, first_id, unknown_id):
    """Genuine-gap proof for a REAL unknown. Unlike the fixture it does not require a committed
    model claim: a real unknown (e.g. member killed after dispatch) is `dispatch_claimed` with
    its reservations held and may have no claim. A completed/failed later operation is refused."""
    before, after = stale['records'], later['records']
    first, second = 'operations/' + first_id, 'operations/' + unknown_id
    need(first_id != unknown_id and first in before and second in after and second not in before
         and before[first]['value']['state'] == 'completed'
         and after[second]['value']['state'] not in TERMINAL
         and after[second]['value'].get('attempt_id') and later['revision'] > stale['revision'],
         'genuine_stale_operation_gap_required')
    from bgp.federation.ha.operations import reservation_keys
    resources = reservation_keys(after[second]['value']['review'])
    for key in resources:
        need(key in before and before[key]['value']['state'] == 'released'
             and before[key]['value']['operation_id'] == first_id
             and after[key]['value']['state'] == 'reserved' and after[key]['value']['operation_id'] == unknown_id,
             'genuine_stale_reservation_gap_required')
    claims = sorted(k for k, row in after.items() if k.startswith('claims/') and k not in before
                    and row['value'].get('request', {}).get('operation_id') == unknown_id)
    return {'first_operation_id': first_id, 'later_unknown_operation_id': unknown_id,
            'later_state': after[second]['value']['state'], 'missing_operation_key': second,
            'missing_claim_keys': claims, 'changed_resource_keys': resources,
            'stale_revision': stale['revision'], 'later_revision': later['revision'],
            'missing_evidence_recovered': False, 'required_protection': 'global-generation-capacity-fence'}


def compare_counters(before, after):
    """Both files are coordinator-saved model access-log observations: `{"request_count": int, ...}`.
    Equality proves no model request after the restore began; it stays an unverified observation."""
    for value in (before, after):
        need(isinstance(value, dict) and type(value.get('request_count')) is int and value['request_count'] >= 0,
             'counter_observation_invalid')
    need(before['request_count'] == after['request_count'], 'model_counter_changed_after_restore')
    return {'model_request_count_before': before['request_count'], 'model_request_count_after': after['request_count'],
            'unchanged': True, 'interpretation': 'unverified_observation'}


def backup_sqlite(source, destination):
    """sqlite backup API over a read-only handle; WAL contents are never dropped."""
    source, destination = Path(source), Path(destination)
    read_private(source, 256 * 1024 * 1024)
    private_directory(destination.parent)
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600); os.close(fd)
    src = sqlite3.connect('file:' + quote(str(source), safe='/') + '?mode=ro', uri=True)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        src.close(); dst.close()
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def collect_exports(paths):
    """Explicit absolute private regular files only; at most 256 (HostIsolation.issue bound)."""
    seen, artifacts = set(), []
    for item in paths:
        path = Path(item)
        need(path.is_absolute() and path == path.resolve(), 'invalid_export_manifest')
        if str(path) in seen:
            continue
        seen.add(str(path))
        artifacts.append({'path': str(path), 'sha256': hashlib.sha256(read_private(path, 64 * 1024 * 1024)).hexdigest()})
    need(1 <= len(artifacts) <= MAX_EXPORT_FILES, 'export_artifact_capacity')
    return {'schema_version': 1, 'artifacts': sorted(artifacts, key=lambda a: a['path'])}


class Restore:
    def __init__(self, root, *, docker=docker_read, observe=None, frozen=True):
        from .real_runtime import hashed_file, pin_protocol_source, validate_plan
        self.root = private_directory(root)
        self.plan = validate_plan(json.loads(read_private(self.root / 'reviewed-plan.json', 8 * 1024 * 1024)))
        need(str(self.root) == self.plan['root'], 'run_root_changed')
        self.docker, self._observe_process = docker, observe
        self.R = self.root / 'restore'
        if frozen:
            source = self.root / 'source'
            need(Path(__file__).resolve() == source / 'labs/ha/real_restore.py', 'run_frozen_source_required')
            actual = {str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() or p.is_symlink()}
            need(actual == set(self.plan['source_files']), 'frozen_source_closure_changed')
            for name, expected in self.plan['source_files'].items():
                hashed_file(source / name, expected)
            pin_protocol_source(source)
        _paths()

    # ---- helpers -------------------------------------------------------
    def observe(self, pid):
        if self._observe_process:
            return self._observe_process(pid)
        from ha_cluster import process_observation
        return process_observation(pid)

    def old_lab(self):
        from .etcd_lab import EtcdLab
        from .real_runtime import voters_path
        return EtcdLab(voters_path(self.plan, self.root)).load()

    def new_lab(self):
        from .etcd_lab import EtcdLab
        return EtcdLab(self.R / 'new-voters').load()

    def host(self):
        from ha_cluster import HostIsolation
        return HostIsolation(self.R / 'isolation', self.R / 'host/host.crt', self.R / 'host/host.key')

    def manifest(self, lab):
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.config import verify_manifest
        anchor = read_private(lab.root / 'cluster-identity/root.crt').decode()
        return verify_manifest(read_private(lab.root / 'cluster-identity/manifest.json'), anchor,
                               expected_key_id=c.key_id(anchor))

    def voter_rows(self, lab, *, running):
        rows = lab.inspect_owned()
        for row in rows:
            state = row['State']
            need(row['HostConfig']['RestartPolicy']['Name'] in ('', 'no'), 'owned_voter_restart_policy')
            if running:
                need(state['Running'] and not state['Paused'] and not state['Restarting'] and state['Pid'] > 0
                     and set(row['NetworkSettings']['Networks']) == {lab.document['name']}, 'owned_voters_not_live_direct')
        return rows

    def running(self, expected):
        return real_running_voters(expected, self.plan['name'], self.docker)

    def read_json(self, path, maximum=64 * 1024 * 1024):
        return json.loads(read_private(path, maximum))

    # ---- phase machinery ----------------------------------------------
    def plan_hash(self):
        return digest(self.read_json(self.R / 'plan.json'))

    def run_phase(self, name, expected, **kwargs):
        need(name in PHASES and name != 'prepare', 'unknown_restore_phase')
        plan = self.read_json(self.R / 'plan.json')
        need(digest(plan) == expected and plan['run_id'] == self.plan['run_id'], 'reviewed_plan_changed')
        for rel, pinned in plan['pins'].items():
            need(hashlib.sha256(read_private(self.R / rel, 64 * 1024 * 1024)).hexdigest() == pinned, 'prepared_input_changed')
        index = PHASES.index(name)
        read_private(self.R / (PHASES[index - 1] + '.complete.json'))
        write_new(self.R / (name + '.claim.json'), {'schema_version': 1, 'phase': name, 'plan_sha256': expected,
                  'state': 'sent_or_unknown', 'claimed_at_ms': int(time.time() * 1000)})
        try:
            result = getattr(self, 'phase_' + name.replace('-', '_'))(**kwargs)
            write_new(self.R / (name + '.complete.json'), result)
            return result
        except BaseException as exc:
            write_new(self.R / (name + '.failed.json'), {'phase': name, 'type': type(exc).__name__,
                      'code': str(exc)[:80], 'automatic_retry': False, 'claim_retained': True})
            raise

    # ---- phases ---------------------------------------------------------
    def prepare(self):
        """Offline only: new generation voter set, replacement identity, host signer. No process, no Docker."""
        from bgp.federation.certs import create_self_signed
        from .etcd_lab import EtcdLab
        from .fenced_restore_fixture import replacement_identity
        need(not self.R.exists(), 'restore_already_prepared')
        old = self.old_lab(); old_manifest = self.manifest(old)
        need((old.root / 'cluster-identity/root.key').is_file(), 'offline_anchor_key_required')
        private_directory(self.R, create=True)
        new = EtcdLab(self.R / 'new-voters').prepare(cluster_id=old.document['cluster_id'])
        replacement_identity(new, old)
        taken = {p for ports in self.plan['ports'].values() for p in ports}
        new_manifest = self.manifest(new)
        fresh = set(new.document['ports'])
        for node in new_manifest.nodes:
            fresh.update(node['endpoints'][k]['port'] for k in ('cluster', 'in2n'))
        need(not fresh & taken, 'fresh_endpoint_collides_with_run_ports')
        need(old_manifest.generation != new_manifest.generation and old_manifest.anchor_key_id == new_manifest.anchor_key_id
             and not (new.root / 'cluster-identity/root.key').exists(), 'replacement_identity_invalid')
        host = private_directory(self.R / 'host', create=True)
        certificate, key = create_self_signed('r08/owned-host-isolation', days=3)
        write_new(host / 'host.crt', certificate.encode()); write_new(host / 'host.key', key.encode())
        private_directory(self.R / 'isolation', create=True); private_directory(self.R / 'evidence', create=True)
        private_directory(self.R / 'counters', create=True); private_directory(self.R / 'pre-isolation', create=True)
        pins = {str(p.relative_to(self.R)): hashlib.sha256(read_private(p, 64 * 1024 * 1024)).hexdigest()
                for p in sorted(self.R.rglob('*')) if p.is_file()}
        plan = {'schema_version': 1, 'class': 'REAL_RESTORE_PLAN', 'run_id': self.plan['run_id'], 'restore_id': str(uuid.uuid4()),
                'source_sha256': self.plan['source_sha256'], 'pins': pins, 'old': old.document, 'new': new.document,
                'phases': list(PHASES), 'limits': {'maximum_running_voters': 3, 'model_calls': 0, 'native_tool_calls': 0,
                'budget_reservations': 0, 'receipt_max_age_seconds': 300}, 'native_profile_qualified': False,
                'retention': 'old and new voter data, run root, journals and all evidence retained; no automatic deletion'}
        write_new(self.R / 'plan.json', plan)
        write_new(self.R / 'prepare.complete.json', {'class': 'PLAN_ONLY', 'plan_sha256': digest(plan), 'running_resources_created': 0})
        return {'class': 'PLAN_ONLY', 'plan_sha256': digest(plan), 'phases': list(PHASES), 'running_resources_created': 0}

    def phase_capture(self):
        """Seven or more live subjects, BEFORE operation A: 3 voter containers, 3 Border daemons, the member."""
        old = self.old_lab(); manifest = self.manifest(old)
        self.running([row['Id'] for row in self.voter_rows(old, running=True)])
        subjects = [{'kind': 'container', 'role': 'voter', 'node_id': None, 'id': row['Id']}
                    for row in self.voter_rows(old, running=True)]
        spawn = {}
        for index, role in enumerate(ROLES):
            state = self.root / 'homes' / role / 'netclaw-federation'
            daemon = self.read_json(state / 'daemon.json'); pid = daemon['pid']
            observed = self.observe(pid)
            need(observed['present'] and observed['uid'] == os.getuid(), 'owned_process_baseline_missing')
            spawn[role] = {'daemon_pid': pid, 'spawn_pid': self.read_json(self.root / (role + '-spawn.json'))['pid']}
            subjects.append({'kind': 'process', 'role': 'executor' if role == 'member' else 'border',
                             'node_id': None if role == 'member' else manifest.nodes[index]['node_id'], 'pid': pid,
                             'start_id': observed['start_id'], 'command_sha256': observed['command_sha256']})
        write_new(self.R / 'evidence/subjects.json', subjects)
        write_new(self.R / 'evidence/spawn-vs-daemon-pids.json', spawn)
        self.host().capture(manifest, old.document['name'], subjects)
        return {'class': 'REAL', 'subjects': len(subjects), 'budget_reservations': 0}

    def phase_snapshot(self, first_claim_file):
        """After A's export-operation settled, before any review of B (a review writes an operations record)."""
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.recovery import export_snapshot
        claim = self.read_json(first_claim_file)
        budget = Budget(self.root).snapshot()
        need(len(budget['reservations']) == 1 and budget['reservations'][0]['claim'] == claim
             and budget['reservations'][0]['state'] == 'settled', 'first_operation_must_be_the_only_settled_reservation')
        old = self.old_lab(); manifest = self.manifest(old); store = old.store(0)
        try:
            snapshot = export_snapshot(store, manifest)
        finally:
            store.close()
        records = snapshot['records']
        row = records.get('operations/' + claim['operation_id'], {}).get('value', {})
        need(row.get('state') == 'completed' and row.get('ack') is not None, 'first_operation_not_completed')
        need(all(r['value']['state'] in TERMINAL for k, r in records.items() if k.startswith('operations/')), 'stale_snapshot_has_unresolved_operation')
        need(all(r['value']['state'] == 'released' for k, r in records.items() if k.startswith('resources/')), 'stale_snapshot_has_held_resources')
        write_new(self.R / 'stale-snapshot.json', c.encode(snapshot))
        return {'class': 'REAL', 'stale_revision': snapshot['revision'], 'snapshot_sha256': c.sha256(snapshot),
                'first_operation_id': claim['operation_id']}

    def phase_gap(self, first_claim_file, unknown_claim_file, later_evidence_file):
        """After B's export-unknown: later snapshot is that export's `consensus-evidence.json`."""
        first, unknown = self.read_json(first_claim_file), self.read_json(unknown_claim_file)
        budget = Budget(self.root).snapshot()
        states = {r['claim']['operation_id']: r['state'] for r in budget['reservations']}
        need(states == {first['operation_id']: 'settled', unknown['operation_id']: 'unknown'}, 'budget_must_show_one_settled_and_one_unknown')
        later = self.read_json(later_evidence_file)
        need(later.get('available') is True, 'later_consensus_evidence_unavailable')
        stale = self.read_json(self.R / 'stale-snapshot.json')
        gap = real_stale_gap(stale, later['snapshot'], first['operation_id'], unknown['operation_id'])
        gap['later_evidence_sha256'] = hashlib.sha256(read_private(later_evidence_file, 64 * 1024 * 1024)).hexdigest()
        write_new(self.R / 'stale-gap.json', gap)
        write_new(self.R / 'evidence/budget-at-gap.json', budget)
        return {'class': 'REAL', 'gap': gap}

    def phase_isolate(self):
        """Old authority isolation. Border/member daemons must already be stopped (stop-role / killed)."""
        need((self.R / 'counters/model-before.json').is_file() and (self.R / 'pre-isolation/model-access.log').is_file(),
             'pre_isolation_model_evidence_required')
        old = self.old_lab(); inventory = self.read_json(self.R / 'isolation/owned-inventory.json')
        for subject in inventory['subjects']:
            if subject['kind'] == 'process':
                need(self.observe(subject['pid'])['present'] is False, 'old_processes_still_running')
        rows = self.voter_rows(old, running=True)
        self.running([row['Id'] for row in rows])
        evidence = self.R / 'evidence'
        write_new(evidence / 'voter-isolation-baseline.json', rows)
        from .etcd_lab import command
        for index, row in enumerate(rows):
            current = old.inspect_owned()[index]
            need(current['Id'] == row['Id'] and current['State']['Running'], 'owned_voter_state_changed')
            command(evidence, f'old-voter{index}-stop', ['docker', 'stop', '--time', '10', row['Id']], timeout=25)
            command(evidence, f'old-voter{index}-disconnect', ['docker', 'network', 'disconnect', old.document['name'], row['Id']])
        after = old.inspect_owned()
        need(all(not r['State']['Running'] and r['State']['Pid'] == 0 and r['NetworkSettings']['Networks'] == {} for r in after),
             'owned_voter_isolation_unproved')
        self.running([])
        write_new(evidence / 'voter-isolation-verified.json', after)
        write_new(evidence / 'actual-isolation.json', self.host()._observe(inventory, isolated=True))
        return {'class': 'REAL', 'old_voters_isolated': 3, 'old_processes_absent': True}

    def phase_exports(self, artifacts=(), export_dirs=()):
        """Immutable export manifest bound into the host receipt. Includes sqlite backups of closed journals."""
        backups = self.R / 'evidence/backups'; private_directory(backups, create=True)
        hashes = {}
        for rel in BACKUPS:
            if (self.root / rel).is_file():
                hashes[rel] = backup_sqlite(self.root / rel, backups / rel.replace('/', '__'))
        write_new(self.R / 'evidence/budget-final.json', Budget(self.root).snapshot())
        paths = [self.R / n for n in ('stale-snapshot.json', 'stale-gap.json', 'plan.json', 'isolation/owned-baseline.json',
                                      'isolation/owned-inventory.json')]
        for directory in [self.R / 'evidence', self.R / 'pre-isolation', self.R / 'counters', *map(Path, export_dirs)]:
            paths.extend(p for p in directory.rglob('*') if p.is_file())
        paths.extend(self.root / n for n in ('model/owned.json', 'reviewed-plan.json', 'source-manifest.json') if (self.root / n).is_file())
        paths.extend(self.root / (r + n) for r in ROLES for n in ('-spawn.json', '-daemon.log') if (self.root / (r + n)).is_file())
        paths.extend(Path(a) for a in artifacts)
        manifest = collect_exports(paths)
        write_new(self.R / 'exports.json', manifest)
        return {'class': 'REAL', 'artifacts': len(manifest['artifacts']), 'sqlite_backups': hashes}

    def phase_start_new(self):
        self.host()._observe(self.read_json(self.R / 'isolation/owned-inventory.json'), isolated=True)
        self.running([])
        new = self.new_lab(); new.start()
        rows = self.voter_rows(new, running=True)
        self.running([r['Id'] for r in rows])
        from bgp.federation.ha.recovery import _require_empty_namespace
        store = new.store(0)
        try:
            _require_empty_namespace(store)
        finally:
            store.close()
        return {'class': 'REAL', 'running_new_voters': [r['Id'] for r in rows], 'unused_namespace_verified': True}

    def phase_install(self):
        from bgp.federation import protected_contract as c
        from bgp.federation.ha.recovery import verify_isolation, install_restored, activate_restored, _require_empty_namespace
        from .restore_verify import verify_restore
        old, new = self.old_lab(), self.new_lab(); old_m, new_m = self.manifest(old), self.manifest(new)
        self.running([r['Id'] for r in self.voter_rows(new, running=True)])
        inventory = self.read_json(self.R / 'isolation/owned-inventory.json')
        host = self.host(); host._observe(inventory, isolated=True)
        counters = self.read_json(self.R / 'counters/model-before.json')
        store = new.store(0)
        try:
            _require_empty_namespace(store)
            snapshot_file = self.R / 'stale-snapshot.json'; snapshot = c.decode(read_private(snapshot_file, 4 * 1024 * 1024), 4 * 1024 * 1024)
            gap = self.read_json(self.R / 'stale-gap.json')
            # Receipt only after the new voters are ready: it lives five minutes.
            proof = host.issue(old_m, new_m, snapshot_file, self.R / 'exports.json')
            receipt = verify_isolation(proof, host.certificate, expected_key_id=c.key_id(host.certificate),
                                       old_manifest=old_m, new_manifest=new_m, snapshot=snapshot)
            installed = install_restored(store, snapshot, old_m, new_m, receipt)
            write_new(self.R / 'restore-installed.json', installed)
            node = new_m.nodes[0]['node_id']
            inactive = verify_restore(store, snapshot, old_m, new_m, node)
            write_new(self.R / 'restore-inactive-gates.json', inactive)
            need(inactive['gate_results'] == [{'gate': 'campaign', 'code': 'recovery_fenced'}], 'inactive_campaign_not_fenced')
            host._observe(inventory, isolated=True)
            active = activate_restored(store, snapshot, old_m, new_m, receipt)
            write_new(self.R / 'restore-activated.json', active)
            verified = verify_restore(store, snapshot, old_m, new_m, node)
            write_new(self.R / 'restore-active-gates.json', verified)
            need(verified['capacity_frozen'] is True and {g['code'] for g in verified['gate_results']} == {'recovery_fenced'}
                 and {g['gate'] for g in verified['gate_results']} == {'fresh-prepare', 'model-admission', 'tool-admission'},
                 'stale_restore_unfenced')
            missing = store.read_many([gap['missing_operation_key'], *gap['missing_claim_keys']])
            need(all(v[0] is None for v in missing.values()), 'stale_gap_was_silently_recreated')
            host._observe(inventory, isolated=True)
        finally:
            store.close()
        return {'class': 'REAL', 'passed': True, 'receipt_id': proof['payload']['receipt_id'], 'inactive': inactive,
                'activated': active, 'active': verified, 'gap': gap, 'missing_evidence_recovered': False,
                'model_calls': 0, 'native_tool_calls': 0, 'budget_reservations': 0, 'model_counter_before': counters,
                'new_voters_retained_running': 3, 'old_voters_retained_isolated': 3, 'native_profile_qualified': False,
                'cleanup_of_new_voters_pending': True}

    def phase_counters(self):
        verdict = compare_counters(self.read_json(self.R / 'counters/model-before.json'),
                                   self.read_json(self.R / 'counters/model-after.json'))
        need(Budget(self.root).snapshot()['reserved']['operations'] == 2, 'restore_consumed_budget')
        return {'class': 'REAL', **verdict, 'budget_reservations_by_restore': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', *PHASES))
    parser.add_argument('--root'); parser.add_argument('--plan-sha256')
    parser.add_argument('--first-claim-file'); parser.add_argument('--unknown-claim-file')
    parser.add_argument('--later-evidence-file')
    parser.add_argument('--artifact', action='append', default=[]); parser.add_argument('--export-dir', action='append', default=[])
    args = parser.parse_args(argv); os.umask(0o077)
    if args.command == 'plan':
        print(json.dumps({'class': 'PLAN_ONLY', 'phases': list(PHASES)})); return 0
    need(args.root, 'root_required')
    run = Restore(args.root)
    if args.command == 'prepare':
        result = run.prepare()
    else:
        need(args.plan_sha256, 'reviewed_plan_hash_required')
        extra = {'snapshot': {'first_claim_file': args.first_claim_file},
                 'gap': {'first_claim_file': args.first_claim_file, 'unknown_claim_file': args.unknown_claim_file,
                         'later_evidence_file': args.later_evidence_file},
                 'exports': {'artifacts': args.artifact, 'export_dirs': args.export_dir}}.get(args.command, {})
        result = run.run_phase(args.command, args.plan_sha256, **extra)
    print(json.dumps(result, sort_keys=True)); return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, RuntimeError):
        print('r08_real_restore: failed_or_unknown; claim retained; no retry', file=sys.stderr)
        raise SystemExit(1)
