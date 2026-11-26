import copy
import unittest
import campaign as c
import cleanup
from test_campaign import packet,NOW


class CleanupTests(unittest.TestCase):
    def setup_case(self):
        state=c.new_campaign('123456789012');p=packet(state,run_id='nc199-abcdef012345')
        c.reserve(state,p,NOW)
        record={'account':p['account'],'region':p['region'],'run_id':p['run_id'],'stage':1,
                'kind':'instance','id':'i-abcdef01234567890','create_request_sha256':'a'*64}
        observed=dict(record,query_succeeded=True,observed_at=NOW,
            tags={'netclaw-spec':'199','netclaw-run':p['run_id'],'netclaw-stage':'1'})
        entry=state['reservations'][p['attempt_id']]
        entry['custody']={record['id']:{'record':record,'record_sha256':c.digest(record),'dependents_recorded':True}}
        return state,p,record,observed

    def test_expired_or_unknown_create_never_blocks_evidence_first_cleanup(self):
        state,p,r,o=self.setup_case();state['reservations'][p['attempt_id']]['state']='unknown'
        later=NOW+100000;o['observed_at']=later
        a=cleanup.begin(state,p,r,o,{},'b'*64,later)
        self.assertEqual(a['request'],{'InstanceIds':[r['id']]})
        self.assertEqual(state['reservations'][p['attempt_id']]['state'],'unknown')

    def test_cleanup_needs_recorded_custody_fresh_owner_and_absent_dependents(self):
        for change in ('record','old','foreign','dependent'):
            state,p,r,o=self.setup_case()
            if change=='record':r['id']='i-00000000000000000'
            if change=='old':o['observed_at']=NOW-31
            if change=='foreign':o['tags']['netclaw-run']='another-run'
            if change=='dependent':
                r['depends_on_absence']=['volume'];state['reservations'][p['attempt_id']]['custody'][r['id']]['record_sha256']=c.digest(r)
            with self.assertRaises(ValueError):cleanup.begin(state,p,r,o,{},'b'*64,NOW)

    def test_unknown_cleanup_is_not_repeated(self):
        state,p,r,o=self.setup_case();a=cleanup.begin(state,p,r,o,{},'b'*64,NOW)
        cleanup.finish(state,p,a,error='TimeoutError')
        with self.assertRaisesRegex(ValueError,'already_sent'):cleanup.begin(state,p,r,o,{},'b'*64,NOW)

    def test_named_resource_recreation_and_attached_disks_refused(self):
        _,_,r,o=self.setup_case()
        for kind,extra in [('volume',{'state':'in-use','attachments':['i']}),
                           ('internet-gateway',{'attachments':['vpc']}),
                           ('role',{'name':'owned','created_at':'new'})]:
            record=dict(r,kind=kind,name='owned',created_at='old')
            with self.assertRaises(ValueError):cleanup.deletion(record,dict(o,**extra),NOW)

    def test_absence_does_not_clear_unknown_work_or_budget(self):
        state,p,r,o=self.setup_case();entry=state['reservations'][p['attempt_id']];entry['state']='unknown'
        rows=[{'observed_at':n,'resources':{r['id']:{'query_succeeded':True,'absent':True}}} for n in (NOW,NOW+3)]
        cleanup.confirm_absence(state,p,r,rows)
        self.assertEqual(entry['state'],'unknown');self.assertEqual(entry['custody'][r['id']]['disposition'],'absent')


if __name__=='__main__':unittest.main()
