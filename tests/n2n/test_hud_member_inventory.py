import asyncio
import json
from types import SimpleNamespace
from bgp.federation.member_inventory import local_inventory, project_inventory, stored_inventory


def test_projection_excludes_all_configuration_values_and_bounds_names():
    card = project_inventory({'llm': {'primary_model': 'provider/model', 'api_key': 'private'},
                              'mcp_servers': [{'name': 'rag-mcp', 'tools': ['rag_search', {'name': 'rag_list','inputSchema': {'secret': 'private'}}], 'env': {'PASSWORD': 'private'}, 'command': 'private'}, {'name': 'bad name with spaces'}], 'secret': 'private'})
    assert len(card['mcp_servers']) == 1
    assert card['mcp_servers'][0]['tools'] == ['rag_search', 'rag_list']
    assert 'private' not in json.dumps(card)
    assert card['llm']['primary_model'] == 'provider/model'


def test_member_config_model_override_and_actual_scoped_servers(tmp_path):
    cfg = tmp_path / 'openclaw.json'
    cfg.write_text(json.dumps({'agents': {'defaults': {'model': {'primary': 'provider/default'}}}, 'mcp': {'servers': {'rag-mcp': {'command': 'hidden', 'tools': ['rag_search']}}}}))
    inventory = local_inventory({'OPENCLAW_CONFIG_PATH': str(cfg), 'N2N_MEMBER_MODEL': 'local/override'})
    assert inventory['llm']['primary_model'] == 'local/override'
    assert [s['name'] for s in inventory['mcp_servers']] == ['rag-mcp']
    assert 'hidden' not in json.dumps(inventory)
    assert local_inventory({'OPENCLAW_CONFIG_PATH': str(tmp_path/'missing')})['available'] is False


def test_inventory_is_bound_to_authenticated_channel_not_claimed_member(manager):
    from bgp.federation.service import FederationService
    svc = FederationService(local_as=65001,router_id='1.1.1.1',manager=manager)
    calls = []
    svc.risk.update_health = lambda member_id, **kw: calls.append((member_id,kw))
    asyncio.run(svc._in2n_on_member_inventory(SimpleNamespace(member_id='risk/actual'), {'member_id':'risk/victim','llm':{'primary_model':'local/model'},'mcp_servers':[]}))
    assert calls[0][0] == 'risk/actual'
    stored = stored_inventory({'health':json.dumps(calls[0][1])})
    assert stored['llm']['primary_model'] == 'local/model'
    assert 'received_at' in stored
    assert stored_inventory({'health':'{}'}) is None


def test_empty_scoped_mcp_list_never_falls_back_to_border_and_agent_model_wins(tmp_path):
    cfg = tmp_path / 'openclaw.json'
    cfg.write_text(json.dumps({'agents': {'defaults': {'model': 'default/model'}, 'list': [{'id': 'main', 'model': 'agent/model'}]}, 'mcp': {'servers': {}}, 'mcpServers': {'border-secret-server': {}}}))
    result = local_inventory({'OPENCLAW_HOME': str(tmp_path)})
    assert result['mcp_servers'] == []
    assert result['llm']['primary_model'] == 'agent/model'
    missing = project_inventory({'available': False})
    assert missing['available'] is False


def test_native_tool_filter_is_projected_without_private_launch_configuration(tmp_path):
    cfg = tmp_path / 'openclaw.json'
    cfg.write_text(json.dumps({'mcp': {'servers': {'subnet-calc-mcp': {
        'toolFilter': {'include': ['subnet_calculator']},
        'command': '/private/python', 'env': {'ANTHROPIC_API_KEY': 'private-secret'}
    }}}}))
    result = local_inventory({'OPENCLAW_CONFIG_PATH': str(cfg)})
    assert result['mcp_servers'] == [{'name': 'subnet-calc-mcp', 'tools': ['subnet_calculator']}]
    assert 'private' not in json.dumps(result)
