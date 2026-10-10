"""Local deterministic OpenAI-compatible fixture; never reaches a real provider."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

class Provider:
    def __init__(self):
        self.calls=[];owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
                self.wfile.write(json.dumps({'object':'list','data':[{'id':'hud-fixture','object':'model'}]}).encode())
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));owner.calls.append(body)
                messages=body.get('messages',[]);latest=next((m.get('content','') for m in reversed(messages) if m['role']=='user'),'')
                tool_results=[m for m in messages if m['role']=='tool']
                tool_calls=None
                if 'SUBNET' in str(latest) and not tool_results:
                    tool=next((t['function']['name'] for t in body.get('tools',[]) if 'subnet_calculator' in t['function']['name']),None)
                    if tool:tool_calls=[{'id':'fixture-call-1','type':'function','function':{'name':tool,'arguments':'{"cidr":"192.0.2.0/28"}'}}]
                if 'FORGED_SHELL' in str(latest):tool_calls=[{'id':'forged-call','type':'function','function':{'name':'terminal','arguments':'{"command":"echo forbidden"}'}}]
                content=None if tool_calls else ('CANARY '+str(tool_results[-1]['content']) if tool_results else 'HERMES FIXTURE '+ ('violet' if any('violet' in str(m.get('content')) for m in messages) else str(latest)))
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
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join()
