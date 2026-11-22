#!/usr/bin/env python3.10
"""Spec 198 preflight: read-only Azure go/no-go. Stdlib only; shells out to `az` for queries only.

Never creates a resource and never prints a secret value (presence booleans only).
usage: r10_preflight.py [--json] [--regions canadacentral,westeurope,southeastasia]
Exit 0 only when the subscription is Enabled and every region is `go`.
"""
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request

REGIONS = ('canadacentral', 'eastus2', 'swedencentral')
FULL_BORDER_IMAGE = 'Canonical:ubuntu-24_04-lts:server:latest'
SIZES = ('Standard_D2as_v7', 'Standard_D2als_v7', 'Standard_B2s', 'Standard_B2ls_v2', 'Standard_B2als_v2')
VCPUS_PER_VM = 2
FAMILY = {'Standard_D2als_v7': 'StandardDalsv7Family', 'Standard_B2s': 'standardBSFamily', 'Standard_B2ls_v2': 'standardBsv2Family', 'Standard_B2als_v2': 'standardBasv2Family'}
SECRET_KEYS = {'godaddy': 'GODADDY_PAT', 'anthropic': 'ANTHROPIC_API_KEY', 'netbox': 'NETBOX_TOKEN'}


def az(*args):
    """Read-only az query; returns parsed JSON or None on any failure."""
    try:
        r = subprocess.run(('az',) + args + ('-o', 'json'), capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def sku_verdict(skus, size):
    """skus: `az vm list-skus --size <size>` output. Returns (usable, family, reason)."""
    for s in skus or []:
        if s.get('name') != size:
            continue
        blocked = [r for r in s.get('restrictions') or [] if r.get('type') == 'Location']
        if blocked:
            return False, s.get('family'), f'{size} restricted in this region ({blocked[0].get("reasonCode", "restricted")})'
        return True, s.get('family'), 'ok'
    return False, None, f'{size} not offered'


def quota_free(usage, family):
    """usage: `az vm list-usage` output. Returns min free vCPUs across regional total and the size family."""
    free = {}
    for u in usage or []:
        n = ((u.get('name') or {}).get('value') or '').lower()
        if n == 'cores' or (family and n == family.lower()):
            free[n] = int(u['limit']) - int(u['currentValue'])
    required = {'cores'} | ({family.lower()} if family else set())
    return min(free.values()) if required <= free.keys() else None


def region_report(region, skus_by_size, usage, sizes=SIZES):
    reasons = []
    for size in sizes:
        ok, family, why = sku_verdict(skus_by_size.get(size), size)
        if not ok:
            reasons.append(why); continue
        free = quota_free(usage, family) if family else None
        if free is None:
            reasons.append(f'{size}: quota unreadable'); continue
        if free < VCPUS_PER_VM:
            reasons.append(f'{size}: only {free} vCPU free, need {VCPUS_PER_VM}'); continue
        return {'region': region, 'size': size, 'available': True, 'quota_free_vcpus': free, 'verdict': 'go', 'reason': 'ok', 'substitute': None}
    return {'region': region, 'size': None, 'available': False, 'quota_free_vcpus': quota_free(usage, None), 'verdict': 'blocked',
            'reason': '; '.join(reasons), 'substitute': None}


def secrets_present(env_path):
    """Presence booleans only. env_path may be one path or several (a secret counts if any file holds a non-empty value)."""
    paths = [env_path] if isinstance(env_path, (str, os.PathLike)) else list(env_path)
    present = {k: False for k in SECRET_KEYS}
    for path in paths:
        try:
            for line in open(path, encoding='utf-8'):
                m = re.match(r'^\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*?)\s*$', line)
                if m:
                    for k, name in SECRET_KEYS.items():
                        if m.group(1) == name and m.group(2).strip('"\''):
                            present[k] = True
        except OSError:
            pass
    return present


def build(regions, account, per_region, budgets, secrets, sizes=SIZES):
    state = (account or {}).get('state', 'unknown')
    rep = {'subscription_state': state, 'regions': [region_report(r, *per_region[r], sizes=sizes) for r in regions],
           'budget_alert': ('present' if budgets else 'missing') if budgets is not None else 'unknown', 'secrets_present': secrets}
    if state != 'Enabled':
        for r in rep['regions']:
            r['reason'] = f'subscription state is {state}, not Enabled'
    rep['go'] = state == 'Enabled' and all(r['verdict'] == 'go' for r in rep['regions'])
    return rep


def resource_skus(subscription, region):
    """Server-filtered SKU API, including unavailable sizes. Never synthesize restrictions."""
    query = urllib.parse.urlencode({'$filter': "location eq '%s'" % region})
    url = f'https://management.azure.com/subscriptions/{subscription}/providers/Microsoft.Compute/skus?api-version=2021-07-01&{query}'
    rows, seen = [], set()
    for _ in range(20):
        if url in seen or not url.startswith('https://management.azure.com/'):
            return None
        seen.add(url)
        page = az('rest', '--method', 'get', '--url', url)
        if not isinstance(page, dict) or not isinstance(page.get('value'), list):
            return None
        rows.extend(page['value'])
        url = page.get('nextLink')
        if not url:
            return [s for s in rows if s.get('resourceType') == 'virtualMachines']
    return None


def compute_price(region, size):
    query = urllib.parse.urlencode({'currencyCode': 'USD', '$filter':
        f"armRegionName eq '{region}' and armSkuName eq '{size}' and priceType eq 'Consumption'"})
    try:
        with urllib.request.urlopen('https://prices.azure.com/api/retail/prices?' + query, timeout=30) as response:
            data = json.load(response)
        rows = [x for x in data.get('Items', []) if x.get('armSkuName') == size
                and x.get('armRegionName') == region and x.get('currencyCode') == 'USD'
                and x.get('unitOfMeasure') == '1 Hour' and x.get('isPrimaryMeterRegion')
                and not any(word in (x.get('skuName', '') + x.get('productName', '')).lower()
                            for word in ('windows', 'spot', 'low priority'))]
        return max(float(x['retailPrice']) for x in rows) if rows and not data.get('NextPageLink') else None
    except (OSError, ValueError, KeyError):
        return None


def validate_probe(region, size, group, public_key, image=FULL_BORDER_IMAGE, disk_gb=40):
    """ARM validation only. Existing explicit group; no resource or SSH key creation."""
    if not group or not public_key or not os.path.isfile(public_key):
        return {'passed': False, 'reason': 'validation group and existing SSH public key required'}
    result = az('vm', 'create', '-g', group, '-n', 'nc198-validation-only', '-l', region,
                '--size', size, '--image', image,
                '--admin-username', 'ncadmin', '--ssh-key-values', public_key,
                '--authentication-type', 'ssh', '--os-disk-size-gb', str(disk_gb),
                '--storage-sku', 'StandardSSD_LRS', '--nsg-rule', 'NONE', '--validate')
    props = (result or {}).get('properties') or {}
    return {'passed': props.get('provisioningState') == 'Succeeded' and not (result or {}).get('error'),
            'correlation_id': props.get('correlationId'), 'timestamp': props.get('timestamp'),
            'reason': 'succeeded' if props.get('provisioningState') == 'Succeeded' else 'ARM validation failed; inspect Azure activity log'}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--regions', default=','.join(REGIONS))
    ap.add_argument('--env', action='append', default=None, help='env file to inspect (repeatable); default: ~/.openclaw/.env and the repo .env')
    ap.add_argument('--size', help='exact intended size; no silent fallback')
    ap.add_argument('--image', default=FULL_BORDER_IMAGE)
    ap.add_argument('--disk-gb', type=int, default=40)
    ap.add_argument('--probe', action='store_true', help='validate template without deploying')
    ap.add_argument('--validation-group', help='existing resource group used only as validation context')
    ap.add_argument('--ssh-public-key', default=os.path.expanduser('~/.ssh/nc198_azure.pub'))
    a = ap.parse_args(argv)
    regions = a.regions.split(',')
    if any(not re.fullmatch('[a-z0-9]+', r) for r in regions):
        ap.error('invalid region name')
    sizes = (a.size,) if a.size else SIZES
    if any(not re.fullmatch('Standard_[A-Za-z0-9_-]+', s) for s in sizes):
        ap.error('invalid VM size')
    account = az('account', 'show')
    per_region = {}
    if (account or {}).get('state') == 'Enabled':
        for r in regions:
            skus = resource_skus(account['id'], r)
            per_region[r] = ({s: [x for x in skus or [] if x.get('name') == s] for s in sizes},
                             az('vm', 'list-usage', '-l', r))
    else:
        per_region = {r: ({}, None) for r in regions}
    budgets = az('consumption', 'budget', 'list')
    rep = build(regions, account, per_region, budgets, secrets_present(a.env or [os.path.expanduser('~/.openclaw/.env'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')]), sizes=sizes)
    for row in rep['regions']:
        row['validated'] = False
        if row['verdict'] == 'go' and rep['subscription_state'] == 'Enabled':
            row['compute_usd_per_hour'] = compute_price(row['region'], row['size'])
            if a.probe:
                row['validation'] = validate_probe(row['region'], row['size'], a.validation_group, a.ssh_public_key,
                                                   image=a.image, disk_gb=a.disk_gb)
                row['validated'] = row['validation']['passed']
                if not row['validated']:
                    row.update(verdict='blocked', reason=row['validation']['reason'])
    rep['go'] = rep['go'] and all(r['verdict'] == 'go' for r in rep['regions'])
    rep['deployment_go'] = rep['go'] and all(r['validated'] and r.get('compute_usd_per_hour') is not None for r in rep['regions'])
    rep['validation_only'] = bool(a.probe)
    rep['image'] = a.image
    rep['disk_gb'] = a.disk_gb
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print(f'subscription: {rep["subscription_state"]}')
        for r in rep['regions']:
            print(f'  {r["region"]}: {r["verdict"]} {r["size"] or ""} {"" if r["verdict"] == "go" else r["reason"]}')
        print(f'budget alert: {rep["budget_alert"]}   secrets present: {rep["secrets_present"]}')
        print('GO' if rep['go'] else 'NO-GO')
    return 0 if (rep['deployment_go'] if a.probe else rep['go']) else 1


if __name__ == '__main__':
    sys.exit(main())
