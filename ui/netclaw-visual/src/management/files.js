import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { invariant } from './errors.js';

export function ownedDirectory(directory, { privateMode = true, create = false } = {}) {
  invariant(path.isAbsolute(directory));
  if (create && !fs.existsSync(directory)) fs.mkdirSync(directory, { mode: 0o700 });
  const stat = fs.lstatSync(directory);
  invariant(stat.isDirectory() && !stat.isSymbolicLink() && stat.uid === process.getuid?.(), 'DENIED');
  invariant(!privateMode || !(stat.mode & 0o077), 'DENIED');
  invariant(fs.realpathSync(directory) === path.resolve(directory), 'DENIED');
  return stat;
}
export function ownedFile(file,{privateMode=true}={}){
  const stat=fs.lstatSync(file);
  invariant(stat.isFile()&&!stat.isSymbolicLink()&&stat.uid===process.getuid?.(),'DENIED');
  invariant(!privateMode||!(stat.mode&0o077),'DENIED');
  invariant(fs.realpathSync(path.dirname(file))===path.resolve(path.dirname(file)),'DENIED');
  return stat;
}
export function readOwned(file, { limit = 1024 * 1024, privateMode = true, missing = false } = {}) {
  try {
    const stat = ownedFile(file,{privateMode});
    invariant(stat.size <= limit, 'INVALID_INPUT');
    const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    try {
      const actual = fs.fstatSync(fd);
      invariant(actual.ino === stat.ino && actual.dev === stat.dev, 'STALE_REVISION');
      invariant(actual.size<=limit);
      // Bound allocation even if another process grows the file after lstat.
      const chunks=[];let total=0;
      while(total<=limit){const chunk=Buffer.allocUnsafe(Math.min(65536,limit-total+1));const count=fs.readSync(fd,chunk,0,chunk.length,null);if(!count)break;total+=count;invariant(total<=limit);chunks.push(chunk.subarray(0,count));}
      return Buffer.concat(chunks,total);
    } finally { fs.closeSync(fd); }
  } catch (error) { if (missing && error.code === 'ENOENT') return null; throw error; }
}
export function atomicPrivate(file, data) {
  ownedDirectory(path.dirname(file));
  readOwned(file, { missing: true, limit: 32 * 1024 * 1024 });
  const temp = `${file}.${randomUUID()}.tmp`;
  const fd = fs.openSync(temp, 'wx', 0o600);
  try { fs.writeFileSync(fd, data); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  try {
    fs.renameSync(temp, file);
    const parent = fs.openSync(path.dirname(file), fs.constants.O_RDONLY);
    try { fs.fsyncSync(parent); } finally { fs.closeSync(parent); }
  } finally { if (fs.existsSync(temp)) fs.unlinkSync(temp); }
}
