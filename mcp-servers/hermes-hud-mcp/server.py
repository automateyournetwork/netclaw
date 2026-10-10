#!/usr/bin/env python3
"""HUD-private stdio MCP. Never register these tools with the agent itself."""
import os
from functools import lru_cache, wraps
from fastmcp import FastMCP
from bridge import Bridge, sanitize
from ledger import HudError

mcp=FastMCP('NetClaw Hermes HUD', strict_input_validation=True)
def safe_errors(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        try:return fn(*args,**kwargs)
        except HudError as error:return {'error':{'code':error.code,'message':str(error)},'mayHaveExecuted':fn.__name__=='hermes_hud_submit'}
        except Exception:return {'error':{'code':'upstream_failed','message':'Private bridge operation unavailable. Check status; do not resend uncertain work.'},'mayHaveExecuted':fn.__name__=='hermes_hud_submit'}
    return wrapped

@lru_cache(maxsize=1)
def bridge():
    home=os.environ.get('HERMES_HOME');installation=os.environ.get('NETCLAW_HUD_INSTALLATION_ID')
    if not home or not installation:raise HudError('configuration_missing')
    return Bridge(home,installation)

def scoped(installationId):
    client=bridge();client.ledger.scope(installationId);return client

@mcp.tool()
@safe_errors
def hermes_hud_status(installationId:str)->dict:
    """Read selected protected-companion readiness; never starts inference."""
    return scoped(installationId).status()

@mcp.tool()
@safe_errors
def hermes_hud_conversation_open(installationId:str,conversationId:str,seed:list[dict]|None=None,seedDigest:str|None=None,acknowledgedUncertainRequestId:str|None=None)->dict:
    """Create an owned session, optionally seeding a validated Canvas ancestor prefix."""
    from ledger import digest
    if seedDigest and seedDigest!=digest(seed or []):raise HudError('input_invalid')
    return scoped(installationId).open(conversationId,seed,acknowledgedUncertainRequestId)

@mcp.tool()
@safe_errors
def hermes_hud_history(installationId:str,conversationId:str,cursor:int=0,limit:int=200)->dict:
    """Read one mapped conversation's sanitized visible transcript."""
    return scoped(installationId).history(conversationId,cursor,limit)

@mcp.tool()
@safe_errors
def hermes_hud_submit(installationId:str,conversationId:str,requestId:str,clientNonce:str,text:str,deadlineMs:int=900000,bodyDigest:str|None=None)->dict:
    """Durably admit at most one run; ambiguous submissions are never replayed."""
    from ledger import digest
    if bodyDigest and bodyDigest!=digest({'text':text,'conversation':conversationId}):raise HudError('input_invalid')
    return scoped(installationId).submit(conversationId,requestId,clientNonce,text,deadlineMs)

@mcp.tool()
@safe_errors
def hermes_hud_request_status(installationId:str,conversationId:str,requestId:str)->dict:
    """Reconcile a known run without submitting more work."""
    return scoped(installationId).request_status(conversationId,requestId)

@mcp.tool()
@safe_errors
def hermes_hud_events(installationId:str,conversationId:str,requestId:str,cursor:int=0)->dict:
    """Page durable correlated invocation events, excluding private reasoning."""
    events=scoped(installationId).ledger.events(conversationId,requestId,cursor)
    return {'events':sanitize(events),'cursor':events[-1]['sequence'] if events else cursor,'gap':False}

@mcp.tool()
@safe_errors
def hermes_hud_approval(installationId:str,conversationId:str,requestId:str,approvalId:str,choice:str)->dict:
    """Resolve exactly one current owned approval, once or deny only."""
    return scoped(installationId).approval(conversationId,requestId,approvalId,choice)

@mcp.tool()
@safe_errors
def hermes_hud_stop(installationId:str,conversationId:str,requestId:str)->dict:
    """Request cooperative stop; acknowledgment is not proof of cancellation."""
    return scoped(installationId).stop(conversationId,requestId)

if __name__=='__main__':
    os.umask(0o077)
    mcp.run(transport='stdio',show_banner=False)
