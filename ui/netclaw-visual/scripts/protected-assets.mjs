import fs from 'node:fs';
import path from 'node:path';
import { buildProtectedManifest, noSymlink, sha256 } from '../src/hud-server/protected-assets.js';

try {
  const args = process.argv.slice(2);
  const workspace = args.length === 5 && args[4] === '--workspace';
  if ((args.length !== 4 && !workspace) || args[0] !== '--dist' || args[2] !== '--output' || !path.isAbsolute(args[1]) || !path.isAbsolute(args[3])) throw Error('arguments');
  const bytes = JSON.stringify(buildProtectedManifest(args[1], { workspace }), null, 2) + '\n';
  noSymlink(path.dirname(args[3]));
  fs.writeFileSync(args[3], bytes, { flag: 'wx', mode: 0o600 });
  console.log(JSON.stringify({ manifestSha256: sha256(bytes) }));
} catch { console.error('Protected asset manifest refused; verify the explicit build and output paths.'); process.exitCode = 1; }
