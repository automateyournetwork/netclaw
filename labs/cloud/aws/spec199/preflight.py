#!/usr/bin/env python3
"""Spec199 read-only AWS observations. No apply, inferred permissions or secrets."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import subprocess

CANONICAL_OWNER = '099720109477'
PUBLIC_AMI = '/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id'
ALLOWED = {
    ('sts', 'get-caller-identity'), ('ec2', 'describe-instances'),
    ('ec2', 'describe-volumes'), ('ec2', 'describe-addresses'),
    ('ec2', 'describe-vpcs'), ('ec2', 'describe-subnets'),
    ('ec2', 'describe-nat-gateways'), ('ec2', 'describe-instance-types'),
    ('ec2', 'describe-instance-type-offerings'), ('ec2', 'describe-images'),
    ('ec2', 'describe-availability-zones'),
    ('service-quotas', 'get-service-quota'), ('ssm', 'get-parameter'),
    ('pricing', 'get-products'), ('freetier', 'get-account-plan-state'),
}


def cli(profile, region, args):
    if tuple(args[:2]) not in ALLOWED:
        raise ValueError('read_only_operation_required')
    env = dict(os.environ, AWS_PAGER='', AWS_MAX_ATTEMPTS='1')
    try:
        result = subprocess.run(
            ['aws', *args, '--profile', profile, '--region', region,
             '--output', 'json', '--no-cli-pager', '--cli-connect-timeout', '8',
             '--cli-read-timeout', '20'], capture_output=True, text=True,
            timeout=45, env=env, check=False)
        if result.returncode:
            match = re.search(r'\(([A-Za-z][A-Za-z0-9]+)\)', result.stderr)
            return {'ok': False, 'error': match.group(1) if match else 'cli_failed',
                    'detail': result.stderr[:8192]}
        return {'ok': True, 'data': json.loads(result.stdout)}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'error': type(exc).__name__}


def fresh_private_dir(path):
    path = Path(path).expanduser()
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ValueError('fresh_absolute_private_directory_required')
    parent = path.parent.resolve(strict=True)
    info = parent.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('private_owned_parent_required')
    repo = Path(__file__).resolve().parents[4]
    if parent == repo or repo in parent.parents:
        raise ValueError('evidence_must_be_outside_source')
    resolved = parent / path.name
    resolved.mkdir(mode=0o700)
    return resolved


def save(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def payload(results, key):
    row = results.get(key, {})
    return row.get('data', {}) if row.get('ok') else {}


def count(results, key, field):
    data = payload(results, key)
    return len(data[field]) if isinstance(data.get(field), list) else None


def compute_rates(data, region, instance_type):
    rates = set()
    for raw in data.get('PriceList', []):
        try:
            product = json.loads(raw) if isinstance(raw, str) else raw
            attributes = product['product']['attributes']
            expected = {'regionCode': region, 'instanceType': instance_type,
                        'operatingSystem': 'Linux', 'tenancy': 'Shared',
                        'preInstalledSw': 'NA', 'capacitystatus': 'Used'}
            if any(attributes.get(k) != v for k, v in expected.items()):
                continue
            for term in product.get('terms', {}).get('OnDemand', {}).values():
                for dimension in term.get('priceDimensions', {}).values():
                    rate = Decimal(dimension.get('pricePerUnit', {}).get('USD', 'NaN'))
                    if (dimension.get('unit') == 'Hrs' and rate.is_finite()
                            and rate > 0 and dimension.get('beginRange') == '0'):
                        rates.add(rate)
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
    return str(next(iter(rates))) if len(rates) == 1 else None


def summarize(results, region, instance_type, expected_account=None):
    identity = payload(results, 'identity')
    account = identity.get('Account')
    identity_ok = bool(re.fullmatch(r'\d{12}', account or ''))
    if expected_account is not None:
        identity_ok = identity_ok and account == expected_account
    quota = payload(results, 'quota').get('Quota', {}).get('Value')
    types = payload(results, 'types').get('InstanceTypes', [])
    selected = next((x for x in types if x.get('InstanceType') == instance_type), {})
    vcpu = selected.get('VCpuInfo', {}).get('DefaultVCpus')
    reservations = payload(results, 'instances').get('Reservations')
    instances = [i for row in reservations for i in row.get('Instances', [])] if isinstance(reservations, list) else None
    active = [x for x in instances if x.get('State', {}).get('Name') in ('running', 'pending')] if instances is not None else None
    used = (sum(vcpu for x in active) if isinstance(vcpu, int) and
            all(x.get('InstanceType') == instance_type for x in active) else None) if active is not None else None
    free = quota - used if isinstance(quota, (int, float)) and used is not None else None
    images = payload(results, 'image').get('Images', [])
    requested = payload(results, 'ami-parameter').get('Parameter', {}).get('Value')
    image_ok = len(images) == 1 and all((images[0].get(k) == v) for k, v in {
        'ImageId': requested, 'OwnerId': CANONICAL_OWNER, 'State': 'available',
        'Architecture': 'x86_64', 'RootDeviceType': 'ebs'}.items())
    offerings = [x['Location'] for x in payload(results, 'offerings').get('InstanceTypeOfferings', [])
                 if x.get('InstanceType') == instance_type and x.get('LocationType') == 'availability-zone']
    credits = payload(results, 'credits')
    core = ['identity', 'instances', 'volumes', 'addresses', 'vpcs', 'subnets',
            'nat', 'quota', 'types', 'offerings', 'ami-parameter', 'image']
    reasons = [key + ':' + results.get(key, {}).get('error', 'unknown')
               for key in core if not results.get(key, {}).get('ok')]
    if not identity_ok: reasons.append('account_unverified_or_mismatch')
    if not image_ok: reasons.append('image_not_verified')
    if free is None or not isinstance(vcpu, int) or free < vcpu: reasons.append('quota_headroom_unverified_or_insufficient')
    if not offerings: reasons.append('instance_offering_unverified')
    if credits.get('accountPlanType')=='FREE' and selected.get('FreeTierEligible') is not True:
        reasons.append('instance_not_eligible_for_free_account_plan')
    return {
        'schema': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
        'region': region, 'instance_type': instance_type,
        'account_verified': identity_ok, 'account_suffix': account[-4:] if identity_ok else None,
        'instances': len(instances) if instances is not None else None,
        'volumes': count(results, 'volumes', 'Volumes'),
        'addresses': count(results, 'addresses', 'Addresses'),
        'vpcs': count(results, 'vpcs', 'Vpcs'), 'subnets': count(results, 'subnets', 'Subnets'),
        'standard_vcpu_quota': quota, 'free_standard_vcpu': free,
        'instance_vcpu': vcpu, 'memory_mib': selected.get('MemoryInfo', {}).get('SizeInMiB'),
        'free_plan_instance_eligible': selected.get('FreeTierEligible'),
        'offered_zones': sorted(offerings), 'canonical_image_verified': image_ok,
        'ami_id': requested if image_ok else None,
        'compute_usd_hour': compute_rates(payload(results, 'price'), region, instance_type),
        'credit_observation': {k: credits[k] for k in ('accountPlanType', 'accountPlanStatus',
            'accountPlanRemainingCredits', 'accountPlanExpirationDate') if k in credits},
        'readiness': 'read_only_checks_pass' if not reasons else 'blocked_or_unknown',
        'reasons': reasons, 'activation_ready': False,
        'remaining_gates': ['complete_cost_packet', 'launch_and_cleanup_permissions',
                            'independent_deadline_guard', 'actual_capacity', 'host_and_runtime_qualification'],
    }


def collect(profile, region, instance_type, invoke=cli, expected_account=None):
    checks = {
        'identity': ['sts', 'get-caller-identity'],
        'instances': ['ec2', 'describe-instances'], 'volumes': ['ec2', 'describe-volumes'],
        'addresses': ['ec2', 'describe-addresses'], 'vpcs': ['ec2', 'describe-vpcs'],
        'subnets': ['ec2', 'describe-subnets'], 'nat': ['ec2', 'describe-nat-gateways'],
        'quota': ['service-quotas', 'get-service-quota', '--service-code', 'ec2', '--quota-code', 'L-1216C47A'],
        'types': ['ec2', 'describe-instance-types', '--instance-types', instance_type],
        'zones': ['ec2', 'describe-availability-zones'],
        'offerings': ['ec2', 'describe-instance-type-offerings', '--location-type', 'availability-zone',
                      '--filters', 'Name=instance-type,Values=' + instance_type],
        'ami-parameter': ['ssm', 'get-parameter', '--name', PUBLIC_AMI],
    }
    results = {k: invoke(profile, region, args) for k, args in checks.items()}
    ami = payload(results, 'ami-parameter').get('Parameter', {}).get('Value')
    if isinstance(ami, str) and re.fullmatch(r'ami-[0-9a-f]{8,17}', ami):
        results['image'] = invoke(profile, region, ['ec2', 'describe-images', '--image-ids', ami])
    price_args = ['pricing', 'get-products', '--service-code', 'AmazonEC2', '--filters']
    for field, value in {'instanceType': instance_type, 'regionCode': region, 'operatingSystem': 'Linux',
                         'tenancy': 'Shared', 'preInstalledSw': 'NA', 'capacitystatus': 'Used'}.items():
        price_args.append(f'Type=TERM_MATCH,Field={field},Value={value}')
    results['price'] = invoke(profile, 'us-east-1', price_args)
    results['credits'] = invoke(profile, 'us-east-1', ['freetier', 'get-account-plan-state'])
    return results, summarize(results, region, instance_type, expected_account)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--instance-type', default='m7i.large')
    parser.add_argument('--expected-account')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d', args.region): parser.error('invalid region')
    if not re.fullmatch(r'[a-z][a-z0-9-]*\.[a-z0-9]+', args.instance_type): parser.error('invalid instance type')
    if args.expected_account and not re.fullmatch(r'\d{12}', args.expected_account): parser.error('invalid expected account')
    out = fresh_private_dir(args.out)
    results, summary = collect(args.profile, args.region, args.instance_type, expected_account=args.expected_account)
    save(out / 'raw.json', results)
    save(out / 'summary.json', summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary['readiness'] == 'read_only_checks_pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
