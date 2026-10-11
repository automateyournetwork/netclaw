import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import dotenv from 'dotenv';
import { withManagementConfigurationLock } from '../management/shared-lock.js';

export function regularTarget(file) {
  try {
    const state = fs.lstatSync(file);
    if (!state.isFile() || state.isSymbolicLink()) throw new Error('Configuration target must be a regular file');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}

export function writePrivateAtomic(file, data) {
  regularTarget(file);
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = path.join(path.dirname(file), `.netclaw-${randomUUID()}.tmp`);
  let created = false;
  try {
    const fd = fs.openSync(temporary, 'wx', 0o600);
    created = true;
    try {
      fs.writeFileSync(fd, data, 'utf8');
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
    fs.renameSync(temporary, file);
    created = false;
  } finally {
    if (created) fs.unlinkSync(temporary);
  }
}

export function parseEnvData(text) {
  const result = Object.assign(Object.create(null), dotenv.parse(text));
  for (const line of text.split(/\r?\n/)) {
    const match = line.trim().match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match || !match[2].startsWith('"')) continue;
    try {
      const value = JSON.parse(match[2]);
      if (typeof value === 'string') result[match[1]] = value;
    } catch { /* legacy dotenv quoting remains supported */ }
  }
  return result;
}

export function updateEnvironment(file, updates) {
  return withManagementConfigurationLock(path.dirname(file), () => updateEnvironmentLocked(file, updates));
}

function updateEnvironmentLocked(file, updates) {
  if (!updates || typeof updates !== 'object' || Array.isArray(updates)) throw new Error('Expected environment assignments');
  for (const [key, value] of Object.entries(updates)) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key) || typeof value !== 'string' || /[\r\n\0]/.test(value)) {
      throw new Error('Environment names and single-line string values are required');
    }
  }
  regularTarget(file);
  const original = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  const lines = original.split(/\r?\n/).filter((line) => {
    const match = line.trim().match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=/);
    return !match || !Object.hasOwn(updates, match[1]);
  });
  while (lines.at(-1) === '') lines.pop();
  for (const [key, value] of Object.entries(updates)) {
    const literal = /^[A-Za-z0-9_@%+=:,./-]+$/.test(value) ? value : JSON.stringify(value);
    lines.push(`${key}=${literal}`);
  }
  writePrivateAtomic(file, lines.join('\n') + '\n');
}
