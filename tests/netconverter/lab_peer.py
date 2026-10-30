"""Controlled CML-shaped MCP peer. No real lab provider, images or device calls."""
import json
from pathlib import Path
import sys
from fastmcp import FastMCP
root=Path(sys.argv[1]);mcp=FastMCP('controlled-rehearsal-peer')
def audit(tool,args):
    with (root/'calls.jsonl').open('a') as f:f.write(json.dumps({'tool':tool,'arguments':args})+'\n')
@mcp.tool()
def get_cml_node_definitions()->dict:
    audit('get_cml_node_definitions',{});return {'definitions':[{'id':'synthetic-router','image':'synthetic-installed-image','architecture':'fixture','licensed':'fixture-only'}]}
@mcp.tool()
def create_empty_lab(title:str,description:str)->dict:
    audit('create_empty_lab',{'title':title,'description':description})
    ownership=json.loads(description)
    result={'id':'fixture-lab-uuid','ownership':ownership,'state':'DEFINED'}
    (root/'lab.json').write_text(json.dumps(result))
    if (root/'lose-response').exists():raise RuntimeError('Synthetic lost response after creation')
    return result
@mcp.tool()
def get_cml_labs()->dict:
    audit('get_cml_labs',{});return {'labs':[json.loads((root/'lab.json').read_text())] if (root/'lab.json').exists() else []}
@mcp.tool()
def add_node_to_cml_lab(lab_id:str,node_definition:str,label:str)->dict:
    assert lab_id=='fixture-lab-uuid' and node_definition=='synthetic-router'
    audit('add_node_to_cml_lab',{'lab_id':lab_id,'node_definition':node_definition,'label':label});return {'id':'fixture-node-uuid'}
@mcp.tool()
def start_cml_lab(lab_id:str)->dict:
    assert lab_id=='fixture-lab-uuid';audit('start_cml_lab',{'lab_id':lab_id});return {'state':'STARTED'}
@mcp.tool()
def get_nodes_for_cml_lab(lab_id:str)->dict:
    audit('get_nodes_for_cml_lab',{'lab_id':lab_id});return {'nodes':[{'id':'fixture-node-uuid','state':'BOOTED','management':'192.0.2.12'}]}
if __name__=='__main__':mcp.run(transport='stdio')
