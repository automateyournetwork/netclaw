import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
import {environment} from './configuration.js';
import {invariant,fail} from './errors.js';

const tools=new Set(['rag_list','rag_stats','rag_search','rag_ingest']);
const messages={MODELS_NOT_CACHED:'RAG embedding or reranking models are not cached on the backend.',UNSUPPORTED_FORMAT:'This document format is not supported by the backend.',PARSE_FAILED:'The backend could not parse this document.',CONVERTER_UNAVAILABLE:'This document requires the backend LibreOffice converter.',REPLACEMENT_REQUIRED:'A document with this title already exists. Review that document before replacing it.',STALE_DOCUMENT:'The document changed since review. Refresh and review it again.',STORAGE_UNAVAILABLE:'The RAG store is unavailable.',SIZE_LIMIT_EXCEEDED:'The document exceeds the backend limit.'};
export class RagToolError extends Error {constructor(code){super(messages[code]||'The RAG backend could not complete the request.');this.code=Object.hasOwn(messages,code)?code:'RAG_UNAVAILABLE';}}

/** Fixed existing MCP integration. No executable, URL or tool names from webviews. */
export class RagClient {
  constructor(binding,root){this.binding=binding;this.root=root;}
  async call(name,args={}){
    invariant(tools.has(name),'DENIED');this.binding.assertCurrent();
    const env=environment(this.binding),configured=env.RAG_DATA_DIR;
    const directory=configured?configured.replace(/^~(?=\/)/,os.homedir()):path.join(this.binding.home,'rag');
    invariant(path.isAbsolute(directory));
    const python=env.RAG_MCP_PYTHON||process.env.NETCLAW_HUD_BRIDGE_PYTHON||'python3';
    invariant(python==='python3'||path.isAbsolute(python));
    const client=new Client({name:'netclaw-operator-rag',version:'1.0.0'});
    // Models are installation prerequisites. Opening/searching this panel cannot fetch models.
    const childEnv={...process.env,...env,RAG_DATA_DIR:directory,HF_HUB_OFFLINE:'1',TRANSFORMERS_OFFLINE:'1',ANONYMIZED_TELEMETRY:'False',PYTHONUNBUFFERED:'1'};
    const transport=new StdioClientTransport({command:python,args:['-u',path.join(this.root,'mcp-servers/rag-mcp/rag_mcp_server.py')],cwd:path.join(this.binding.statePath,'management'),env:childEnv,stderr:'ignore'});
    try{
      await client.connect(transport,{timeout:20000});
      const result=await client.callTool({name,arguments:args},{timeout:name==='rag_ingest'?600000:120000});
      invariant(!result.isError,'SOURCE_UNAVAILABLE');
      const value=result.structuredContent||JSON.parse(result.content?.find(v=>v.type==='text')?.text||'{}');
      invariant(Buffer.byteLength(JSON.stringify(value))<=4*1024*1024);
      if(value.success!==true)throw new RagToolError(value.error?.code);
      return value.data;
    }catch(error){if(error instanceof RagToolError)throw error;fail('SOURCE_UNAVAILABLE');}
    finally{await client.close().catch(()=>{});}
  }
}
