import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import campaign as c
import run
from preflight import save


class RunTests(unittest.TestCase):
    def config(self):
        return {'account':'123456789012','region':'us-east-2','stage':1,'zone':'us-east-2a','instance_type':'m7i-flex.large',
            'ami':'ami-abcdef01234567890','operator_cidr':'8.8.8.8/32','source_sha':'a'*40,
            'readiness_sha256':'b'*64,'pricing_sha256':'c'*64,'baseline_ids':['vpc-00000000000000000'],
            'compute_usd_hour':'0.1008','ipv4_usd_hour':'0.005','gp3_usd_gb_month':'0.08','egress_usd_gb':'0.09'}

    def test_prepare_is_private_reserved_and_never_invokes_aws(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()/'campaign'
            with patch.object(run.subprocess,'run') as proc:
                def keygen(argv,**kwargs):
                    self.assertEqual(argv[0],'ssh-keygen')
                    key=Path(argv[-1]);save(key,{});key.with_name(key.name+'.pub').write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBogus fixture')
                proc.side_effect=keygen
                result=run.plan(self.config(),root)
            self.assertFalse(result['activation_performed'])
            self.assertEqual(result['reserved'],{'aws':'2','external':'1'})
            _,packet,actions=run.load(root)
            self.assertEqual(actions[-1]['name'],'stop-schedule')
            state=c.read_private(root/'campaign.json')
            self.assertEqual(state['reservations'][packet['attempt_id']]['state'],'reserved')
            self.assertEqual((root/'packet.json').stat().st_mode & 0o777,0o600)
            with patch.object(run,'source_closure',return_value={'changed':'source'}):
                with self.assertRaises(ValueError):run.load(root)
                run.load(root,allow_source_change=True)

    def test_costs_and_lease_cannot_be_silently_expanded(self):
        for changes in ({'lease_seconds':21601},{'compute_usd_hour':'100'}):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve()/'campaign'
                with patch.object(run.subprocess,'run') as proc:
                    def keygen(argv,**kwargs):
                        key=Path(argv[-1]);save(key,{});key.with_name(key.name+'.pub').write_text('ssh-ed25519 AAAA fixture')
                    proc.side_effect=keygen
                    with self.assertRaises(ValueError):run.plan(dict(self.config(),**changes),root)

    def test_later_stage_requires_settled_accepted_predecessor(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory).resolve();ledger=base/'prior.json';state=c.new_campaign(self.config()['account'])
            save(ledger,state)
            with self.assertRaisesRegex(ValueError,'accepted_predecessor_required'):
                run.plan(dict(self.config(),stage=2,predecessor_ledger=str(ledger)),base/'refused')
            state['accepted_stage']=1;state['receipts']['1']={'stage':1,'accepted':True,'sha256':'d'*64};state['spent']['aws']='1.2'
            ledger.unlink();save(ledger,state)
            def keygen(argv,**kwargs):
                key=Path(argv[-1]);save(key,{});key.with_name(key.name+'.pub').write_text('ssh-ed25519 AAAA fixture')
            with patch.object(run.subprocess,'run',side_effect=keygen):
                run.plan(dict(self.config(),stage=2,predecessor_ledger=str(ledger)),base/'next')
            _,packet,_=run.load(base/'next')
            self.assertEqual(packet['stage'],2);self.assertEqual(packet['predecessor_sha256'],'d'*64)
            self.assertEqual(c.read_private(base/'next/campaign.json')['spent']['aws'],'1.2')


if __name__=='__main__':unittest.main()
