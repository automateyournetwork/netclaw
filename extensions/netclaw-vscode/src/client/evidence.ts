import { ownerCanonical } from "./owner";
import type { Json } from "./hud";

const object = (v: any): v is Json => v !== null && typeof v === "object" && !Array.isArray(v);
const digest = (v: any) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
/** Project native facts separately; a signature does not verify model prose. */
export function operationEvidence(operation: Json) {
  const result = operation?.result, tool = result?.evidence?.output?.tool, call = operation?.review?.tool_call;
  let facts: Json | null = null, summary = "Unavailable";
  if (result?.verified === true && object(tool) && object(tool.output)) {
    if (call?.tool === "pyats_run_show_command" && tool.parsed === true) facts = tool.output;
    else if (tool.schemaVersion === 1 && tool.mcp_calls === 1 && call?.tool === tool.tool &&
      ["endpoint_sha256", "source_sha256", "skill_sha256", "mcp_schema_sha256"].every(k => digest(tool[k])) && tool.endpoint_sha256 === call.endpoint_sha256) {
      try { if (ownerCanonical(call.arguments) === ownerCanonical(tool.arguments)) facts = tool.output; } catch { /* Invalid evidence has no authoritative projection. */ }
    }
  }
  if (facts?.schema_version === 1 && ["subnet_calculator", "subnet_calculator_v6"].includes(call?.tool)) {
    const family = call.tool === "subnet_calculator" ? 4 : 6, bits = family === 4 ? 32 : 128, prefix = facts.prefix_length;
    if (tool.independent_verification !== true || !digest(tool.native_result_sha256) || facts.family !== family ||
      Object.keys(call.arguments).length !== 1 || facts.network !== call.arguments.cidr || typeof facts.network !== "string" ||
      !Number.isSafeInteger(prefix) || prefix < 0 || prefix > bits || Number(facts.network.split("/")[1]) !== prefix ||
      typeof facts.address_count !== "string" || !/^[1-9]\d{0,38}$/.test(facts.address_count) || BigInt(facts.address_count) !== (1n << BigInt(bits - prefix))) facts = null;
    else if (family === 4 && facts.usable_count === String(BigInt(facts.address_count) - (prefix < 31 ? 2n : 0n))) summary = `${facts.network} · ${facts.usable_count} usable hosts`;
    else if (family === 6 && facts.subnets_64 === String(prefix <= 64 ? 1n << BigInt(64 - prefix) : 0n)) summary = `${facts.network} · ${facts.address_count} addresses`;
    else facts = null;
  }
  const commentary = result?.evidence?.output?.model_answer;
  return {
    "Authoritative tool facts": facts,
    "Verified native summary": summary === "Unavailable" ? null : summary,
    "Unverified model commentary": result?.verified === true && typeof commentary === "string" ? commentary : null,
    "Commentary notice": "Model commentary can be inaccurate. Use the authoritative tool facts. The signature verifies the receipt and its bindings, not the accuracy of model commentary.",
  };
}
export function presentOperationDocument(value: any): any {
  if (!object(value)) return value;
  if (Array.isArray(value.children)) return { result_interpretation: value.children.map((child: Json) => ({ operation_id: child.operation_id, ...operationEvidence(child) })), ...value };
  if (value.operation_id && value.result) return { result_interpretation: operationEvidence(value), ...value };
  return value;
}
