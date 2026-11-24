"""Sequential fresh-context Spec200 passes. No model resume and no paid trial logic."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path('/Users/john.capobianco/netclaw-spec200-genie')
FEATURE = ROOT / 'specs/200-genie-network-worlds'
NOTES = FEATURE / 'loops'
PRIVATE = ROOT / '.spec200-local/ralph'
STATE = PRIVATE / 'state.json'
CONTROL = PRIVATE / 'control.json'
EXPECTED_BRANCH = '200-genie-network-worlds'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.chmod(0o600)
    temp.replace(path)


def tasks():
    rows = re.findall(r'^- \[([xX ])\] (T\d+)\b', (FEATURE / 'tasks.md').read_text(), re.M)
    if len(rows) != 30 or len({r[1] for r in rows}) != 30:
        raise RuntimeError('task_inventory_changed_review_required')
    return {name: mark.lower() == 'x' for mark, name in rows}


def branch():
    return subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()


def control():
    data = json.loads(CONTROL.read_text())
    if data['max_passes'] != 32 or data['schema'] != 1:
        raise RuntimeError('invalid_loop_control')
    return data


def source_digest():
    h = hashlib.sha256()
    for folder in ['scripts/genie-worlds', 'tests/genie-worlds', 'mcp-servers/genie-worlds-mcp', 'workspace/skills/netclaw-genie-worlds']:
        base = ROOT / folder
        if not base.exists():
            continue
        for p in sorted(base.rglob('*')):
            if p.is_file() and not any(x in p.parts for x in ['node_modules', '__pycache__', '.venv']):
                h.update(str(p.relative_to(ROOT)).encode())
                h.update(p.read_bytes())
    for name in ['scripts/lib/catalog.sh', 'scripts/lib/install-steps.sh', 'config/openclaw.json']:
        p = ROOT / name
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()


def progress(state):
    rows = ['# Spec200 Ralph progress', '',
            f"Status: **{state['status']}**. Passes started: {state.get('passes_started', 0)}/32.",
            f"Tasks complete: {sum(tasks().values())}/30. Updated: {stamp()}.", '',
            'Each pass is a new `codex exec --ephemeral` process. No conversation is resumed.',
            'Private process logs/state are in `.spec200-local/ralph/`. This is source progress,not live acceptance.', '',
            '| Pass | Outcome | Tasks complete | Handoff |', '| --- | --- | --- | --- |']
    for r in state.get('history', []):
        rows.append(f"| {r['pass']:02} | {r['outcome']} | {r['tasks_complete']}/30 | [pass-{r['pass']:02}.md](pass-{r['pass']:02}.md) |")
    if state.get('reason'):
        rows += ['', 'Stop/review reason: ' + state['reason']]
    (NOTES / 'PROGRESS.md').write_text('\n'.join(rows) + '\n')


def run():
    os.umask(0o077)
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (PRIVATE / 'runner.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError('loop_already_running')
    if branch() != EXPECTED_BRANCH:
        raise RuntimeError('branch_mismatch')
    state = json.loads(STATE.read_text()) if STATE.exists() else {
        'schema': 1, 'passes_started': 0, 'history': [], 'stagnant_passes': 0,
        'started_at': stamp(), 'status': 'ready'}
    if state['status'] == 'running_pass':
        raise RuntimeError('previous_pass_outcome_requires_review')
    state['runner_pid'] = os.getpid()
    save(STATE, state)
    for number in range(state['passes_started'] + 1, 33):
        ctl = control()
        if ctl.get('stop_requested'):
            state.update(status='stopped_by_owner', reason='stop_requested')
            break
        if branch() != EXPECTED_BRANCH:
            state.update(status='review_required', reason='branch_changed')
            break
        before = tasks()
        if all(before.values()):
            state.update(status='complete' if ctl.get('owner_acceptance') == 'accepted' else 'review_required',
                         reason='all_tasks_checked; actual owner acceptance required' if ctl.get('owner_acceptance') != 'accepted' else 'all_tasks_and_owner_acceptance')
            break
        before_digest = source_digest()
        state.update(status='running_pass', passes_started=number, active_started_at=stamp(), child_pid=None)
        state.pop('reason', None)
        save(STATE, state)
        progress(state)
        prefix = PRIVATE / f'pass-{number:02}'
        response = prefix.with_suffix('.result.json')
        argv = ['/opt/homebrew/bin/codex', 'exec', '--ephemeral', '--json', '--color', 'never',
                '-C', str(ROOT), '-s', 'danger-full-access', '-c', 'approval_policy="never"',
                '--output-schema', str(NOTES / 'result.schema.json'),
                '--output-last-message', str(response), '-']
        env = dict(os.environ)
        for key in list(env):
            if key.startswith(('GEMINI_', 'GOOGLE_', 'PYATS_', 'CML_')):
                env.pop(key)
        env['SPEC200_LOOP_NUMBER'] = f'{number:02}'
        env['NETCLAW_TEST_TMP'] = str(ROOT / '.spec200-local/tests')
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        timed_out = False
        with prefix.with_suffix('.events.jsonl').open('wb') as stdout, prefix.with_suffix('.stderr.log').open('wb') as stderr:
            child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                     env=env, start_new_session=True)
            state['child_pid'] = child.pid
            save(STATE, state)
            print(json.dumps({'event': 'pass_started', 'pass': number, 'tasks_complete': sum(before.values()), 'at': stamp()}), flush=True)
            child.stdin.write((NOTES / 'PROMPT.md').read_bytes())
            child.stdin.close()
            deadline = time.monotonic() + 900
            while child.poll() is None:
                if control().get('stop_requested') or time.monotonic() > deadline:
                    timed_out = True
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                    break
                time.sleep(1)
        after = tasks()
        thread_id = None
        with prefix.with_suffix('.events.jsonl').open(errors='replace') as events:
            for line in events:
                try:
                    event = json.loads(line)
                    if event.get('type') == 'thread.started':
                        thread_id = event.get('thread_id')
                        break
                except ValueError:
                    continue
        try:
            report = json.loads(response.read_text())
        except (OSError, ValueError):
            report = None
        if timed_out:
            outcome = 'interrupted_review_required'
        elif child.returncode or not report:
            outcome = 'runner_error'
        else:
            outcome = report['status']
        entry = {'pass': number, 'outcome': outcome, 'exit_code': child.returncode,
                 'thread_id': thread_id,
                 'tasks_complete': sum(after.values()), 'at': stamp(),
                 'changed_tasks': [t for t in after if after[t] != before[t]],
                 'source_changed': before_digest != source_digest()}
        state['history'].append(entry)
        state['child_pid'] = None
        no_work = not entry['source_changed'] and not entry['changed_tasks']
        state['stagnant_passes'] = state['stagnant_passes'] + 1 if no_work and outcome == 'blocked' else 0
        note = NOTES / f'pass-{number:02}.md'
        if not note.exists():
            note.write_text(f"# Pass {number:02}\n\nOutcome: {outcome}. No complete agent handoff was produced.\nReview private logs and existing file changes before continuing.\n")
        if outcome in ['runner_error', 'interrupted_review_required']:
            state.update(status='review_required', reason=outcome)
        elif thread_id and any(h.get('thread_id') == thread_id for h in state['history'][:-1]):
            state.update(status='review_required', reason='context_reuse_detected')
        elif after['T029'] and control().get('owner_acceptance') != 'accepted':
            state.update(status='review_required', reason='human_acceptance_not_recorded')
        elif state['stagnant_passes'] >= 3:
            state.update(status='blocked', reason='three_passes_without_independent_progress')
        else:
            state.update(status='between_passes')
        save(STATE, state)
        progress(state)
        print(json.dumps({'event': 'pass_finished', **entry}), flush=True)
        if state['status'] in ['review_required', 'blocked']:
            break
    else:
        state.update(status='pass_limit_reached', reason='32_passes_exhausted_no_automatic_extension')
    if state['status'] == 'between_passes' and state['passes_started'] >= 32:
        state.update(status='pass_limit_reached')
    save(STATE, state)
    progress(state)
    print(json.dumps({'event': 'runner_stopped', 'status': state['status'], 'passes': state['passes_started'], 'tasks_complete': sum(tasks().values())}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        print(json.dumps({'branch_ok': branch() == EXPECTED_BRANCH, 'tasks_complete': sum(tasks().values()),
                          'maximum_passes': control()['max_passes'], 'paid_generation': control()['paid_generation'],
                          'prompt_exists': (NOTES / 'PROMPT.md').is_file(), 'fresh_context': True}))
    else:
        run()
