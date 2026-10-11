import { z } from 'zod';
import { fail } from '../../ui/netclaw-visual/src/management/errors.js';
export const id = z.string().min(1).max(200).regex(/^[A-Za-z0-9][A-Za-z0-9_.:/-]*$/).refine(v => !v.includes('..'));
export const nonce = z.string().regex(/^\d{13}:[a-f\d-]{36}$/);
export const action = z.enum(['settings.patch','runtime.select','service.start','service.stop','service.restart','risk.role','member.enroll','member.disable','member.enable','peer.trust','peer.untrust','security.patch','budget.patch','integration.configure','terminal-intent.prepare','terminal-intent.apply']);
export const kinds = z.enum(['overview','member','peer','edge','advisor','integration','skill','network']);
export const page = { cursor: z.string().max(512).optional(), limit: z.number().int().min(1).max(500).default(100) };
export const envKey = z.string().regex(/^[A-Z][A-Z0-9_]{0,100}$/);
export const patch = z.strictObject({
  provider: z.string().min(1).max(100).optional(), model: z.string().min(1).max(200).optional(), effort: z.enum(['low','medium','high','max']).optional(),
  role: z.enum(['standalone','border','member']).optional(), runtimeId: id.optional(), serviceId: z.enum(['hud','gateway','federation','hermes-companion','openshell']).optional(),
  monthlyLimit: z.number().min(0).max(1000000).optional(), dailyLimit: z.number().min(0).max(1000000).optional(),
  fields: z.array(z.strictObject({ key: envKey, intent: z.enum(['keep','replace','clear']), value: z.string().max(4096).optional() })).max(100).optional(),
  mode: z.enum(['observe','enforce','disabled']).optional(), enabled: z.boolean().optional(), intent: z.string().max(65536).optional(),
  acknowledgeActiveWork: z.boolean().optional(),
});
export const changeInput = { nonce, action, targets: z.array(id).min(1).max(100), expectedRevision: z.string().uuid(), patch };
export const schemas = Object.freeze({
  operator_identity: z.strictObject({}),
  operator_resources: z.strictObject({ kind: kinds, filters: z.strictObject({ query: z.string().max(256).optional(), status: z.enum(['active','inactive','unknown']).optional() }).optional(), ...page }),
  operator_snapshot: z.strictObject({ domain: z.enum(['settings','security','usage','knowledge','documentation']), resourceId: id.optional(), window: z.enum(['day','week','month']).optional(), ...page }),
  operator_conversation_open: z.strictObject({ nonce, conversationId: id.optional(), view: z.enum(['chat','canvas','avatar']).default('chat'), model: z.string().max(200).optional(), effort: z.enum(['low','medium','high','max']).optional() }),
  operator_request_submit: z.strictObject({ nonce, conversationId: id, prompt: z.string().max(65536).refine(v => Buffer.byteLength(v) <= 65536), contextIds: z.array(id).max(20).default([]) }),
  operator_operation_get: z.strictObject({ operationId: id }),
  operator_events: z.strictObject({ operationId: id, after: z.number().int().min(0).default(0), ...page }),
  operator_cancel_request: z.strictObject({ operationId: id, nonce }),
  operator_change_prepare: z.strictObject(changeInput),
  operator_change_apply: z.strictObject({ proposalId: id, nonce, expectedRevision: z.string().uuid(), approvalReference: id.optional(), replacements: z.record(envKey, z.string().max(65536)).optional() }),
  operator_evidence: z.strictObject({ kind: z.enum(['gait','log','artifact','approval']), id: id.optional(), filters: z.strictObject({ query: z.string().max(200).optional(), severity: z.enum(['info','warning','error']).optional() }).optional(), ...page }),
  operator_workspace: z.strictObject({ action: z.enum(['rag-list','rag-search','rag-stage','rag-upload','rag-index','rag-context','memory-search','gcf-read','meeting-read','assessment-read','assessment-reconsider','canvas-import','canvas-export','mobile-capture-request']), nonce: nonce.optional(), args: z.strictObject({ id: id.optional(), query: z.string().max(4096).optional(), name: z.string().max(200).optional(), content: z.string().max(14*1024*1024).optional(), collection: z.string().regex(/^[\w.-]{1,128}$/).optional(), k: z.number().int().min(1).max(20).optional(), docType: z.enum(['vendor','standard','customer','install-guide','other']).optional(), indices: z.array(z.number().int().min(0).max(19)).min(1).max(20).optional(), expectedDocumentId: id.optional(), consentReference: id.optional(), capability: z.enum(['camera.capture','audio.record']).optional() }), ...page }),
  operator_client_prepare: z.strictObject({ nonce, client: z.enum(['copilot','claude-code','codex']), targets: z.array(id).min(1).max(100), actions: z.array(z.enum(['inspect','delegate','propose','evidence','cancel'])).min(1).max(5), disclosure: z.array(z.enum(['summary','usage','evidence','conversation'])).min(1).max(4), expiresAt: z.number().int().positive() }),
  operator_client_apply: z.strictObject({ proposalId: id, nonce, expectedRevision: z.string().uuid() }),
  operator_client_revoke: z.strictObject({ grantId: id, nonce }),
});
export function parseOperatorInput(name, args) {
  if (!Object.hasOwn(schemas, name)) fail('DENIED');
  const parsed = schemas[name].safeParse(args); if (!parsed.success) fail('INVALID_INPUT'); return parsed.data;
}
