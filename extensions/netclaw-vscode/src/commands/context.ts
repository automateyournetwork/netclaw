import * as vscode from 'vscode';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { Connection } from '../connection/connect';

export async function stageSelectedContext(connection:Connection):Promise<void>{
  if(!connection.ready)throw Error('Connect to a trusted installation before staging context.');
  const editor=vscode.window.activeTextEditor;
  if(!editor||editor.selection.isEmpty)throw Error('Select the exact text you want to share in an editor first.');
  const text=editor.document.getText(editor.selection);
  if(Buffer.byteLength(text)>1024*1024)throw Error('Selected text exceeds the 1 MiB staging limit. Select a smaller excerpt.');
  const generation=connection.generation,name=path.basename(editor.document.fileName);
  const preview=await vscode.workspace.openTextDocument({content:text,language:editor.document.languageId});
  await vscode.window.showTextDocument(preview,{preview:true,preserveFocus:false});
  const answer=await vscode.window.showInformationMessage(`Stage ${Buffer.byteLength(text).toLocaleString()} bytes for ${connection.profile?.label}?`,{modal:true,detail:'Review the selected text for credentials and private material. It becomes available to explicitly selected NetClaw requests; staging does not index the rest of the workspace.'},'Stage selected text');
  if(answer!=='Stage selected text')return;
  if(generation!==connection.generation)throw Error('Connection changed. Review the selection again.');
  await connection.call('operator_workspace',{action:'rag-stage',nonce:`${Date.now()}:${randomUUID()}`,args:{name,content:text}});
  void vscode.window.showInformationMessage('Context staged. Select it in Chat before sending your request.');
}
