import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import r10_ops as ops


def test_verdict_reports_durable_ack_and_epoch():
    current = {'state': 'completed', 'result': {'durable_ack': True, 'evidence': {'outcome': 'succeeded'}}, 'authority': {'epoch': 7}}
    line = ops.verdict('nne1', 'abc123', current)
    assert 'completed' in line and 'durable_ack=True' in line and 'epoch=7' in line


def test_load_reads_group_summary(tmp_path):
    (tmp_path / 'summary.json').write_text(json.dumps({'nodes': [{'code': 'nne1'}], 'cluster_id': 'c', 'generation': 'g'}))
    assert ops.load(tmp_path)['cluster_id'] == 'c'


def test_member_scripts_are_syntactically_valid_and_scoped():
    root = Path(__file__).resolve().parents[2]
    for name in ('ha-r10-members.sh', 'ha-r10-teardown-all.sh', 'ha-r10-build-group.sh'):
        assert subprocess.run(['bash', '-n', str(root / 'scripts' / name)]).returncode == 0
    text = (root / 'scripts/ha-r10-teardown-all.sh').read_text()
    assert 'rg-nc198-' in text and 'nc198-' in text            # refuses names outside the spec-198 scope
    assert 'netclaw-r08' not in text                           # never touches other labs' containers
    members = (root / 'scripts/ha-r10-members.sh').read_text()
    assert 'ollama)' not in members.lower() and 'subnet|pyats' in members   # hosted flavors only
