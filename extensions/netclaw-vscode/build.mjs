import { build } from 'esbuild';
import path from 'node:path';
import { mkdir,copyFile } from 'node:fs/promises';
await build({ entryPoints: ['src/extension.ts'], outfile: 'dist/extension.cjs', bundle: true,
  platform: 'node', format: 'cjs', target: 'node22', external: ['vscode'], sourcemap: false,
  legalComments: 'linked', metafile: true }).then(async result => {
  const { writeFile } = await import('node:fs/promises');
  await writeFile('dist/build-inputs.json', JSON.stringify(Object.keys(result.metafile.inputs).sort(), null, 2));
});
await build({entryPoints:['webview/avatar.jsx'],outfile:'dist/avatar.js',bundle:true,platform:'browser',format:'iife',target:'es2022',minify:true,legalComments:'linked',
  nodePaths:[path.resolve('../../ui/netclaw-visual/node_modules')],define:{'process.env.NODE_ENV':'"production"'}});
await mkdir('resources/pal',{recursive:true});
await build({entryPoints:['webview/canvas.js'],outfile:'dist/canvas.js',bundle:true,platform:'browser',format:'iife',target:'es2022',legalComments:'linked'});
for(const file of ['john.glb','john.png','lobster.glb','lobster.png','manifest.json'])await copyFile(`../../ui/netclaw-visual/public/pal/${file}`,`resources/pal/${file}`);
