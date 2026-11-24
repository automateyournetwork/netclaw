"""One foreground, fresh-context world pass at a time; new campaign, no paid logic."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / 'specs/200-genie-network-worlds/world-suite'
PRIVATE = ROOT / '.spec200-local/world-suite'
CONTROL = PRIVATE / 'control.json'
STATE = PRIVATE / 'state.json'


def stamp(): return datetime.now(timezone.utc).isoformat()


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2)+'\n'); temp.chmod(0o600); temp.replace(path)


def preflight():
    ctl = json.loads(CONTROL.read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else dict(schema=1, passes_started=0, history=[], status='foundation_first')
    branch = subprocess.check_output(['git','branch','--show-current'], cwd=ROOT, text=True).strip()
    number = state['passes_started']+1; world = (number-1)//10+1
    gates = []
    if branch != '200-genie-network-worlds': gates.append('branch_mismatch')
    if ctl.get('schema') != 1 or ctl.get('max_passes') != 50 or ctl.get('passes_per_world') != 10: gates.append('invalid_campaign')
    source_mode = ctl.get('phase') == 'source_refinement'
    if ctl.get('phase') not in ('world_refinement', 'source_refinement') or ctl.get('loops_may_start') is not True: gates.append('foundation_not_released')
    if source_mode:
        if ctl.get('source_foundation_ready') is not True: gates.append('source_foundation_evidence_incomplete')
    elif ctl.get('foundation_ready') is not True: gates.append('foundation_evidence_incomplete')
    if ctl.get('stop_requested'): gates.append('owner_stop')
    if state.get('status') in ('running', 'review_required', 'blocked'): gates.append('previous_pass_requires_review')
    if number > 50: gates.append('50_pass_cap')
    if not source_mode and world >= 3 and ctl.get('first_two_live_accepted') is not True: gates.append('first_two_actual_worlds_required')
    return ctl, state, dict(ready=not gates, gates=gates, next_pass=number, world=world, maximum=50, fresh_context=True, paid_calls_by_runner=0, execution_mode=ctl.get('phase'))


def progress(state):
    rows = ['# Google world refinement progress', '', f"Status: **{state['status']}** · {state['passes_started']}/50 passes started; {len(state['history'])} finished.", '',
            'Ten passes per world. Each uses a new ephemeral context. Counts do not establish generated-world acceptance.', '',
            '| Pass | World | Outcome | Note |', '| --- | --- | --- | --- |']
    for item in state['history']:
        n=item['pass']; rows.append(f"| {n:02} | {item['world']} | {item['outcome']} | [pass-{n:02}.md](pass-{n:02}.md) |")
    (NOTES/'PROGRESS.md').write_text('\n'.join(rows)+'\n')


def run_next():
    os.umask(0o077)
    with (PRIVATE/'runner.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ctl, state, ready = preflight()
        if not ready['ready']:
            print(json.dumps(ready)); return 2
        number, world = ready['next_pass'], ready['world']
        authority_hash = hashlib.sha256(CONTROL.read_bytes()).hexdigest()
        state.update(status='running', passes_started=number, active_started_at=stamp(), runner_pid=os.getpid())
        save(STATE,state); progress(state)
        prefix=PRIVATE/f'pass-{number:02}'; result=prefix.with_suffix('.result.json')
        args=['/opt/homebrew/bin/codex','exec','--ephemeral','--json','--color','never','-C',str(ROOT),
              '-s','danger-full-access','-c','approval_policy="never"','--output-schema',str(NOTES/'result.schema.json'),
              '--output-last-message',str(result),'-']
        env=dict(os.environ)
        for key in list(env):
            if key.startswith(('GEMINI_','GOOGLE_','PYATS_','CML_','NETCLAW_GENIE_')): env.pop(key)
        env.update(SPEC200_WORLD_PASS=f'{number:02}', SPEC200_WORLD_NUMBER=str(world),
                   SPEC200_EXECUTION_MODE=ctl['phase'],
                   NETCLAW_TEST_TMP=str(ROOT/'.spec200-local/tests'), PYTHONDONTWRITEBYTECODE='1')
        interrupted=False
        with prefix.with_suffix('.events.jsonl').open('wb') as out, prefix.with_suffix('.stderr.log').open('wb') as err:
            child=subprocess.Popen(args, cwd=ROOT, stdin=subprocess.PIPE, stdout=out, stderr=err, env=env, start_new_session=True)
            state['child_pid']=child.pid; save(STATE,state)
            child.stdin.write((NOTES/'PROMPT.md').read_bytes()); child.stdin.close()
            print(json.dumps(dict(event='pass_started', pass_number=number, world=world, at=stamp())),flush=True)
            deadline=time.monotonic()+900
            try:
                while child.poll() is None:
                    current=json.loads(CONTROL.read_text())
                    if current.get('stop_requested') or time.monotonic()>deadline:
                        interrupted=True; break
                    time.sleep(1)
            except (KeyboardInterrupt, Exception): interrupted=True
            finally:
                if child.poll() is None:
                    os.killpg(child.pid,signal.SIGTERM)
                    try: child.wait(timeout=10)
                    except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); child.wait()
        thread=None
        for line in prefix.with_suffix('.events.jsonl').read_text(errors='replace').splitlines():
            try:
                event=json.loads(line)
                if event.get('type')=='thread.started': thread=event.get('thread_id'); break
            except ValueError: pass
        try: report=json.loads(result.read_text())
        except (OSError,ValueError): report={}
        note=NOTES/f'pass-{number:02}.md'
        reason=None
        if interrupted or child.returncode: reason='interrupted_or_failed'
        elif report.get('status') not in ('progress','review','blocked'): reason='invalid_result'
        elif not note.exists(): reason='handoff_missing'
        elif not thread or any(h.get('thread_id')==thread for h in state['history']): reason='fresh_context_unproven'
        elif hashlib.sha256(CONTROL.read_bytes()).hexdigest()!=authority_hash: reason='authority_changed_during_pass'
        item=dict(pass_number=number, world=world, outcome=reason or report['status'], thread_id=thread, at=stamp())
        item['pass']=item.pop('pass_number'); state['history'].append(item); state['child_pid']=None
        state['status']='review_required' if reason or report.get('status') in ('review','blocked') else 'between_passes'
        if number==50 and not reason: state['status']='pass_cap_reached'
        save(STATE,state); progress(state)
        print(json.dumps(dict(event='pass_finished', **item, summary=report.get('summary'), next_step=report.get('next_step'))),flush=True)
        return 1 if reason else 0


def run_campaign():
    """Sequential fresh contexts; stop on a failed/review pass or any admission gate."""
    with (PRIVATE/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            _, state, ready = preflight()
            if not ready['ready']:
                print(json.dumps(dict(event='campaign_stopped', **ready)), flush=True)
                return 0 if state.get('status') == 'pass_cap_reached' else 2
            result = run_next()
            if result: return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true'); group.add_argument('--next',action='store_true')
    group.add_argument('--run',action='store_true',help='Continue sequentially up to 50 passes, stopping for review/failure/owner stop')
    args=parser.parse_args()
    if args.check: print(json.dumps(preflight()[2],indent=2))
    else: raise SystemExit(run_campaign() if args.run else run_next())
