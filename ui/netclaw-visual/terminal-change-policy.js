import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { activityText } from './terminal-intent-live.js';
import { createMigrationVault } from './terminal-migration-artifacts.js';

const fail = (message, status = 400) => Object.assign(new Error(message), { status });
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const endpoint = d => ({ id: d.id, name: d.alias || d.name || d.id, host: d.host, port: d.port, protocol: d.protocol });
const sameEndpoint = (a, b) => a && b && a.id === b.id && a.host === b.host && a.port === b.port && a.protocol === b.protocol;
const validId = id => /^[a-f0-9-]{36}$/i.test(id || '');

function atomicJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.${crypto.randomUUID()}.tmp`;
  let fd;
  try {
    fd = fs.openSync(temporary, 'wx', 0o600);
    fs.writeFileSync(fd, JSON.stringify(data, null, 2)); fs.fsyncSync(fd);
    fs.closeSync(fd); fd = undefined;
    fs.renameSync(temporary, file);
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

export function createLocalChangePolicy({ directory, listDevices }) {
  const migrationVault = createMigrationVault(directory);
  const root = () => typeof directory === 'function' ? directory() : directory;
  const policyFile = () => path.join(root(), 'policy.json');
  const readPolicy = () => {
    try {
      const data = JSON.parse(fs.readFileSync(policyFile(), 'utf8'));
      if (data.version !== 1 || typeof data.enabled !== 'boolean' || !Array.isArray(data.devices) || data.devices.length > 100 || !validId(data.revision) ||
          data.devices.some(d => !d || typeof d.id !== 'string' || !d.id || typeof d.host !== 'string' || !d.host || d.protocol !== 'ssh' || !Number.isInteger(d.port) || d.port < 1 || d.port > 65535) ||
          new Set(data.devices.map(d => d.id)).size !== data.devices.length) throw new Error('Invalid policy');
      return data;
    } catch (error) {
      if (error.code === 'ENOENT') return { version: 1, revision: 'initial', devices: [], enabled: false };
      throw fail('Local change policy cannot be read. Lab changes are disabled until it is repaired.', 503);
    }
  };
  const recordFile = id => {
    if (!validId(id)) throw fail('Invalid change record ID.');
    return path.join(root(), 'records', id, 'record.json');
  };
  const readRecord = id => {
    try { return JSON.parse(fs.readFileSync(recordFile(id), 'utf8')); }
    catch (error) { if (error.code === 'ENOENT') return null; throw error; }
  };
  function audit(id, kind, detail) {
    const file = path.join(path.dirname(recordFile(id)), 'events.jsonl');
    const fd = fs.openSync(file, 'a', 0o600);
    try { fs.writeFileSync(fd, JSON.stringify({ at: new Date().toISOString(), kind, detail }) + '\n'); fs.fsyncSync(fd); }
    finally { fs.closeSync(fd); }
  }
  function validate(change) {
    const policy = readPolicy();
    if (!policy.enabled || policy.revision !== change.revision) throw fail('Lab authorization changed. No further work segment was submitted.', 409);
    const live = listDevices();
    for (const d of change.devices) {
      if (!sameEndpoint(d, policy.devices.find(p => p.id === d.id)) || !sameEndpoint(d, live.find(p => p.id === d.id))) {
        throw fail(`Lab endpoint changed or is no longer authorized: ${d.id}. Reauthorize it in Change control.`, 409);
      }
    }
  }
  return {
    migrationInventories: () => migrationVault.inventories(),
    captureCandidate: input => migrationVault.capture(input),
    state() {
      const policy = readPolicy();
      const live = listDevices();
      return { ...policy, defaultMode: 'production', recordDirectory: path.join(root(), 'records'), devices: policy.devices.map(d => ({ ...d, valid: sameEndpoint(d, live.find(p => p.id === d.id)) })) };
    },
    save(input) {
      const previous = readPolicy();
      if (input.revision !== previous.revision) throw fail('Change control settings changed; reload before saving.', 409);
      if (typeof input.enabled !== 'boolean') throw fail('Choose whether Local/Lab changes are enabled.');
      if (!Array.isArray(input.deviceIds)) throw fail('Select the lab device IDs.');
      const ids = [...new Set(input.deviceIds)];
      if (ids.length > 100 || ids.some(id => typeof id !== 'string') || (input.enabled && (!ids.length || input.confirmLab !== true))) throw fail('Explicitly confirm the selected devices are your lab devices.');
      const inventory = listDevices();
      const devices = input.enabled ? ids.map(id => {
        const d = inventory.find(item => item.id === id);
        if (!d?.supported || d.protocol !== 'ssh' || !d.host || !Number.isInteger(d.port) || d.port < 1 || d.port > 65535) throw fail(`Select an available SSH lab device: ${id}.`);
        return endpoint(d);
      }) : [];
      const next = { version: 1, revision: crypto.randomUUID(), enabled: input.enabled, devices, authorizedAt: new Date().toISOString() };
      atomicJson(policyFile(), next);
      return this.state();
    },
    resolve(input) {
      if (!input.changeMode || input.changeMode === 'production') {
        if (input.migration) throw fail('Private artifact application currently requires the Local/Lab workflow.');
        return { mode: 'production' };
      }
      if (input.changeMode !== 'local-lab') throw fail('Unknown change-control mode.');
      const policy = readPolicy();
      const ids = input.targetDeviceIds;
      if (!Array.isArray(ids) || !ids.length || ids.length > 100 || new Set(ids).size !== ids.length) throw fail('Select the lab devices for this request.');
      if (input.policyRevision !== policy.revision) throw fail('Lab settings changed; reload Change control before submitting.', 409);
      const devices = ids.map(id => {
        const d = policy.devices.find(item => item.id === id);
        if (!d) throw fail(`Device ${id} is not explicitly authorized for Local/Lab changes.`, 403);
        return d;
      });
      const change = { mode: 'local-lab', revision: policy.revision, devices };
      validate(change);
      if (input.migration) change.migration = migrationVault.bind(input.migration, devices);
      return change;
    },
    begin(id, input, scope) {
      if (readRecord(id)) throw fail('This local change ID already exists on disk. Check its outcome; it will not be replayed.', 409);
      const dir = path.dirname(recordFile(id));
      fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
      const devices = scope.devices.map(d => ({ ...d,
        baselinePath: path.join(dir, `${hash(d.id).slice(0, 16)}-baseline.txt`),
        rollbackPath: path.join(dir, `${hash(d.id).slice(0, 16)}-rollback.txt`),
      }));
      const record = { ...scope, id, devices, phase: 'prepare', status: 'running', createdAt: new Date().toISOString(),
        request: activityText(input.request, 4000), requestHash: hash(input.request),
        authorization: 'Explicit operator request through Local/Lab Intent; only the stated task on selected lab endpoints. Questions authorize no writes.',
      };
      atomicJson(recordFile(id), record);
      audit(id, 'request-accepted', { requestHash: record.requestHash, deviceIds: devices.map(d => d.id) });
      return { ...record, recordPath: recordFile(id) };
    },
    validate,
    prepared(change, report) {
      validate(change);
      const artifacts = [];
      for (const device of change.devices) {
        for (const field of ['baseline', 'rollback']) {
          if (!report[field]?.some(item => item.device === device.id && item.summary)) throw fail(`Missing ${field} evidence for ${device.id}.`, 409);
          const file = device[`${field}Path`];
          let stat;
          try { stat = fs.lstatSync(file); } catch { throw fail(`Save the ${field} artifact for ${device.id} before applying changes.`, 409); }
          if (!stat.isFile() || stat.isSymbolicLink() || stat.size < 8 || stat.size > 4 * 1024 * 1024 || fs.realpathSync(path.dirname(file)) !== path.resolve(path.dirname(file))) throw fail(`Invalid ${field} artifact for ${device.id}.`, 409);
          artifacts.push({ device: device.id, kind: field, sha256: hash(fs.readFileSync(file)), bytes: stat.size });
        }
      }
      if(change.migration) for(const device of change.devices)migrationVault.verifyBaseline(change,device);
      audit(change.id, 'baseline-and-rollback-recorded', artifacts);
      const next = { ...readRecord(change.id), phase: 'apply', artifacts };
      if (next.migration) {
        next.applyRevision = crypto.randomUUID();
        next.applyGrants = [crypto.randomUUID().replaceAll('-', '')];
      }
      atomicJson(recordFile(change.id), next);
      if (next.migration) migrationVault.issue(next);
      return { ...change, ...next };
    },
    record(change, report, status) {
      // Only bounded/redacted reports, never transcript/config/secret payloads.
      const safe = { status, summary: activityText(report?.summary || '', 12000),
        actions: (report?.actions || []).map(a => ({ device: activityText(a.device, 256), kind: a.kind, summary: activityText(a.summary, 2000) })),
        verification: (report?.verification || []).map(v => ({ device: activityText(v.device, 256), summary: activityText(v.summary, 2000) })),
      };
      audit(change.id, 'agent-report', safe);
      atomicJson(recordFile(change.id), { ...readRecord(change.id), phase: change.phase, status, updatedAt: new Date().toISOString(), report: safe });
    },
    get: readRecord,
  };
}
