#!/usr/bin/env python3
"""New finite local guard for one exact final-stage packet. Never restarts work."""
import argparse
import os
from pathlib import Path
import time
import campaign as c
import external as e
from preflight import save


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args()
    root=c.owned_directory(Path(a.root));packet=c.read_private(root/'packet.json');plan=c.read_private(root/'external-plan.json')
    c.need(packet['stage']==5 and c.digest(plan)==packet['external_plan_sha256'],'frozen_final_packet_required')
    deadline=c.stamp(packet['deadline']);c.need(time.time()<deadline,'expired_guard_cannot_restart')
    save(root/'external-guard-started.json',dict(packet_sha256=c.digest(packet),deadline=packet['deadline'],at=time.time()))
    while time.time()<deadline:
        heartbeat=root/('guard-heartbeat-'+str(os.getpid())+'.json')
        save(heartbeat,dict(pid=os.getpid(),packet_sha256=c.digest(packet),at=time.time()))
        os.replace(heartbeat,root/'external-guard-live.json')
        state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
        vms=[r for r in entry.get('external_custody',{}).values() if r['record']['kind']=='vm']
        if len(vms)==6 and all(r.get('disposition')=='absent' for r in vms):
            save(root/'external-guard-complete.json',{'all_six_vms_absent':True,'at':time.time()});return
        time.sleep(min(5,max(0,deadline-time.time())))
    api=e.API();results={};absent_samples={};resolved=set();attempted=set()
    # Reconcile original frozen slots for ten bounded minutes. An unknown create
    # that still reads404 remains an obligation; it is never treated as retired.
    until=deadline+600
    while time.time()<until:
        state=c.read_private(root/'campaign.json');entry=state['reservations'][packet['attempt_id']]
        slots=[a for a in plan['actions'] if a['kind']=='vm' and a['name'] in entry.get('external_actions',{})]
        for action in slots:
            if action['id'] in resolved:continue
            try:
                obs=api.observe(action)
                if obs['absent']:
                    samples=absent_samples.setdefault(action['id'],[]);samples.append(obs['observed_at'])
                    original=entry['external_actions'][action['name']]
                    if original['state'] in ('observed','rejected') and len(samples)>1 and samples[-1]-samples[-2]>=2:
                        results[action['id']]=dict(repeated_absence=True,known_terminal_creation=True);resolved.add(action['id'])
                    else:results[action['id']]=dict(absence_unresolved=True,creation_state=original['state'])
                    continue
                absent_samples.pop(action['id'],None)
                rec=e.adopt_for_guard(root,packet,plan,action,obs)
                stopped=e.stopped_observation(root,packet,plan,rec,api)
                if stopped.get('stopped'):
                    results[action['id']]=stopped;resolved.add(action['id']);continue
                intent=root/('guard-stop-'+c.digest(rec)[:24]+'.intent.json')
                if action['id'] not in attempted and not intent.exists():
                    attempted.add(action['id']);e.stop_once(root,packet,plan,rec,obs,api)
                results[action['id']]=dict(stop_sent=True,completion_unverified=True)
            except Exception as exc:results[action['id']]=dict(error_class=type(exc).__name__,uncertainty_retained=True)
        if len(resolved)==len(slots):break
        time.sleep(min(5,max(0,until-time.time())))
    save(root/'external-guard-expired.json',dict(results=results,at=time.time(),restart_forbidden=True,
        all_slots_accounted_for=len(resolved)==len(slots),unresolved=[a['id'] for a in slots if a['id'] not in resolved]))

if __name__=='__main__':main()
