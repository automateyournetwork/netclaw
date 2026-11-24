import { GoogleGenAI } from "@google/genai";
import { need, POLICY } from "./model.mjs";
import { validateReviewedCampaignSend } from "./live-packet.mjs";
// Internal adapter only. The fixture manager intentionally exposes no paid route.
export async function openGoogle({ ledger, id, apiKey, client, env = process.env }) {
  const validatedRecord = validateReviewedCampaignSend(ledger, id, env);
  need(typeof apiKey === "string" && apiKey.length > 0, "credential_missing");
  const ai =
    client || new GoogleGenAI({ apiKey, apiVersion: POLICY.api_version });
  ledger.claimProviderCreate(id, validatedRecord);
  const releaseLedger = ledger.retain();
  try {
    const interaction = await ai.interactions.create(
      {
        model: POLICY.model,
        api_version: POLICY.api_version,
        automatic_continuation: false,
      },
      { retries: { strategy: "none" }, timeout_ms: 10000 },
    );
    need(typeof interaction.id === "string", "provider_id_missing");
    ledger.providerId(id, interaction.id);
    const session = await ai.interactions.connect(
      interaction.id,
      { transport: "websocket", api_version: POLICY.api_version },
      { timeout_ms: 10000 },
    );
    return {
      id: interaction.id,
      send: (event) => session.send(event),
      complete: () => session.complete(),
      cancel: () => session.cancel(),
      receive: () => session.receive(),
    };
  } catch (error) {
    ledger.audit('provider_open_error', { operation_id: id,
      error_name: String(error?.name || 'Error').slice(0, 80),
      http_status: Number.isInteger(error?.status) ? error.status : null,
      message: String(error?.message || 'Provider rejected connection').replaceAll(apiKey, '[REDACTED]').slice(0, 2048) });
    // A rejection, absent ID or connect failure cannot prove that create had no
    // effect. Retain the claim, original ID (if known), and full reservation.
    if (['create_pending', 'stop_requested'].includes(ledger.get(id).state))
      ledger.transition(id, 'unknown', { reason: 'provider_open_unknown' });
    throw error;
  } finally {
    releaseLedger();
  }
}
