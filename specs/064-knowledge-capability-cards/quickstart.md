# Quickstart: Knowledge Capability Cards & Knowledge-Aware Routing

Prove the feature end-to-end on the live mesh (the same setup that demonstrated the
Hermes↔NetClaw book summary), then the automated checks.

## Manual walkthrough

1. **Have a corpus.** On claw A (e.g. AS 65001) ingest a document into RAG (feature 062):
   `rag_list` shows the `documents` collection with page/chunk counts.
2. **See it advertised.** From a federated peer B, pull A's card:
   `netclaw n2n inventory get as65001-4.4.4.4` → the card now contains a `knowledge` array
   with `knowledge:documents` (topics, tags, counts) and no document content.
3. **Route to it.** Ask B a question answerable only by A's corpus. B semantically matches
   the query to A's advertised `knowledge:documents`, invokes `n2n/knowledge/query` against
   A, and returns A's grounded, cited answer — attributed to A.
4. **Confirm sovereignty + audit.** Check that B never received chunks/embeddings (only the
   answer), and that A's audit trail has one record `{peer=B, collection_id, gait_ref}`.
5. **Confirm visibility.** Hide the collection from B (`n2n_set_visibility`); re-pull the
   card as B → `knowledge:documents` is gone; a permitted peer C still sees it.
6. **Confirm fallback.** Ask B something no advertised corpus covers → B answers from its own
   model and does not claim a federated source.

## Automated checks (pytest)

```bash
cd ~/netclaw
python3 -m pytest tests/n2n/test_knowledge_cards.py tests/n2n/test_knowledge_routing.py -q
```

Expected coverage:
- Card lists one entry per ready collection; counts correct; **no** chunk text / source paths;
  passes `_assert_no_secrets`.
- Hidden collection absent for the hidden peer, present for a permitted peer.
- Deterministic selection: same query + same advertised set → same corpus; stable tiebreak.
- Retrieval: possession-tier + granted peer succeeds and is audited; self-asserted or
  ungranted peer refused; unknown/hidden `collection_id` answered as "no such corpus".
- Fallback order peer → local → model; never fabricates a federated source.

## Success signals (from spec)

- SC-001 all authorized collections enumerable; 0% content on the card.
- SC-002 ≥95% of peer-only questions delegated + answered with citations.
- SC-003 selection deterministic.
- SC-004 every retrieval audited; unauthorized fetch/retrieval refused 100%.
- SC-005 card growth independent of corpus size.
