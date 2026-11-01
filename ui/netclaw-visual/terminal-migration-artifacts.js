import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const LIMIT = 2 * 1024 * 1024;
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const fail = () => Object.assign(new Error('Migration artifact or active pyATS binding is unavailable or changed. Review it again.'), { status: 409 });
const id = value => { if (!/^[a-f0-9-]{32,36}$/.test(value || '')) throw fail(); return value; };
const same = (a, b) => a && b && ['id', 'host', 'port', 'protocol'].every(k => a[k] === b[k]);

// The local OS owner remains trusted. Refuse symlinks, nonregular files,
// hardlinks, public vaults and changing reads; never return candidate bytes.
function checkDirectory(dir) {
  if (!path.isAbsolute(dir) || fs.realpathSync(dir) !== path.resolve(dir)) throw fail();
  const st = fs.statSync(dir);
  if (st.uid !== process.getuid() || (st.mode & 0o077)) throw fail();
}
function read(file, limit = 8 * LIMIT) {
  if (fs.realpathSync(path.dirname(file)) !== path.resolve(path.dirname(file))) throw fail();
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const before = fs.fstatSync(fd);
    if (!before.isFile() || before.nlink !== 1 || before.uid !== process.getuid() || before.size > limit) throw fail();
    const data = fs.readFileSync(fd), after = fs.fstatSync(fd);
    if (data.length > limit || ['ino','dev','size','mtimeMs','ctimeMs'].some(k => before[k] !== after[k])) throw fail();
    return data;
  } finally { fs.closeSync(fd); }
}
function write(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); checkDirectory(path.dirname(file));
  const fd = fs.openSync(file, 'wx', 0o600);
  try { fs.writeFileSync(fd, data); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}

export function createMigrationVault(directory) {
  const root = () => {
    const dir = typeof directory === 'function' ? directory() : directory;
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 }); checkDirectory(dir); return dir;
  };
  function inventory(ref) {
    const item = JSON.parse(read(path.join(root(), 'inventories', id(ref) + '.json')));
    if (item.schema !== 1 || item.harness !== ref || item.installation !== hash(root()) ||
        !Number.isInteger(item.pid) || item.pid <= 0 || Date.now()/1000 - item.observed > 300 || item.observed > Date.now()/1000 + 5 ||
        !Array.isArray(item.devices) || item.devices.length > 1000) throw fail();
    try { process.kill(item.pid, 0); } catch { throw fail(); }
    return item;
  }
  function candidate(ref) {
    const metadata = JSON.parse(read(path.join(root(), 'candidates', id(ref) + '.json')));
    const data = read(path.join(root(), 'candidates', ref + '.cfg'), LIMIT);
    if (metadata.artifact_ref !== ref || metadata.sha256 !== hash(data) || metadata.bytes !== data.length) throw fail();
    return metadata;
  }
  return {
    inventories() {
      const dir = path.join(root(), 'inventories');
      if (!fs.existsSync(dir)) return [];
      return fs.readdirSync(dir).filter(f => /^[a-f0-9]{32}\.json$/.test(f)).flatMap(f => {
        try { return [inventory(f.slice(0, -5))]; } catch { return []; }
      });
    },
    capture(input) {
      if (typeof input?.content !== 'string' || input.content.includes('\0')) throw fail();
      const data = Buffer.from(input.content);
      if (data.length < 8 || data.length > LIMIT) throw fail();
      const ref = crypto.randomUUID().replaceAll('-', '');
      const meta = { artifact_ref: ref, sha256: hash(data), bytes: data.length };
      write(path.join(root(), 'candidates', ref + '.cfg'), data);
      write(path.join(root(), 'candidates', ref + '.json'), JSON.stringify(meta));
      return meta;
    },
    verifyBaseline(record, device) {
      const m=record.migration;
      if (!m || path.dirname(device.baselinePath) !== path.join(root(),'records',id(record.id))) throw fail();
      const receipt=JSON.parse(read(device.baselinePath+'.receipt.json',65536));
      if(receipt.schema!==1 || receipt.record!==record.id || receipt.installation!==m.installation ||
         receipt.harness!==m.harness || receipt.testbed!==m.testbed || !same(receipt.endpoint,device)) throw fail();
      const artifact=receipt.artifact;
      const captured=read(path.join(root(),'artifacts',id(artifact?.artifact_ref)+'.artifact'),LIMIT);
      const baseline=read(device.baselinePath,LIMIT);
      if(artifact.role!=='running-configuration' || artifact.bytes!==captured.length ||
         artifact.sha256!==hash(captured) || baseline.length!==captured.length || hash(baseline)!==artifact.sha256) throw fail();
      return {sha256:artifact.sha256,bytes:artifact.bytes};
    },
    bind(input, devices) {
      if (!input) return undefined;
      if (devices.length !== 1 || !['ospf-routing-v1','firewall-policy-v1'].includes(input.profile)) throw fail();
      const reviewed = candidate(input.artifact_ref), current = inventory(input.harness);
      if (reviewed.sha256 !== input.sha256 || current.testbed !== input.testbed) throw fail();
      const endpoint = current.devices.find(d => same(d, devices[0]));
      if (!endpoint || endpoint.route !== 'pyats_configure_device' || !['ios','iosxe','junos'].includes(endpoint.os)) throw fail();
      return { candidate: reviewed, installation: current.installation, harness: current.harness,
        testbed: current.testbed, endpoint, profile: input.profile, tool: 'pyats_configure_device' };
    },
    issue(record) {
      const m = record.migration;
      if (!m || record.phase !== 'apply' || record.status !== 'running') throw fail();
      for(const device of record.devices)this.verifyBaseline(record,device);
      const rebound = this.bind({ ...m.candidate, harness:m.harness, testbed:m.testbed, profile:m.profile }, record.devices);
      if (JSON.stringify(rebound) !== JSON.stringify(m)) throw fail();
      const keyFile = path.join(root(), 'api-signing.key');
      if (!fs.existsSync(keyFile)) write(keyFile, crypto.randomBytes(32));
      const key = read(keyFile, 32); if (key.length !== 32) throw fail();
      const nonce = record.applyGrants[0], issued = Date.now()/1000;
      const claim = { schema:1, nonce, installation:m.installation, harness:m.harness, testbed:m.testbed,
        tool:m.tool, endpoint:m.endpoint, candidate:m.candidate, migration:m, profile:m.profile,
        record:record.id, task:record.id, revision:record.revision, applyRevision:record.applyRevision,
        requestHash:record.requestHash, artifacts:record.artifacts, issued, expires:issued+300 };
      const raw = Buffer.from(JSON.stringify(claim));
      write(path.join(root(), 'grants', id(nonce)+'.json'), JSON.stringify({ payload:raw.toString('base64'), signature:crypto.createHmac('sha256',key).update(raw).digest('hex') }));
      return nonce;
    },
  };
}
