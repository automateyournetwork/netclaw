"""Local deterministic OpenAI-compatible fixture; never reaches a real provider."""
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

class Provider:
    def __init__(self):
        self.calls=[];self.started=threading.Event();self.release=threading.Event();self.fail_auth=False;owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
                if self.path == '/__fixture/count':
                    self.wfile.write(json.dumps({'inferences':len(owner.calls)}).encode());return
                self.wfile.write(json.dumps({'object':'list','data':[{'id':'hud-fixture','object':'model'}]}).encode())
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/__fixture/release':
                    owner.release.set();self.send_response(200);self.end_headers();return
                # Native provider discovery may probe non-inference endpoints
                # (for example Ollama /api/show). Do not simulate chat there.
                if self.path != '/v1/chat/completions':
                    self.send_response(404);self.end_headers();return
                owner.calls.append(body)
                if owner.fail_auth:
                    self.send_response(401);self.send_header('Content-Type','application/json');self.end_headers()
                    self.wfile.write(b'{"error":{"message":"Synthetic provider credentials rejected","type":"authentication_error"}}');return
                messages=body.get('messages',[]);latest=next((m.get('content','') for m in reversed(messages) if m['role']=='user'),'')
                if 'WAIT_FOR_TEST' in str(latest):
                    owner.started.set()
                    if not owner.release.wait(30):raise TimeoutError('Test did not release the controlled provider')
                turn_start=max((i for i,m in enumerate(messages) if m['role']=='user'),default=-1)
                tool_results=[m for m in messages[turn_start+1:] if m['role']=='tool']
                tool_calls=None
                if 'SUBNET' in str(latest) and not tool_results:
                    tool=next((t['function']['name'] for t in body.get('tools',[]) if 'subnet_calculator' in t['function']['name']),None)
                    if tool:tool_calls=[{'id':'fixture-call-1','type':'function','function':{'name':tool,'arguments':'{"cidr":"192.0.2.0/28"}'}}]
                delegation=re.search(r'MOBILE_DELEGATE:([A-Za-z0-9_./-]+)',str(latest))
                if delegation:
                    tool_name='n2n_delegate' if not tool_results else 'n2n_task_result'
                    tool=next((t['function']['name'] for t in body.get('tools',[]) if t['function']['name'].endswith('__'+tool_name)),None)
                    args={'peer':delegation.group(1),'target_name':'subnet-calculator','input_text':'SUBNET'}
                    task=re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',str(tool_results[0].get('content',''))) if tool_results else None
                    finished=tool_results and any(word in str(tool_results[-1].get('content','')) for word in ('completed','failed','cancelled','outcome_unknown'))
                    if tool_results:args={'task_id':task.group(0)} if task else {}
                    if tool and not finished and (not tool_results or task):
                        if tool_results:time.sleep(.4)
                        tool_calls=[{'id':'delegate-call-'+str(len(tool_results)),'type':'function','function':{'name':tool,'arguments':json.dumps(args)}}]
                if 'FORGED_SHELL' in str(latest):tool_calls=[{'id':'forged-call','type':'function','function':{'name':'terminal','arguments':'{"command":"echo forbidden"}'}}]
                content=None if tool_calls else ('CANARY '+str(tool_results[-1]['content']) if tool_results else 'HERMES FIXTURE '+ ('violet' if any('violet' in str(m.get('content')) for m in messages) else str(latest)))
                if not tool_calls and 'CANVAS_' in str(latest):
                    content='HERMES FIXTURE violet '+str(latest).splitlines()[0]
                message={'role':'assistant','content':content}
                if tool_calls:message['tool_calls']=tool_calls
                output={'id':'fixture-response','object':'chat.completion','created':1,'model':'hud-fixture','choices':[{'index':0,'message':message,'finish_reason':'tool_calls' if tool_calls else 'stop'}],'usage':{'prompt_tokens':12,'completion_tokens':8,'total_tokens':20}}
                self.send_response(200)
                if body.get('stream'):
                    self.send_header('Content-Type','text/event-stream');self.end_headers()
                    delta={'role':'assistant','content':content or ''}
                    if tool_calls:delta['tool_calls']=[{'index':0,**tool_calls[0]}]
                    chunk={**output,'object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':None}]}
                    self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
                    chunk['choices']=[{'index':0,'delta':{},'finish_reason':'tool_calls' if tool_calls else 'stop'}]
                    self.wfile.write(('data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n').encode())
                else:
                    self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(output).encode())
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
    def start(self):self.thread.start();return f'http://127.0.0.1:{self.server.server_port}/v1'
    def close(self):self.release.set();self.server.shutdown();self.server.server_close();self.thread.join()
