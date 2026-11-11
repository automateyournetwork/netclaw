"""R09A lab helper: call the public Border HUD owner API (open-lab) with the cluster pin headers. Stdlib only."""
import json, os, sys, urllib.request, urllib.error
R = os.path.expanduser(os.environ['R09A_RUN'])
s = json.load(open(R + '/summary.json'))
def call(code, route, method='GET', body=None):
    n = [x for x in s['nodes'] if x['code'] == code][0]
    h = {'Accept': 'application/json', 'X-NetClaw-Installation': n['installation_id'], 'X-NetClaw-Cluster-ID': s['cluster_id'],
         'X-NetClaw-Cluster-Generation': s['generation']}
    data = None
    if body is not None:
        h['Content-Type'] = 'application/json'; h['Origin'] = 'https://' + n['dns']; data = json.dumps(body).encode()
    elif method != 'GET':
        h['Origin'] = 'https://' + n['dns']; h['Content-Type'] = 'application/json'; data = b'{}'
    r = urllib.request.Request('https://' + n['dns'] + route, data=data, method=method, headers=h)
    try:
        resp = urllib.request.urlopen(r, timeout=60); return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try: return e.code, json.load(e)
        except Exception: return e.code, {}
if __name__ == '__main__':
    code, route = sys.argv[1], sys.argv[2]
    print(json.dumps(call(code, route), indent=1)[:3000])
