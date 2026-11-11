"""R09A lab driver: prepare, approve and reconcile one catalog operation through a Border (usage: R09A_RUN=<run dir> r09a_run_operation.py nne1 out.json)."""
import json, os, sys, time, uuid
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from labs.ha.r09a_hudcall import call
code = sys.argv[1]
st, cat = call(code, '/api/hud/operations/catalog')
row = cat['members'][0]; tool = row['tools'][0]; model = row['model_profiles'][0]
body = {'client_nonce': str(uuid.uuid4()), 'catalog_revision': cat['revision'], 'member_id': row['member']['member_id'],
        'model_profile_id': model['profile_id'], 'tool': tool['tool'], 'arguments': tool['arguments']}
st, op = call(code, '/api/hud/operations', 'POST', body)
print('prepare', st, op.get('state'), op.get('operation_id'))
if st >= 300: print(json.dumps(op)[:600]); sys.exit(1)
rv = op['review']; print('review', json.dumps({k: rv.get(k) for k in ('member', 'tool_call', 'limits')})[:500])
st, d = call(code, '/api/hud/operations/%s/decision' % op['operation_id'], 'POST',
             {'revision': op['revision'], 'review_digest': op['review_digest'], 'decision': 'approve'})
print('decision', st, d.get('state'))
end = time.time() + 150; last = None
while time.time() < end:
    st, cur = call(code, '/api/hud/operations/' + op['operation_id'])
    if cur.get('state') != last: last = cur.get('state'); print(time.strftime('%T'), st, last, flush=True)
    if last == 'member_admitted': call(code, '/api/hud/operations/%s/reconcile' % op['operation_id'], 'POST')
    if last in ('completed', 'refused', 'failed', 'denied', 'revoked', 'unknown'): break
    time.sleep(2)
json.dump({'entered_via': code, 'operation': cur}, open(sys.argv[2], 'w'), indent=1); print('FINAL', cur.get('state'), (cur.get('result') or {}).get('durable_ack'))
