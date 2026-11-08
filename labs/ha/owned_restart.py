"""Serial exact-owned voter restart; only a coordinator may execute this helper.

The export is mandatory and durable before any stop. A start failure is not
retried. Actual inspected state is retained for explicit follow-up recovery.
"""
import hashlib
from pathlib import Path

from .etcd_lab import private, command


class OwnedVoterRestart:
    def __init__(self, lab, evidence, snapshot_file):
        self.lab, self.evidence, self.snapshot_file = lab, Path(evidence), Path(snapshot_file)

    def execute(self):
        raw = self.snapshot_file.read_bytes()
        if not raw or not self.snapshot_file.is_absolute():
            raise RuntimeError('restart_export_required')
        before = self.lab.inspect_owned()
        if any(not row['State']['Running'] or row['State']['Paused'] for row in before):
            raise RuntimeError('restart_baseline_not_running')
        ids = [row['Id'] for row in before]
        private(self.evidence / 'voter-restart.claim.json', {'ids': ids,
            'snapshot_sha256': hashlib.sha256(raw).hexdigest()})
        private(self.evidence / 'voter-restart.baseline.json', before)
        for index, identifier in enumerate(ids):
            current = self.lab.inspect_owned()[index]
            if current['Id'] != identifier or not current['State']['Running']:
                raise RuntimeError('restart_identity_changed')
            command(self.evidence, f'restart-stop-v{index}', ['docker', 'stop', '--time', '10', identifier], timeout=20)
        stopped = self.lab.inspect_owned()
        private(self.evidence / 'voter-restart.stopped.json', stopped)
        if any(row['State']['Running'] or row['State']['Paused'] for row in stopped):
            raise RuntimeError('restart_stop_not_verified')
        for index, identifier in enumerate(ids):
            current = self.lab.inspect_owned()[index]
            if current['Id'] != identifier or current['State']['Running']:
                raise RuntimeError('restart_identity_changed')
            command(self.evidence, f'restart-start-v{index}', ['docker', 'start', identifier], timeout=20)
        after = self.lab.inspect_owned()
        private(self.evidence / 'voter-restart.verified.json', after)
        if any(not row['State']['Running'] or row['State']['Paused'] for row in after):
            raise RuntimeError('restart_start_not_verified')
        return {'kind': 'actual-owned-voter-restart', 'ids': ids,
                'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
                'baseline_pids': [row['State']['Pid'] for row in before],
                'restarted_pids': [row['State']['Pid'] for row in after]}
