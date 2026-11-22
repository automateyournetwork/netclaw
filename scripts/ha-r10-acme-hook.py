#!/usr/bin/env python3
"""Exact-name R10 DNS-01 hook; GoDaddy PAT stays in process memory, never argv."""
import json
import os
import sys
import urllib.request

action, fqdn = sys.argv[1], sys.argv[2].rstrip('.')
value = sys.argv[-1]
names = os.environ.get('R10_DNS_NAMES', '').split(',')
if not fqdn.startswith('_acme-challenge.') or fqdn.removeprefix('_acme-challenge.') not in names:
    raise SystemExit('refused: challenge outside this run')
zone = 'automateyournetwork.com'
name = fqdn.removesuffix('.' + zone)
url = 'https://api.godaddy.com/v1/domains/' + zone + '/records/TXT/' + name
headers = {'Authorization': 'Bearer ' + os.environ['GODADDY_PAT'], 'Content-Type': 'application/json'}
if action == 'present':
    req = urllib.request.Request(url, method='PUT', headers=headers,
        data=json.dumps([{'data': value, 'ttl': 600}]).encode())
elif action == 'cleanup':
    req = urllib.request.Request(url, method='DELETE', headers=headers)
else:
    raise SystemExit('unsupported challenge action')
try:
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status not in (200, 201, 204): raise SystemExit('DNS challenge update failed')
except urllib.error.HTTPError as error:
    if not (action == 'cleanup' and error.code == 404):
        raise SystemExit('DNS challenge HTTP ' + str(error.code))
