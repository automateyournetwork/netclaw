import React from 'react';
import { authoritativeToolFacts, unverifiedModelCommentary, verifiedResultSummary } from '../shared/protected-operation-references.js';

export default function OperationResultEvidence({ operation }) {
  if (operation?.result?.verified !== true) return null;
  const facts = authoritativeToolFacts(operation), commentary = unverifiedModelCommentary(operation);
  return <section aria-label="Result interpretation">
    {facts && <><h4>Authoritative tool facts</h4><p aria-label="Verified native summary">{verifiedResultSummary(operation)}</p><pre aria-label="Authoritative tool facts">{JSON.stringify(facts, null, 2)}</pre></>}
    {commentary !== null && <><h4>Unverified model commentary</h4><p>Model commentary can be inaccurate. Use the authoritative tool facts.</p><pre aria-label="Unverified model commentary">{commentary}</pre></>}
    <details><summary>Signed receipt and audit references</summary><p>The signature verifies the receipt and its bindings. Model commentary is not independently verified.</p><pre aria-label="Signed receipt and audit references">{JSON.stringify(operation.result.evidence, null, 2)}</pre></details>
  </section>;
}
