import { build } from 'esbuild';
import vm from 'node:vm';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
export async function sourceModule(file,vscode={}){
  const result=await build({entryPoints:[new URL('../src/'+file,import.meta.url).pathname],bundle:true,write:false,platform:'node',format:'cjs',target:'node22',external:['vscode','@modelcontextprotocol/client','@modelcontextprotocol/client/stdio']});
  const module={exports:{}};
  vm.runInNewContext(result.outputFiles[0].text,{module,exports:module.exports,process,Buffer,require:id=>id==='vscode'?vscode:require(id)});
  return module.exports;
}
