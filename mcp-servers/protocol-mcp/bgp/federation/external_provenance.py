"""Native gateway tool events joined to local eN2N receipts, never model prose."""
import json
import re

TOOLS = {f'n2n-mcp__{name}': name for name in ('n2n_invoke', 'n2n_delegate', 'n2n_chat', 'n2n_task_result', 'n2n_task_status')}
ID = re.compile(r'[A-Za-z0-9_.:-]{1,200}')


class ExternalProvenance:
    def __init__(self, tasks, parent, run):
        self.tasks, self.parent, self.run = tasks, parent, run
        self.started = {}
        self.last_sequence = -1
        self.count = 0

    def event(self, payload):
        if not isinstance(payload, dict) or payload.get('runId') != self.run:
            return
        sequence = payload.get('seq')
        if type(sequence) is not int or sequence <= self.last_sequence:
            return
        self.last_sequence = sequence
        if payload.get('stream') != 'tool':
            return
        data = payload.get('data')
        if not isinstance(data, dict) or data.get('name') not in TOOLS:
            return
        call = data.get('toolCallId')
        if not isinstance(call, str) or not ID.fullmatch(call):
            return
        if data.get('phase') == 'start':
            args = data.get('args')
            if len(self.started) < 32 and isinstance(args, dict):
                # Keep only identifiers; prompts/arguments/results stay out of
                # the durable attribution record and this correlation map.
                self.started[call] = (data['name'], {k: args.get(k) for k in ('peer', 'task_id')})
            return
        start = self.started.pop(call, None)
        if data.get('phase') != 'result' or not start or start[0] != data['name'] or data.get('isError') or self.count >= 16:
            return
        result = data.get('result')
        if not isinstance(result, dict) or result.get('isError'):
            return
        details = result.get('details')
        if not isinstance(details, dict) or details.get('mcpServer') != 'n2n-mcp' or details.get('mcpTool') != TOOLS[data['name']] or details.get('status') == 'error':
            return
        try:
            if isinstance(details.get('structuredContent'), dict):
                value = details['structuredContent']
                if len(json.dumps(value).encode()) > 131072:
                    return
            else:
                content = result.get('content')
                if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict) or content[0].get('type') != 'text':
                    return
                text = content[0].get('text')
                if not isinstance(text, str) or len(text.encode()) > 131072:
                    return
                value = json.loads(text.removeprefix('structuredContent:\n'))
            # FastMCP's native str-return schema wraps the JSON string once.
            if isinstance(value, dict) and set(value) == {'result'} and isinstance(value['result'], str):
                value = json.loads(value['result'])
        except (ValueError, TypeError):
            return
        if not isinstance(value, dict) or value.get('trust') != 'remote-untrusted':
            return
        peer, request, task = value.get('source'), value.get('request_id'), value.get('task_id')
        if not isinstance(peer, str) or not ID.fullmatch(peer):
            return
        method, args = TOOLS[data['name']], start[1]
        conn = self.tasks.manager._conn
        if method in ('n2n_task_result', 'n2n_task_status'):
            if not isinstance(task, str) or not ID.fullmatch(task) or args['task_id'] != task:
                return
            row = conn.execute("SELECT target_type FROM delegated_task WHERE task_id=? AND direction='outbound' AND peer_identity=?", (task, peer)).fetchone()
            if not row:
                return
            kind, request = row['target_type'], task
        else:
            if args['peer'] != peer or not isinstance(request, str) or not ID.fullmatch(request):
                return
            if method == 'n2n_chat':
                row = conn.execute("SELECT target_type FROM remote_invocation_record WHERE direction='outbound' AND peer_identity=? AND request_id=? AND target_type='chat' AND outcome='success'", (peer, request)).fetchone()
                kind = 'chat'
            else:
                row = conn.execute("SELECT method,remote_task FROM outbound_intent WHERE request=? AND peer=? AND state IN ('completed','submitted')", (request, peer)).fetchone()
                kind = 'skill' if row and row['method'] == 'n2n/tasks/submit' else 'tool'
                if row and row['remote_task'] != task:
                    return
            if not row:
                return
        self.tasks.record_external_source(self.parent, self.run, call,
            {'peer': peer, 'kind': kind, 'request_id': request, 'task_id': task,
             'trust': 'remote-untrusted'})
        self.count += 1
