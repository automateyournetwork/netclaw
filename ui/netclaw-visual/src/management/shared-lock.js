import fs from 'node:fs';
import path from 'node:path';
import { Journal } from './journal.js';
import { readOwned } from './files.js';

/** Existing HUD/CLI writers participate once this installation is managed. */
export function withManagementConfigurationLock(home, callback) {
  const state=path.join(home,'netclaw-hud'),directory=path.join(state,'management');
  if(!fs.existsSync(path.join(directory,'operations.sqlite')))return callback();
  const identity=JSON.parse(readOwned(path.join(state,'installation.json')));
  const journal=new Journal(directory,identity.installationId);
  let token;
  try{token=journal.lock('configuration',`existing-client:${process.pid}`);return callback();}
  finally{if(token)journal.unlock('configuration',token);journal.close();}
}
