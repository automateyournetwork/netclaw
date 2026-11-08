"""Read-only private evidence snapshots; reservations never imply actual effects.

Each SQLite database is read in one transaction. Separate databases, consensus,
files and external observations are not a globally atomic snapshot. Exports
retain those limits and never turn missing evidence into a zero counter.
"""
import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import time

from .real_budget import canonical, need, read_private, uuid_value

MAX_JOURNAL_BYTES = 32 * 1024 * 1024
MAX_ROWS = 10000
ARTIFACTS = ('containment.json', 'cleanup.json', 'ollama-accounting.json',
             'inference-refusal.json', 'tool/mcp-schema.json', 'tool/mcp-call.json',
             'tool/native-mcp-result.json', 'tool/mcp-result.json', 'tool/tool-evidence.json')


def observation(path):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return {'available': False, 'reason': 'not_present'}
    raw = read_private(path, 8 * 1024 * 1024)
    return {'available': True, 'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'value': json.loads(raw),
            'observed_at_ms': int(time.time() * 1000)}


def journal_snapshot(path, tables):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return {'available': False, 'reason': 'not_present'}
    # Validate the owned private file without treating its raw bytes as a
    # consistent backup: committed rows may currently live in a WAL file.
    read_private(path, MAX_JOURNAL_BYTES)
    result = {}
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')
            existing = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in tables:
                # Table names are code-owned constants, never command arguments.
                need(table.replace('_', '').isalnum(), 'journal_table_invalid')
                if table not in existing:
                    result[table] = {'available': False, 'reason': 'table_not_present'}
                    continue
                rows = [dict(r) for r in db.execute('SELECT * FROM ' + table + ' ORDER BY rowid LIMIT ?', (MAX_ROWS + 1,))]
                need(len(rows) <= MAX_ROWS, 'journal_export_bound')
                result[table] = {'available': True, 'rows': rows}
            db.commit()
    except sqlite3.Error:
        return {'available': False, 'reason': 'sqlite_unavailable'}
    need(len(canonical(result)) <= MAX_JOURNAL_BYTES, 'journal_export_bound')
    return {'available': True, 'tables': result, 'observed_at_ms': int(time.time() * 1000),
            'consistency': 'single_database_read_transaction'}


def table_rows(journal, table):
    entry = journal.get('tables', {}).get(table, {})
    return entry['rows'] if journal.get('available') and entry.get('available') else None


def execution_evidence(root, operation_id):
    uuid_value(operation_id)
    root = Path(root)
    home = root / 'homes/member'
    state = home / 'netclaw-federation'
    runtime = state / 'runtime'
    journals = {
        'member': journal_snapshot(home / 'n2n/federation.db', ('protected_operation',)),
        'admission': journal_snapshot(state / 'ha-member/ha-admission.sqlite3', ('ha_identity', 'ha_admission')),
        'inference': journal_snapshot(runtime / 'inference.sqlite', ('protected_inference',)),
        'runner': journal_snapshot(runtime / 'ollama-runner.sqlite',
                                   ('runner_latch', 'runner_recovery', 'runner_profile_transition')),
    }
    inference = table_rows(journals['inference'], 'protected_inference')
    selected = [r for r in inference if r['operation_id'] == operation_id] if inference is not None else None
    artifacts = {name: observation(runtime / operation_id / name) for name in ARTIFACTS}
    independent = {name: dict(observation(root / 'counter-observations' / (name + '.json')),
                             interpretation='unverified_observation') for name in ('guard', 'model', 'native')}
    return {'schema_version': 1, 'operation_id': operation_id, 'journals': journals,
            'inference_claims': {'total': len(inference) if inference is not None else None,
                                'operation': len(selected) if selected is not None else None,
                                'finished_responses': sum(r['state'] == 'finished' for r in selected) if selected is not None else None},
            'operation_artifacts': artifacts, 'independent_counter_artifacts': independent,
            'actual_effect_totals': {'model_forwards': None, 'native_handoffs': None},
            'globally_consistent_snapshot': False,
            'limits': ['Inference rows and native intents/claims precede final admission and handoff.',
                       'Finished responses prove completion evidence, not an exact cumulative send count.',
                       'Independent counter artifacts are copied verbatim for review; their assertions are not trusted.',
                       'Missing or unverified counters are unknown, never zero.']}
