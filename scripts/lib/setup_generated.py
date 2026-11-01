"""Installation-owned references, derived from the selected home's layout only.

Paths mirror common.sh/core_deploy and their actual launch wrappers. Commands
use shlex quoting for the existing MCP_CALL string interface; no user command
or executable is accepted. This module does not read another installation.
"""
from pathlib import Path
import shlex
import os
from setup_state import guarded_read,Conflict

SCRIPTS={
 'MCP_CALL':'scripts/mcp-call.py','PYATS_MCP_SCRIPT':'scripts/pyats-stdio.py',
 'GAIT_MCP_SCRIPT':'scripts/gait-stdio.py','MEMPALACE_MCP_SCRIPT':'scripts/mempalace-stdio.py',
 'F5_MCP_SCRIPT':'mcp-servers/f5-mcp-server/F5MCPserver.py',
 'CATC_MCP_SCRIPT':'mcp-servers/catc-mcp/server.py',
 'NETBOX_MCP_SCRIPT':'mcp-servers/netbox-mcp-server/src/netbox_mcp_server/server.py',
 'ACI_MCP_SCRIPT':'mcp-servers/ACI_MCP/aci_mcp/main.py',
 'SERVICENOW_MCP_SCRIPT':'mcp-servers/servicenow-mcp/src/servicenow_mcp/cli.py',
 'ISE_MCP_SCRIPT':'mcp-servers/ISE_MCP/src/ise_mcp_server/server.py',
 'SDWAN_MCP_SCRIPT':'mcp-servers/cisco-sdwan-mcp/sdwan_mcp_server.py',
 'NVD_MCP_SCRIPT':'mcp-servers/mcp-nvd/mcp_nvd/main.py',
 'CISCO_PSIRT_MCP_SCRIPT':'mcp-servers/cisco-psirt-mcp/server.py',
 'NMAP_MCP_SCRIPT':'mcp-servers/nmap-mcp/server.py',
 'CLAB_MCP_SCRIPT':'mcp-servers/clab-mcp-server/clab_mcp_server.py',
 'PROTOCOL_MCP_SCRIPT':'mcp-servers/protocol-mcp/server.py',
 'MARKMAP_MCP_SCRIPT':'mcp-servers/markmap_mcp/markmap-mcp/dist/index.js',
 'SUBNET_MCP_SCRIPT':'mcp-servers/subnet-calculator-mcp/servers/subnetcalculator_mcp.py',
 'WIKIPEDIA_MCP_SCRIPT':'mcp-servers/Wikipedia_MCP/main.py',
 'PACKET_BUDDY_MCP_SCRIPT':'mcp-servers/packet-buddy-mcp/server.py',
 'FWRULE_MCP_DIR':'mcp-servers/fwrule-mcp',
}
COMMANDS={'FORTINET_MCP_CMD':('fortinet','fortinet-mcp'),
 'ZABBIX_MCP_CMD':('zabbix','zabbix-mcp'),'BGP_INTEL_MCP_CMD':('bgp-intel','bgp-intel-mcp'),
 'DOCUMENT_MCP_CMD':('document','document-mcp')}


def generated(claw,validator,python):
    home=Path(claw['runtimeHome']);source=home/'.setup/source'
    keys={s['key'] for name in claw['capabilities']['components']
          for s in validator.components[name]['settings'] if s['input']=='generated'}
    values={k:str(source/v) for k,v in SCRIPTS.items() if k in keys}
    # Both layouts are supported by the existing Markmap build step. Observe
    # the actual owned output, then keep the selected launcher path explicit.
    if 'MARKMAP_MCP_SCRIPT' in values and not Path(values['MARKMAP_MCP_SCRIPT']).is_file():
        alternate=source/'mcp-servers/markmap_mcp/dist/index.js'
        if alternate.is_file() and not alternate.is_symlink():values['MARKMAP_MCP_SCRIPT']=str(alternate)
    for key,(component,server) in COMMANDS.items():
        if key in keys:values[key]=shlex.join([python,str(source/'scripts/component-launch.py'),component,'--server',server])
    for component,key,module in [('infoblox','INFOBLOX_MCP_CMD','infoblox_ddi_mcp'),('panorama','PANOS_MCP_CMD','palo_alto_mcp'),('mempalace','MEMPALACE_MCP_PYTHON',None)]:
        record=home/'python-runtimes/records'/component
        if component not in claw['capabilities']['components'] or not record.exists():continue
        executable=guarded_read(record,8192,private=True).decode().strip()
        if not Path(executable).is_relative_to(home) or not os.access(executable,os.X_OK):raise Conflict('component_runtime_outside_home')
        values[key]=shlex.join([executable,'-m',module]) if module else executable
    paths={'PYATS_TESTBED_PATH':Path(claw['workspace'])/'testbed.yaml','PYATS_VENV':home/'pyats-venv',
           'PYATS_UPSTREAM_SCRIPT':home/'pyats-venv/upstream/pyats_mcp_server.py',
           'GAIT_VENV':home/'gait-venv','GTRACE_MCP_BIN':home/'.setup/prefix/bin/gtrace',
           'K8S_MCP_CMD':source/'mcp-servers/k8s-mcp/kubernetes-mcp-server','HERMES_HOME':home}
    values.update({k:str(v) for k,v in paths.items() if k in keys})
    if 'pyats' in claw['capabilities']['components']:
        from pyats_testbeds import policy_environment
        values.update(policy_environment(claw.get('testbed'),Path(claw['workspace'])/'testbed.yaml'))
    if 'netconverter' in claw['capabilities']['components']:
        values['NETCONVERTER_DATA_DIR']=str(home/'netconverter')
        values['NETCONVERTER_INSTALLATION_ID']=claw['id']
    if claw.get('role') in ('border','member'):
        # Registration precedes Risk materialization and freezes native MCP
        # aliases. Bind to the reviewed local endpoint now, not the component's
        # default 8179 or another claw's API. Focused settings remain unchanged.
        endpoint='http://127.0.0.1:'+str(claw['endpoints']['bgpApiPort'])
        values.update(BGP_DAEMON_API=endpoint,NETCLAW_BGP_API=endpoint)
    # Data/cache paths must stay local even when upstream's default is a global
    # .openclaw path. Operator-reviewed explicit settings remain authoritative.
    for component,key,directory in [('nsm','NSM_HOME','nsm'),('rag-mcp','RAG_DATA_DIR','rag'),
        ('memory-mcp','MEMORY_DATA_DIR','memory'),('document','DOCUMENT_OUTPUT_DIR','documents')]:
        if component in claw['capabilities']['components'] and key not in claw['settings']:
            values[key]=str(home/directory)
    return values
