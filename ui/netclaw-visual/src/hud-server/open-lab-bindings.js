import fs from 'node:fs';
import path from 'node:path';
import { Bindings, safeId } from './bindings.js';
import { writePrivateAtomic } from '../security/private-files.js';

const LIMIT = 8 * 1024 * 1024;
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const unavailable = () => { throw Error('Shared lab conversation state unavailable'); };

// This is deliberately not an authentication context. Every visitor to the
// explicitly enabled lab shares these conversations; request headers confer no
// identity or authority. Protected operation approvals use their own ledger.
export function labConversationContext(_request) { return undefined; }

export class OpenLabBindings extends Bindings {
  constructor(directory, clock = Date.now, installation) {
    if (!installation || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(installation.installationId) ||
        !['openclaw', 'hermes'].includes(installation.kind) || !path.isAbsolute(directory) || path.normalize(directory) !== directory) unavailable();
    super(directory, clock, Object.freeze({ installationId: installation.installationId, kind: installation.kind }));
    this.cookieName = undefined;
    this.openLab = true;
  }

  ensure() {
    // Check existing ancestors before mkdir: recursive creation must never
    // traverse a symlink into another installation's private state.
    for (let current = this.directory; ; current = path.dirname(current)) {
      try { if (fs.lstatSync(current).isSymbolicLink()) unavailable(); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      if (current === path.dirname(current)) break;
    }
    fs.mkdirSync(this.directory, { recursive: true, mode: 0o700 });
    const stat = fs.lstatSync(this.directory);
    if (!stat.isDirectory() || stat.isSymbolicLink() || stat.uid !== process.getuid() || (stat.mode & 0o777) !== 0o700) unavailable();
  }

  file(_context) { this.ensure(); return path.join(this.directory, 'lab-conversations.json'); }

  inspect(file) {
    const stat = fs.lstatSync(file);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.nlink !== 1 || stat.uid !== process.getuid() ||
        (stat.mode & 0o777) !== 0o600 || stat.size > LIMIT) unavailable();
    return stat;
  }

  validate(state) {
    if (!plain(state) || state.version !== 1 || state.mode !== 'open-lab' ||
        state.installationId !== this.installation.installationId || state.runtime !== this.installation.kind ||
        Object.keys(state).some(key => !['version', 'mode', 'installationId', 'runtime', 'tasks', 'acknowledged'].includes(key)) ||
        !plain(state.tasks) || Object.keys(state.tasks).length > 500) unavailable();
    for (const [id, task] of Object.entries(state.tasks)) {
      if (!/^[a-f0-9]{48}$/.test(id) || !plain(task) || task.id !== id || !/^[a-f0-9]{64}$/.test(task.thread) ||
          typeof task.gatewayKey !== 'string' || !new RegExp(`^agent:[a-zA-Z0-9][a-zA-Z0-9_-]*:hud:${id}$`).test(task.gatewayKey) ||
          !Number.isSafeInteger(task.createdAt) || task.createdAt < 0 || !plain(task.assessments) || Object.keys(task.assessments).length > 500 ||
          task.publicThread !== undefined && !safeId(task.publicThread) || task.resumeThread !== undefined && !safeId(task.resumeThread) ||
          task.requests !== undefined && (!plain(task.requests) || Object.keys(task.requests).length > 500)) unavailable();
    }
    if (state.acknowledged !== undefined && (!Array.isArray(state.acknowledged) || state.acknowledged.length > 500 || state.acknowledged.some(id => !safeId(id)))) unavailable();
    return state;
  }

  read(_context) {
    const file = this.file();
    let before;
    try { before = this.inspect(file); }
    catch (error) {
      if (error.code !== 'ENOENT') throw error;
      // Reading an empty lab does not create a login/session or import any
      // legacy cookie state. The first explicit conversation persists it.
      return { version: 1, mode: 'open-lab', installationId: this.installation.installationId, runtime: this.installation.kind, tasks: {} };
    }
    const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    try {
      const after = fs.fstatSync(fd);
      if (after.dev !== before.dev || after.ino !== before.ino || after.size !== before.size || !after.isFile() ||
          after.nlink !== 1 || after.uid !== process.getuid() || (after.mode & 0o777) !== 0o600 || after.size > LIMIT) unavailable();
      const bytes = Buffer.alloc(before.size + 1);
      let length = 0, count;
      while ((count = fs.readSync(fd, bytes, length, bytes.length - length, null)) > 0) {
        length += count;
        if (length > before.size) unavailable();
      }
      if (length !== before.size) unavailable();
      return this.validate(JSON.parse(bytes.subarray(0, length).toString('utf8')));
    } finally { fs.closeSync(fd); }
  }

  save(_context, state) {
    const data = JSON.stringify(this.validate(state));
    if (Buffer.byteLength(data, 'utf8') > LIMIT) unavailable();
    const file = this.file();
    // Refuse an existing foreign/legacy record even if a caller supplies a new
    // locally valid object. This is never an installation migration mechanism.
    this.read();
    writePrivateAtomic(file, data);
  }

  begin(_context, taskId) {
    if (!safeId(taskId) || !Object.hasOwn(this.read().tasks, taskId)) unavailable();
    if (this.busy.has(taskId)) throw Error('Thread has an active request');
    this.busy.add(taskId);
    return () => this.busy.delete(taskId);
  }

  create() { throw Error('Open lab conversations do not use sessions'); }
  revoke() { throw Error('Open lab conversations do not use sessions'); }
}

export const createOpenLabBindings = (directory, installation, clock = Date.now) => new OpenLabBindings(directory, clock, installation);
