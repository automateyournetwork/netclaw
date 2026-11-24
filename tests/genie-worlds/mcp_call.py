"""Single actual stdio call for the browser/member-boundary qualification."""
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server = Path(__file__).resolve().parents[2] / 'mcp-servers/genie-worlds-mcp/server.py'
    params = StdioServerParameters(command=sys.executable, args=[str(server)], env={
        'PATH': os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1',
        'NETCLAW_GENIE_CONTROL_FILE': os.environ['NETCLAW_GENIE_CONTROL_FILE']})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(sys.argv[1], json.loads(sys.argv[2]))
            if result.is_error: raise RuntimeError('MCP call refused')
            payload = result.structured_content
            if payload is None:
                payload = json.loads(next(x.text for x in result.content if x.type == 'text'))
            print(json.dumps(payload))

if __name__ == '__main__': asyncio.run(main())
