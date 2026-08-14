# Contract: notification intent and push ingest

**Feature**: 107-push-render-deeplink
**Date**: 2026-08-13

The app exposes no external API, so this is an **internal-collaboration
contract** — the obligations each collaborator owes the others, which is the
contract form appropriate to an application rather than a service. It exists so
the two new modules and the two modified ones cannot drift apart, and so the
tests in `tasks.md` have something to assert against.

---

## §1 Pending open intent

### Obligations

| # | Obligation |
|---|---|
| 1.1 | Recording an intent MUST NOT block, and MUST NOT itself trigger navigation. |
| 1.2 | Recording a second intent MUST discard the first. Exactly one intent exists at any time. |
| 1.3 | If the named message is already in the feed at record time, the intent MUST resolve without waiting. |
| 1.4 | If the named message enters the feed later, the intent MUST resolve then. |
| 1.5 | An intent MUST expire within a bounded interval, ≤10s (SC-007), and expiry MUST leave the operator on a usable screen. |
| 1.6 | Resolution MUST fire the open callback exactly once. Expiry MUST NOT fire it at all. |
| 1.7 | Intent state MUST NOT persist across app launches. |

### Non-obligations

- Does not guarantee the message ever arrives. That is spec 106's job.
- Does not fetch, retry, or contact the Border. It only observes the local feed.

---

## §2 Feed append

### Obligations

| # | Obligation |
|---|---|
| 2.1 | Append MUST be the single enforcement point for message identity. Callers MUST NOT pre-check for duplicates. |
| 2.2 | Appending a Message whose `pushedAt` matches a stored Message MUST leave the stored one byte-for-byte unchanged — including `read` state (FR-006). |
| 2.3 | Append MUST report whether it stored or declined, so a caller can avoid firing an "arrived" side effect (badge, notification) for a message the operator already has. |
| 2.4 | Declining MUST NOT be an error. It is the expected outcome whenever two delivery paths carry the same message. |

### Rationale for 2.3

Without a return signal, the ingest path would fire an unread badge for every
replayed duplicate, so the fix for double *entries* would leave double
*notifications* — a visibly identical bug one layer up.

---

## §3 Push payload ingest

### Obligations

| # | Obligation |
|---|---|
| 3.1 | MUST tolerate every value arriving as a string. The sender stringifies the whole content map (`data: {k: str(v) …}`), so no field may be assumed to have survived with its original type. |
| 3.2 | MUST route `content_type: 'approval'` to the approvals path and MUST NOT write it to the feed (FR-009). |
| 3.3 | MUST reject a payload with a missing or unparseable `pushed_at` rather than substituting a value (see data-model's validation rule — substituting would mint a fresh identity per attempt and defeat dedup). |
| 3.4 | MUST NOT corrupt or truncate the stored feed on any malformed input (FR-010). Rejecting the payload is the correct outcome. |
| 3.5 | MUST reconstruct through the same wire parser the live channel path uses. A second parser is forbidden — it would drift. |

### Non-obligations

- Not required to succeed. A rejected payload falls back to spec 106's replay,
  which is the guarantee; this path is an acceleration of it (R5).

---

## §4 Handler registration

### Obligations

| # | Obligation |
|---|---|
| 4.1 | `wireMessageFeed` MUST remain the ONLY registration site for `n2n/edge/message`. |
| 4.2 | The push ingest path MUST NOT register a channel handler. |

### Why this is a contract clause and not a comment

`EdgeClient.on()` keeps only the **last** handler registered per method. A second
registration for `n2n/edge/message` would silently displace the first and disable
live delivery entirely — with no error, and with the feature's own tests still
passing if they exercised the new path. This is the highest-severity failure mode
in the feature and the cheapest to guard: a structural test asserting a single
registration site.

---

## §5 What this feature must not change

| # | Obligation |
|---|---|
| 5.1 | No Border-side change. Spec 106 owns delivery. |
| 5.2 | No new push transport. The existing one is used as-is (spec 103). |
| 5.3 | No weakening of SC-006 — every message the Border delivers still reaches the feed, whether or not the push path accelerated it. |
| 5.4 | Local-notification tap behavior (spec 073), which already deep-links correctly, MUST keep working; it converges on the shared intent rather than being replaced. |
