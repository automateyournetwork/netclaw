import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import preflight as p


def fixture():
    data = {'identity': {'Account': '123456789012'}, 'instances': {'Reservations': []},
            'volumes': {'Volumes': []}, 'addresses': {'Addresses': []},
            'vpcs': {'Vpcs': [{}]}, 'subnets': {'Subnets': [{}, {}, {}]}, 'nat': {'NatGateways': []},
            'quota': {'Quota': {'Value': 8}}, 'types': {'InstanceTypes': [{'InstanceType': 'm7i.large',
                'VCpuInfo': {'DefaultVCpus': 2}, 'MemoryInfo': {'SizeInMiB': 8192}}]},
            'offerings': {'InstanceTypeOfferings': [{'InstanceType': 'm7i.large', 'LocationType': 'availability-zone', 'Location': 'us-east-2a'}]},
            'ami-parameter': {'Parameter': {'Value': 'ami-abcdef01234567890'}},
            'image': {'Images': [{'ImageId': 'ami-abcdef01234567890', 'OwnerId': p.CANONICAL_OWNER,
                'State': 'available', 'Architecture': 'x86_64', 'RootDeviceType': 'ebs'}]}}
    return {k: {'ok': True, 'data': v} for k, v in data.items()}


class PreflightTests(unittest.TestCase):
    def test_pass_is_never_activation_authority(self):
        result = p.summarize(fixture(), 'us-east-2', 'm7i.large')
        self.assertEqual(result['readiness'], 'read_only_checks_pass')
        self.assertFalse(result['activation_ready'])
        self.assertEqual(result['free_standard_vcpu'], 8)
        self.assertNotIn('123456789012', json.dumps(result))

    def test_denial_is_not_empty(self):
        data = fixture(); data['volumes'] = {'ok': False, 'error': 'UnauthorizedOperation', 'detail': 'secret'}
        result = p.summarize(data, 'us-east-2', 'm7i.large')
        self.assertIsNone(result['volumes'])
        self.assertEqual(result['readiness'], 'blocked_or_unknown')
        self.assertNotIn('secret', json.dumps(result))

    def test_account_mismatch(self):
        self.assertFalse(p.summarize(fixture(), 'us-east-2', 'm7i.large', '000000000000')['account_verified'])

    def test_free_account_credit_does_not_authorize_ineligible_type(self):
        data=fixture();data['credits']={'ok':True,'data':{'accountPlanType':'FREE','accountPlanRemainingCredits':{'amount':100,'unit':'USD'}}}
        self.assertIn('instance_not_eligible_for_free_account_plan',p.summarize(data,'us-east-2','m7i.large')['reasons'])
        data['types']['data']['InstanceTypes'][0]['FreeTierEligible']=True
        self.assertEqual(p.summarize(data,'us-east-2','m7i.large')['readiness'],'read_only_checks_pass')

    def test_unknown_existing_type_never_zero_usage(self):
        data = fixture(); data['instances']['data']['Reservations'] = [{'Instances': [
            {'InstanceType': 'm6i.large', 'State': {'Name': 'running'}}]}]
        result = p.summarize(data, 'us-east-2', 'm7i.large')
        self.assertIsNone(result['free_standard_vcpu'])
        self.assertEqual(result['readiness'], 'blocked_or_unknown')

    def test_quota_accounts_for_running_and_pending(self):
        data = fixture(); data['quota']['data']['Quota']['Value'] = 4
        data['instances']['data']['Reservations'] = [{'Instances': [
            {'InstanceType': 'm7i.large', 'State': {'Name': state}} for state in ('running', 'pending')]}]
        self.assertEqual(p.summarize(data, 'us-east-2', 'm7i.large')['free_standard_vcpu'], 0)

    def test_image_substitution_refused(self):
        for field, value in [('OwnerId', '000000000000'), ('Architecture', 'arm64'), ('State', 'pending'), ('ImageId', 'ami-deadbeef')]:
            data = fixture(); data['image']['data']['Images'][0][field] = value
            self.assertFalse(p.summarize(data, 'us-east-2', 'm7i.large')['canonical_image_verified'])

    def test_cli_write_unreachable(self):
        with patch.object(p.subprocess, 'run') as run:
            with self.assertRaises(ValueError): p.cli('test', 'us-east-2', ['ec2', 'run-instances'])
            run.assert_not_called()

    def test_private_output_refuses_overwrite_symlink_and_public_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = p.fresh_private_dir(root / 'evidence')
            p.save(path / 'data.json', {'test': True})
            self.assertEqual((path / 'data.json').stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError): p.save(path / 'data.json', {})
            (root / 'link').symlink_to(path, target_is_directory=True)
            with self.assertRaises(ValueError): p.fresh_private_dir(root / 'link')
            root.chmod(0o755)
            with self.assertRaises(ValueError): p.fresh_private_dir(root / 'public')

    def test_price_must_match_exact_product_not_reserved(self):
        attributes = dict(regionCode='us-east-2', instanceType='m7i.large', operatingSystem='Linux', tenancy='Shared', preInstalledSw='NA', capacitystatus='Used')
        product = {'product': {'attributes': attributes}, 'terms': {'OnDemand': {'term': {'priceDimensions': {
            'hour': {'unit': 'Hrs', 'beginRange': '0', 'pricePerUnit': {'USD': '0.1008'}}}}}}}
        self.assertEqual(p.compute_rates({'PriceList': [json.dumps(product)]}, 'us-east-2', 'm7i.large'), '0.1008')
        self.assertIsNone(p.compute_rates({'PriceList': [json.dumps(product)]}, 'us-west-2', 'm7i.large'))
        product['terms']['Reserved'] = product['terms'].pop('OnDemand')
        self.assertIsNone(p.compute_rates({'PriceList': [json.dumps(product)]}, 'us-east-2', 'm7i.large'))


if __name__ == '__main__': unittest.main()
