"""Thermidor-derived arithmetic boundaries; actual isolated native MCP, no model/cloud."""
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest
from bgp.federation import protected_calculator as calc
from bgp.federation import protected_contract as contract

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('subnet_patch_176',ROOT/'scripts/apply-subnet-summary.py')
patcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(patcher)
PATCH=(ROOT/'scripts/patches/subnet-calculator-bounded.patch').read_bytes()
# Full single-file patch preserves an independently hash-pinned original fixture.
ORIGINAL=b''.join(line[1:] for line in PATCH.splitlines(keepends=True)[3:] if line[:1] in (b'-',b' '))


def source(tmp_path):
    root=tmp_path/'native';(root/'servers').mkdir(parents=True)
    (root/'servers/subnetcalculator_mcp.py').write_bytes(ORIGINAL)
    assert hashlib.sha256(ORIGINAL).hexdigest()==patcher.BEFORE
    assert patcher.AFTER==calc.SUMMARY_SOURCE_SHA256
    assert patcher.apply(root)['changed']
    return root


def test_patch_is_exact_idempotent_and_refuses_changed_source(tmp_path):
    root=source(tmp_path)
    assert patcher.apply(root)=={'changed':False,'source_sha256':patcher.AFTER}
    target=root/'servers/subnetcalculator_mcp.py';target.write_bytes(target.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='native_source_revision_unqualified'):patcher.apply(root)
    assert target.read_bytes().endswith(b'\n\n')


@pytest.mark.parametrize('tool,args',[
    ('subnet_calculator',{'cidr':'192.0.2.1/24'}),
    ('subnet_calculator',{'cidr':'::/0'}),
    ('subnet_calculator_v6',{'cidr':'::ffff:c000:200/120'}),
    ('subnet_calculator_v6',{'cidr':'2001:DB8::/32'}),
    ('subnet_calculator_v6',{'cidr':'::/0','url':'https://invalid'}),
    ('unknown',{'cidr':'::/0'}),
])
def test_canonical_exact_family_scope(tool,args):
    with pytest.raises(contract.ProtectedError):calc.summary_network(tool,args)


def test_old_protected_profile_is_not_widened():
    for tool,cidr in [('subnet_calculator','0.0.0.0/0'),('subnet_calculator','192.0.2.0/31'),('subnet_calculator_v6','::/0')]:
        with pytest.raises(contract.ProtectedError):contract.validate_tool_arguments(tool,{'cidr':cidr})
        contract.validate_tool_arguments(tool,{'cidr':cidr},summary=True)


def test_native_mcp_bounded_full_range_and_independent_arithmetic(tmp_path):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    root=source(tmp_path)
    cases=[('subnet_calculator','0.0.0.0/0','4294967296'),
           ('subnet_calculator','255.255.255.255/32','1'),
           ('subnet_calculator','192.0.2.0/31','2'),
           ('subnet_calculator','192.0.2.0/26','64'),
           ('subnet_calculator_v6','::/0','340282366920938463463374607431768211456'),
           ('subnet_calculator_v6','2001:db8:1234::/48','1208925819614629174706176'),
           ('subnet_calculator_v6','2001:db8::/127','2'),
           ('subnet_calculator_v6','ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff/128','1')]
    async def run():
        params=StdioServerParameters(command=sys.executable,args=['-B',str(root/'servers/subnetcalculator_mcp.py')],
            env={'PATH':os.defpath,'HOME':str(tmp_path),'PYTHONDONTWRITEBYTECODE':'1'},cwd=str(tmp_path))
        with open(os.devnull,'w') as errors:
            async with stdio_client(params,errlog=errors) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    tools=await session.list_tools()
                    assert {t.name for t in tools.tools}==set(calc.TOOLS.values())
                    for entry in tools.tools:
                        assert entry.input_schema['required']==['cidr']
                        assert set(entry.input_schema['properties'])=={'cidr'}
                        assert entry.input_schema['properties']['cidr']['type']=='string'
                    for tool,cidr,count in cases:
                        response=await session.call_tool(tool,{'cidr':cidr})
                        assert not response.is_error
                        output=response.structured_content
                        if output is None:output=json.loads(response.content[0].text)
                        if set(output)=={'result'}:output=output['result']
                        summary=calc.verify_summary(tool,{'cidr':cidr},output)
                        assert summary['address_count']==count
                        assert len(json.dumps(summary))<2048
                        if tool=='subnet_calculator':
                            assert len(output['usable_hosts_preview'])<=10
                            assert output['usable_hosts_count']==int(summary['usable_count'])
                        bad=copy.deepcopy(output);bad['address_count']='7'
                        with pytest.raises(contract.ProtectedError,match='calculator_arithmetic_mismatch'):
                            calc.verify_summary(tool,{'cidr':cidr},bad)
                        with pytest.raises(contract.ProtectedError):
                            calc.verify_summary(tool,{'cidr':cidr},dict(output,answer='model says success'))
    asyncio.run(asyncio.wait_for(run(),10))


def test_summary_binding_requires_exact_qualified_native_source(tmp_path):
    from bgp.federation import protected_mcp as native
    from bgp.federation.protected_runtime import RuntimeRefused
    root=source(tmp_path).resolve()
    args={'cidr':'::/0'}
    config={'kind':'subnet_summary','tool':'subnet_calculator_v6','python':'/unopened/python',
        'python_manifest':'/unopened/manifest','python_manifest_sha256':'a'*64,
        'source_root':str(root),'source_sha256':{'servers/subnetcalculator_mcp.py':patcher.AFTER},
        'input_schema_sha256':'b'*64,'endpoint_sha256':native.sha({'kind':'subnet','transport':'private-stdio'}),
        'selection_sha256':native.sha({'tool':'subnet_calculator_v6','arguments':args}),
        'skill':{'path':'/unopened/subnet-calculator/SKILL.md','sha256':'c'*64}}
    assert native.validate_binding(config,arguments=args,check_files=False)==config
    for changed in ('source','extra_source','old_kind','family','selection'):
        bad=copy.deepcopy(config)
        if changed=='source':bad['source_sha256']['servers/subnetcalculator_mcp.py']='0'*64
        if changed=='extra_source':bad['source_sha256']['servers/extra.py']='0'*64
        if changed=='old_kind':bad['kind']='subnet'
        if changed=='family':bad['tool']='subnet_calculator'
        if changed=='selection':bad['selection_sha256']='0'*64
        with pytest.raises((RuntimeRefused,contract.ProtectedError)):
            native.validate_binding(bad,arguments=args,check_files=False)
