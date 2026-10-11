import fs from 'node:fs';
import path from 'node:path';
import { randomUUID, createHash } from 'node:crypto';
import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { ownedDirectory, readOwned, atomicPrivate } from './files.js';
import { fail, invariant } from './errors.js';

const secretKey = /password|secret|api.?key|authorization|credential|^(?:token|accessToken|refreshToken|bearer|cookie)$/i;
export function redactor(secrets = []) {
  const values = [...new Set(secrets.filter(v => typeof v === 'string' && v.length > 0))].sort((a,b) => b.length-a.length);
  const text = value => {
    let result = value;
    for (const secret of values) result = result.split(secret).join('[redacted]');
    return result.replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, 'Bearer [redacted]')
      .replace(/\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{8,}/g, '[redacted]');
  };
  const visit = (value, depth = 0) => {
    if (depth > 16) return '[depth limit]';
    if (typeof value === 'string') return text(value).slice(0, 65536);
    if (Array.isArray(value)) return value.slice(0,500).map(item => visit(item, depth+1));
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).slice(0,500).map(([key,item]) => [key, secretKey.test(key) ? '[redacted]' : visit(item, depth+1)]));
    return value;
  };
  return visit;
}
export function bounded(value) {
  if (Buffer.byteLength(JSON.stringify(value)) <= 1024*1024) return value;
  return { available: false, truncated: true, reason: 'Response exceeded 1 MiB. Narrow the query or use pagination.' };
}
export class ArtifactStore {
  constructor(journal) { this.journal = journal; this.directory = path.join(journal.directory, 'artifacts'); ownedDirectory(this.directory, { create: true }); }
  write(owner, bytes, kind) {
    invariant(Buffer.byteLength(bytes) <= 20*1024*1024);
    const id = randomUUID(), hash = createHash('sha256').update(bytes).digest('hex');
    atomicPrivate(path.join(this.directory, id), bytes);
    this.journal.put('artifact', id, owner, { kind, hash, size: Buffer.byteLength(bytes) });
    return { id, hash, size: Buffer.byteLength(bytes), kind };
  }
  read(owner, id) {
    invariant(/^[a-f\d-]{36}$/.test(id));
    const record = this.journal.record('artifact', id, owner);
    const bytes = readOwned(path.join(this.directory, id), { limit: 20*1024*1024 });
    invariant(createHash('sha256').update(bytes).digest('hex') === record.hash, 'STALE_REVISION');
    return bytes;
  }
}

/** Dedicated MCP process, cwd, sticky file and GAIT root for each installation. */
export class InstallationAudit {
  constructor(binding, root, journal, environment = process.env) {
    this.binding = binding; this.root = root; this.journal = journal; this.environment = environment;
    this.directory = path.join(journal.directory, 'audit'); this.queue = Promise.resolve();
  }
  async connect() {
    if (this.client) return;
    ownedDirectory(this.directory, { create: true });
    const transport = new StdioClientTransport({ command: 'python3', args: ['-u', path.join(this.root,'scripts/gait-stdio.py')],
      cwd: this.directory, env: { ...this.environment, GAIT_MCP_STICKY_FILE: path.join(this.directory,'root') }, stderr: 'ignore' });
    const client = new Client({ name: 'netclaw-management-audit', version: '1.0.0' });
    try {
      await client.connect(transport, { timeout: 10000 }); this.client = client;
      if (!fs.existsSync(path.join(this.directory,'.gait'))) await this.call('gait_init', { path: this.directory });
      const status = await this.call('gait_status', { path: this.directory });
      invariant(status.root === this.directory, 'AUDIT_UNAVAILABLE');
      this.branch = `management-${randomUUID()}`;
      await this.call('gait_branch', { name: this.branch });
      await this.call('gait_checkout', { name: this.branch });
    } catch { this.client = null; await client.close().catch(() => {}); fail('AUDIT_UNAVAILABLE'); }
  }
  async call(name, args) {
    const result = await this.client.callTool({ name, arguments: args }, { timeout: 10000 });
    const data = result.structuredContent?.result || JSON.parse(result.content?.find(c=>c.type==='text')?.text || '{}');
    invariant(!result.isError && data.ok === true, 'AUDIT_UNAVAILABLE'); return data;
  }
  async record(value) {
    const work = this.queue.catch(() => {}).then(async () => {
      const lock = this.journal.lock('gait', this.binding.principal.principalId, 60000);
      try {
        await this.connect();
        const status = await this.call('gait_status', { path: this.directory });
        invariant(status.root === this.directory, 'AUDIT_UNAVAILABLE');
        await this.call('gait_checkout', { name: this.branch });
        // Never record freeform input, configuration, replacement secrets or provider output.
        const summary = {installationId:this.binding.installationId,principalId:this.binding.principal.principalId,...Object.fromEntries(['operationId','proposalId','action','state','artifactId'].filter(k => typeof value[k] === 'string' && /^[A-Za-z0-9_.:-]{1,200}$/.test(value[k])).map(k => [k,value[k]]))};
        return await this.call('gait_record_turn', { user_text: 'Authorized NetClaw management operation', assistant_text: JSON.stringify(summary), note: 'netclaw-management', use_memory_snapshot: false });
      } catch { fail('AUDIT_UNAVAILABLE'); } finally { this.journal.unlock('gait', lock); }
    });
    this.queue = work; return work;
  }
  async log(limit = 100) {
    const lock=this.journal.lock('gait',this.binding.principal.principalId,60000);
    try{await this.connect();const status=await this.call('gait_status',{path:this.directory});invariant(status.root===this.directory,'AUDIT_UNAVAILABLE');return await this.call('gait_log',{limit:Math.min(limit,500)});}
    finally{this.journal.unlock('gait',lock);}
  }
  async close() { await this.queue.catch(() => {}); if (this.client) { try { await this.log(20); } finally { await this.client.close(); this.client = null; } } }
}
