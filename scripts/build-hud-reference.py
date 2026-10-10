#!/usr/bin/env python3
"""Build offline CLI/MCP/HTTP and documentation references from repository source.
No entry point is imported or executed. Run again after changing a public interface.
"""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/reference'


def files():
    tracked = subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    added = subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    return sorted(set(tracked + added))


def build():
    OUT.mkdir(exist_ok=True)
    paths = files(); cli = []
    for name in paths:
        p = ROOT / name
        if not p.is_file() or p.is_symlink() or '/vendor/' in name or name.startswith(('tests/','specs/','docs/','workspace/')):
            continue
        if not (p.suffix in ('.py','.sh') or name == 'scripts/netclaw'):
            continue
        source = p.read_text(errors='replace')
        if not (name.startswith('scripts/') or '__main__' in source or 'ArgumentParser(' in source or p.suffix == '.sh'):
            continue
        declarations=[]
        if p.suffix == '.py':
            try:
                tree=ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('add_argument','add_parser','add_subparsers','ArgumentParser'):
                        declarations.append({'line':node.lineno,'declaration':ast.get_source_segment(source,node)})
                # Hand-written argv parsers have no argparse declarations. Include
                # their branches and usage statements as source evidence.
                for n,line in enumerate(source.splitlines(),1):
                    if re.search(r'sys\.argv|Usage:|usage:|cmd ==|cmd in ',line):
                        declarations.append({'line':n,'declaration':line.strip()})
            except SyntaxError:
                declarations.append({'line':1,'declaration':'Source could not be parsed; consult source.'})
        else:
            for n,line in enumerate(source.splitlines(),1):
                if re.search(r'(^\s*#.*(?:netclaw|--|Usage)|Usage:|case .* in|^\s*[\w|*-]+\)|--[\w-]+)',line):
                    declarations.append({'line':n,'declaration':line.strip()})
        cli.append({'path':name,'kind':'Python' if p.suffix=='.py' else 'Shell',
                    'flags':sorted(set(re.findall(r'(?<![\w-])--[a-zA-Z][a-zA-Z0-9-]*',source))),
                    'declarations':declarations,'sha256':hashlib.sha256(source.encode()).hexdigest(),
                    'coverage':'Static source declarations; lexical flags may include delegated commands. No execution performed.'})
    # npm scripts and Node launchers are part of the user-facing CLI surface too.
    for name in paths:
        p=ROOT/name
        if not p.is_file() or p.is_symlink() or '/vendor/' in name or '/node_modules/' in name:
            continue
        if p.name=='package.json':
            try: package=json.loads(p.read_text())
            except (ValueError,UnicodeError): continue
            commands=package.get('scripts') or {}
            if not commands: continue
            cli.append({'path':name,'kind':'npm scripts','flags':sorted(set(re.findall(r'--[a-zA-Z][a-zA-Z0-9-]*',json.dumps(commands)))),
                        'declarations':[{'line':1,'declaration':f'npm run {key} → {value}'} for key,value in commands.items()],
                        'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'coverage':'All package.json script commands. Arguments after -- are delegated to the underlying command.'})
        elif p.suffix in ('.js','.mjs','.cjs') and (name.startswith('scripts/') or p.name in ('server.js','preview-build.mjs')):
            source=p.read_text(errors='replace')
            cli.append({'path':name,'kind':'Node launcher','flags':sorted(set(re.findall(r'--[a-zA-Z][a-zA-Z0-9-]*',source))),
                        'declarations':[{'line':n,'declaration':line.strip()} for n,line in enumerate(source.splitlines(),1) if re.search(r'process\.argv|Usage:|usage:',line)],
                        'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'coverage':'Node entry point; argument/source references only. npm wrapper commands are indexed separately.'})
    cli.sort(key=lambda c:c['path'])
    config=json.loads((ROOT/'config/openclaw.json').read_text()); servers=[]
    registrations={**config.get('mcpServers',{}),'hermes-hud-mcp':{'access':'hud-private','command':'python3','args':['-u','scripts/component-launch.py','hermes-hud','--server','hermes-hud-mcp']}}
    for name,cfg in sorted(registrations.items()):
        directory=ROOT/'mcp-servers'/name; tools=[]
        if directory.is_dir():
            for p in sorted(directory.rglob('*.py')):
                if any(part in ('vendor','.venv','tests','test','__pycache__') for part in p.relative_to(directory).parts): continue
                try: tree=ast.parse(p.read_text())
                except (SyntaxError,UnicodeError): continue
                tool_decorators={node.name for node in ast.walk(tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and any(isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='tool' and isinstance(call.func.value,ast.Name) and call.func.value.id=='mcp' for call in ast.walk(node))}
                for node in ast.walk(tree):
                    if isinstance(node,ast.Call) and ((isinstance(node.func,ast.Attribute) and node.func.attr=='Tool') or (isinstance(node.func,ast.Name) and node.func.id=='Tool')):
                        kw={k.arg:k.value for k in node.keywords}
                        if isinstance(kw.get('name'),ast.Constant) and isinstance(kw['name'].value,str):
                            tools.append({'name':kw['name'].value,'signature':ast.unparse(kw['inputSchema']) if 'inputSchema' in kw else 'Schema supplied dynamically', 'description':kw['description'].value if isinstance(kw.get('description'),ast.Constant) and isinstance(kw['description'].value,str) else '', 'source':str(p.relative_to(ROOT)), 'line':node.lineno})
                    if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
                    decorators=[ast.unparse(d) for d in node.decorator_list]
                    if not any(re.search(r'(^|\.)tool(?:\(|$)',d) or d.split('(')[0] in tool_decorators for d in decorators): continue
                    tools.append({'name':node.name,'signature':ast.unparse(node.args),'description':ast.get_docstring(node) or '', 'source':str(p.relative_to(ROOT)), 'line':node.lineno})
        servers.append({'name':name,'access':cfg.get('access','agent-native'),'transport':'HTTP' if cfg.get('url') else 'stdio','tools':tools,
                        'coverage':'Source-declared tool signatures/schemas; runtime tools/list is authoritative.' if tools else 'External, generated or non-decorator tools: runtime tools/list required; schema not inferred.'})
    routes={}
    for p in [ROOT/'ui/netclaw-visual/server.js',*sorted((ROOT/'ui/netclaw-visual/src/hud-server').rglob('*.js'))]:
        if '.test.' in p.name: continue
        source=p.read_text()
        for match in re.finditer(r"app\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]",source):
            method,url=match.groups(); route=re.sub(r':(\w+)',r'{\1}',url)
            op={'operationId':method+'_'+re.sub(r'\W+','_',url).strip('_'),'summary':method.upper()+' '+route,
                'description':'Local Host/Origin guards apply. See x-source for implementation. General response schema is intentionally unspecified; this is not a promise of upstream device API compatibility.',
                'x-source':f'{p.relative_to(ROOT)}:{source[:match.start()].count(chr(10))+1}',
                'responses':{'200':{'description':'Successful response; see implementation for payload and other success codes.'},'default':{'description':'Rejected, unavailable or failed request.'}}}
            parameters=[{'name':n,'in':'path','required':True,'schema':{'type':'string'}} for n in re.findall(r'\{(\w+)\}',route)]
            if parameters: op['parameters']=parameters
            if method in ('post','put','patch'):
                op['requestBody']={'required':False,'content':{'application/json':{'schema':{'type':'object','additionalProperties':True}}}}
            if '/hud/tasks/' in route or '/chat/' in route: op['security']=[{'HUDCookie':[]}]
            routes.setdefault(route,{})[method]=op
    # These fixed routes are registered by a small table rather than app.get/post.
    for method,suffix in [('get',''),('get','/events'),('post','/approval'),('post','/stop')]:
        route='/api/chat/requests/{id}'+suffix
        routes.setdefault(route,{})[method]={'operationId':method+'_owned_request'+suffix.replace('/','_'),'summary':method.upper()+' '+route,'x-source':'ui/netclaw-visual/src/hud-server/runtime/routes.js','description':'Owned Hermes request. Selected-installation HttpOnly cookie; authorization rechecked after I/O. Polling never resubmits.','security':[{'HUDCookie':[]}],'parameters':[{'name':'id','in':'path','required':True,'schema':{'type':'string'}}],'responses':{'200':{'description':'Owned request state or bounded event page.'},'404':{'description':'Unavailable or not owned.'}}}
    search=routes['/api/rag/search']['post']; search['requestBody']={'required':True,'content':{'application/json':{'schema':{'type':'object','required':['query'],'properties':{'query':{'type':'string','minLength':1,'maxLength':4000},'collection':{'type':'string','pattern':'^[\\w.-]{1,128}$','default':'documents'},'k':{'type':'integer','minimum':1,'maximum':20,'default':5}},'additionalProperties':False}}}}
    upload=routes['/api/rag/upload']['post'];upload['requestBody']={'required':True,'content':{'multipart/form-data':{'schema':{'type':'object','required':['file'],'properties':{'file':{'type':'string','format':'binary'},'title':{'type':'string'},'doc_type':{'type':'string','enum':['other','vendor','standard','customer','install-guide']}}}}}};upload['responses']['202']={'description':'Accepted; ingestion pending, not ready.'}
    openapi={'openapi':'3.1.0','info':{'title':'NetClaw local HUD HTTP API','version':'127','description':'Source-derived HUD route inventory. Local loopback service; not an internet API. MCP uses JSON-RPC tools/list and tools/call, not REST/OpenAPI. Generic schemas are explicitly incomplete.'},'servers':[{'url':'http://localhost:3000','description':'Default UI proxy; operator ports may differ'}],'paths':routes,'components':{'securitySchemes':{'HUDCookie':{'type':'apiKey','in':'cookie','name':'nc_hud','description':'Legacy OpenClaw cookie, or selected-installation nc_hud_<UUID without hyphens> cookie. HttpOnly; no browser-supplied ownership IDs.'}}}}
    daemon=ROOT/'mcp-servers/protocol-mcp/bgp-daemon-v2.py'
    daemon_conditions=[{'line':n,'declaration':line.strip()} for n,line in enumerate(daemon.read_text().splitlines(),1) if re.search(r'if .*path|elif .*path|method ==',line)]
    reference={'scope':'Repository script entry points, non-vendored Python/shell launchers, npm scripts and Node service/preview launchers. Static declarations include positional args, defaults and choices when present; delegated upstream/runtime CLIs require their installed help. MCP source signatures are not runtime schema attestations.', 'cli':cli,'mcps':servers,'http':openapi,'daemon':{'source':str(daemon.relative_to(ROOT)),'conditions':daemon_conditions}}
    (OUT/'interfaces.json').write_text(json.dumps(reference,indent=2)+'\n')
    (OUT/'hud-openapi.json').write_text(json.dumps(openapi,indent=2)+'\n')
    md=['# NetClaw CLI and interface reference','',reference['scope'],'','Generated with `python3 scripts/build-hud-reference.py`. Nothing is executed during extraction.','',
        '## Modalities','', 'Canvas branching chat; HUD dashboards; terminal/TUI; Slack and WebEx; mobile text, voice, QR/deep links and camera/microphone capture; MCP stdio/HTTP; external eN2N and internal iN2N delegation. Availability depends on installed/configured integrations. Mobile has no local LLM runtime; Border or a delegated member answers.','',
        '## Top-level command','', 'Run `scripts/netclaw` for the interactive menu. `tui` delegates to OpenClaw (`openclaw tui`) or Hermes (`hermes --tui`). `install` forwards arguments to scripts/install.sh. `help`, `-h`, `--help` display the built-in summary.','',
        '`peering`: status (default), bgp, n2n, ngrok, up, down, announce.','',
        '`risk`: status (default), members, health, add <profile|custom> <name> [csv-skills], remove <member>, role <role> <risk-name> [stacks], edge-check (aliases edge_check/preflight), token [--edge] [label], enroll-mobile [label] (alias enroll_mobile), route <request> [capability].','',
        '`chats`: list, <id-prefix> to tail, --watch (alias watch) [seconds]. `link` recreates the local launcher symlink. These commands may mutate state; documentation is not authorization to run them.','',
        '## HTTP and MCP','', '[HUD OpenAPI JSON](hud-openapi.json) inventories every registered HUD HTTP route. Generic schemas remain unspecified; detailed schemas exist for RAG retrieval/upload. [Machine-readable reference](interfaces.json) includes source-declared MCP signatures and daemon route conditions. MCP is JSON-RPC, not REST; use tools/list from the installed server for authoritative schemas. This reference does not contact servers, execute tools or include configuration values.','']
    for entry in cli:
        md.extend(['## '+entry['path'],'',entry['coverage'],'','Flags mentioned: '+(', '.join('`'+x+'`' for x in entry['flags']) or 'none'),'','```text'])
        md.extend(f"L{d['line']}: {d['declaration']}" for d in entry['declarations'])
        md.extend(['```',''])
    (OUT/'CLI-REFERENCE.md').write_text('\n'.join(md)+'\n')
    allowed_roots={'README.md','TOOLS-REFERENCE.md','N2N-PEERING-NETCLAWS.md','CONTRIBUTING.md','SECURITY.md'}
    documents=[]
    for name in sorted(set(paths+['docs/reference/CLI-REFERENCE.md','docs/reference/hud-openapi.json','docs/reference/interfaces.json'])):
        p=ROOT/name
        if not p.is_file() or p.is_symlink(): continue
        if not (name in allowed_roots or (name.startswith('docs/') and p.suffix=='.md') or name in ['docs/reference/hud-openapi.json','docs/reference/interfaces.json'] or name.endswith('/SKILL.md') and name.startswith('workspace/skills/') or name=='mobile/netclaw-mobile/MOBILE-ONBOARDING.md'): continue
        first=next((line.strip('# ').strip() for line in p.read_text(errors='replace').splitlines() if line.startswith('# ')),p.stem)
        documents.append({'id':hashlib.sha256(name.encode()).hexdigest()[:16],'path':name,'title':first,'category':'Skills' if name.startswith('workspace/') else 'Reference' if name.startswith('docs/reference/') else 'Guides'})
    (OUT/'documents.json').write_text(json.dumps(documents,indent=2)+'\n')
    print(f'{len(cli)} CLI/source entries; {len(servers)} MCP registrations; {sum(len(s["tools"]) for s in servers)} source tool signatures; {sum(len(v) for v in routes.values())} HUD routes; {len(documents)} documents')

if __name__=='__main__': build()
