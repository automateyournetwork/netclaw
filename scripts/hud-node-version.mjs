import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
const policy=JSON.parse(fs.readFileSync(new URL('../config/installer-runtime.json',import.meta.url),'utf8'));
const compare=(a,b)=>a.reduce((n,v,i)=>n || Math.sign(v-(b[i] || 0)),0);
export function supportsHudNode(version=process.versions.node) {
  const values=version.replace(/^v/,'').split('.').map(Number);
  return values.length===3 && values.every(Number.isInteger) && policy.node_ranges.hud.some(r=>compare(values,r.min)>=0 && (!r.max_exclusive || compare(values,r.max_exclusive)<0));
}
if(process.argv[1]===fileURLToPath(import.meta.url) && !supportsHudNode()) {
  console.error('HUD requires Node '+policy.node_descriptions.hud);process.exitCode=1;
}
