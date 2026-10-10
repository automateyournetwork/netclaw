"""Source-qualified read-only MCP tools; annotations never grant permission."""
import hashlib
import ipaddress
import json
from pathlib import Path
from ledger import HudError, digest

ROOT=Path(__file__).resolve().parents[2]

def verify_source(source):
    manifest=json.loads((ROOT/'config/hermes-hud-compatibility.json').read_text())
    for name,expected in manifest['files'].items():
        try: actual=hashlib.sha256((Path(source)/name).read_bytes()).hexdigest()
        except OSError: raise HudError('compatibility_unsupported') from None
        if actual!=expected:raise HudError('compatibility_unsupported', 'Hermes source differs from the qualified release.')
    return manifest

class ToolPolicy:
    def __init__(self, entries, config_file, config_digest):
        self.entries=entries;self.config_file=Path(config_file);self.config_digest=config_digest
        self.names=set(entries)
        self.fingerprint=digest({'config':config_digest,'entries':entries})
    def check_sources(self):
        if getattr(self, "runtime_source", None):verify_source(self.runtime_source)
        if hashlib.sha256(self.config_file.read_bytes()).hexdigest()!=self.config_digest:raise HudError('policy_unverified','Selected configuration changed. Restart and requalify.')
        for entry in self.entries.values():
            if hashlib.sha256(Path(entry['source']).read_bytes()).hexdigest()!=entry['sourceHash']:raise HudError('policy_unverified')
    def check_arguments(self,name,args):
        self.check_sources()
        if name not in self.entries or not isinstance(args,dict):raise HudError('capability_unsupported')
        rule=self.entries[name]['argumentPolicy']
        if rule=='ipv4-small-subnet':
            if set(args)!={'cidr'}:raise HudError('input_invalid')
            try: network=ipaddress.IPv4Network(args['cidr'],strict=False)
            except (ValueError,TypeError):raise HudError('input_invalid') from None
            # Upstream implementation materializes addresses; bound its allocation.
            if not 24<=network.prefixlen<=30:raise HudError('input_invalid','Qualified subnet tool supports IPv4 /24 through /30.')
        elif rule=='fixture-echo':
            if set(args)!={'text'} or not isinstance(args['text'],str) or len(args['text'])>256:raise HudError('input_invalid')
        elif rule=='federation-operator':
            from federation_tools import validate_operator
            validate_operator(name,args)
        else:raise HudError('policy_unverified')

def qualified_servers(config, manifest=None, home=None):
    """Accept only reviewed source + explicit stdio registration, not arbitrary commands."""
    manifest=manifest or json.loads((ROOT/'config/hermes-hud-tool-policy.json').read_text())
    selected={};entries={}
    for name,registration in (config.get('mcp_servers') or {}).items():
        rule=manifest['servers'].get(name)
        if not rule:continue
        source=(ROOT/rule['source']).resolve()
        if not source.is_file():continue
        source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        if source_hash not in rule.get('sourceHashes',[rule.get('sourceHash')]):continue
        args=registration.get('args',[])
        # Only the existing NetClaw isolated component launcher or the exact reviewed script.
        launcher=str(ROOT/'scripts/component-launch.py')
        expected=['-u',launcher,rule['component'],'--server',name]
        direct=['-u',str(source)]
        normalized=[str((ROOT/a).resolve()) if isinstance(a,str) and (a.startswith('scripts/') or a.startswith('mcp-servers/')) else a for a in args]
        if normalized not in (expected,direct):continue
        command=registration.get('command','')
        if Path(command).name not in ('python','python3','python3.12','python3.14'):continue
        if registration.get('url'):continue
        registered_env=dict(registration.get('env') or {})
        if rule.get('argumentPolicy')=='federation-operator' and 'BGP_DAEMON_API' in registered_env:
            endpoint=registered_env.pop('BGP_DAEMON_API')
            # Existing installer templates carry this ordinary-agent endpoint.
            # It is never an execution destination in the protected profile.
            import re
            if endpoint!='${BGP_DAEMON_API:-http://127.0.0.1:8179}' and (not isinstance(endpoint,str) or not re.fullmatch(r'http://(?:127\.0\.0\.1|localhost):[0-9]{1,5}/?',endpoint)):
                continue
            registration={**registration,'env':registered_env}
        allowed_env={'NETCLAW_RUNTIME_ROOT':str(Path(home)/'python-runtimes'), 'NETCLAW_RUNTIME_ENV':str(Path(home)/'.env')} if home else {}
        if any(key not in allowed_env or value!=allowed_env[key] for key,value in registered_env.items()):continue
        if rule.get('argumentPolicy')=='federation-operator':
            # Discovery may expose schemas, but its process is never an execution
            # fallback. Every real dispatch receives its own broker permit.
            registration={**registration,'env':{**registered_env,'NETCLAW_FEDERATION_SCOPED':'1'}}
        # Bind live handlers at companion startup, including after a restart.
        # Cached lazy registrations can disappear when the agent changes its
        # profile scope; a schema cache is not execution qualification.
        selected[name]={**registration,'args':normalized,'tools':{'include':rule['tools']},'trust':'full','lazy':False}
        for tool in rule['tools']:
            native='mcp__'+name.replace('-','_')+'__'+tool
            entries[native]={'source':str(source),'sourceHash':source_hash,'argumentPolicy':rule['argumentPolicy']}
    return selected,entries

def qualified_skills(home):
    """Only installed, reviewed static instructions; no arbitrary file/read tool."""
    from os import O_RDONLY, O_NOFOLLOW, open as os_open, fdopen
    expected=ROOT/'workspace/skills/subnet-calculator/SKILL.md'
    target=Path(home)/'skills/subnet-calculator/SKILL.md'
    if not target.exists():return ''
    if target.resolve().parent != (Path(home).resolve()/'skills/subnet-calculator'):raise HudError('policy_unverified')
    with fdopen(os_open(target,O_RDONLY|O_NOFOLLOW),'rb') as stream: content=stream.read(32769)
    if len(content)>32768 or hashlib.sha256(content).digest()!=hashlib.sha256(expected.read_bytes()).digest():return ''
    return '\nInstalled qualified subnet-calculator skill (only IPv4 /24 through /30 is enabled; shell examples are documentation, not executable tools):\n'+content.decode()
