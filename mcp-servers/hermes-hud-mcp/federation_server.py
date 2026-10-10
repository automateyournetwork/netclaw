#!/usr/bin/env python3
"""Private NCFED runtime MCP. Never register with a Hermes agent."""
import os
from functools import lru_cache
from fastmcp import FastMCP
from bridge import Bridge
from ledger import HudError
from server import safe_errors

mcp=FastMCP('NetClaw Hermes Federation Runtime',strict_input_validation=True)

@lru_cache(maxsize=1)
def bridge():
    home=os.environ.get('HERMES_HOME');installation=os.environ.get('NETCLAW_INSTALLATION_ID')
    if not home or not installation:raise HudError('configuration_missing')
    return Bridge(home,installation,namespace='federation')

def scoped(installationId):
    client=bridge();client.ledger.scope(installationId);return client

@mcp.tool()
@safe_errors
def hermes_federation_status(installationId:str)->dict:
    return scoped(installationId).status()

@mcp.tool()
@safe_errors
def hermes_federation_open(installationId:str,conversationId:str)->dict:
    return scoped(installationId).open(conversationId)

@mcp.tool()
@safe_errors
def hermes_federation_submit(installationId:str,conversationId:str,requestId:str,text:str,scope:dict,permit:str,deadlineMs:int=300000)->dict:
    return scoped(installationId).submit(conversationId,requestId,requestId,text,deadlineMs,scope,permit)

@mcp.tool()
@safe_errors
def hermes_federation_request_status(installationId:str,conversationId:str,requestId:str)->dict:
    return scoped(installationId).request_status(conversationId,requestId)

@mcp.tool()
@safe_errors
def hermes_federation_history(installationId:str,conversationId:str)->dict:
    return scoped(installationId).history(conversationId)

@mcp.tool()
@safe_errors
def hermes_federation_stop(installationId:str,conversationId:str,requestId:str)->dict:
    return scoped(installationId).stop(conversationId,requestId)

if __name__=='__main__':
    os.umask(0o077)
    mcp.run(transport='stdio',show_banner=False)
