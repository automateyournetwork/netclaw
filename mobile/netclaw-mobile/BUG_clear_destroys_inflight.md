# Bug Report — "Clear messages" destroys in-flight requests

**Reported by:** Justin, 2026-07-27 18:44 EDT
**Triaged & fixed by:** NetClaw Border (`as65001-4.4.4.4`)
**Severity:** High — silent, unrecoverable data loss
**Status:** FIXED · `flutter analyze` clean · `flutter test` 132/132 · APK rebuilt

---

## Report

> "when you clear messages it actually clears all messages including the pending
> actual working messages that are processing currently"

Confirmed exactly as described.

---

## Root cause

`ConversationStore.clear()` deleted every turn unconditionally, regardless of
state. The old implementation:

```dart
Future<void> clear() async {
  await load();
  for (final turn in _turns) { /* delete photo */ }
  _turns.clear();
  final file = _file();
  if (await file.exists()) await file.delete();
}
```

`_turns.clear()` takes `pending` and `working` rows along with finished ones.

### Why the loss is silent and permanent

The Border keeps working on a cleared request. When the answer arrives,
`updateState` looks for its row:

```dart
for (final t in _turns) {
  if (t.taskId == taskId) { ... }
}
```

No row matches, the loop finds nothing, and **the answer is dropped with no
error**. `reconcileStaleTurns` is equally helpless — it iterates local turns to
decide what to re-query, so a deleted turn is invisible to it. The work is done,
billed, and audited on the Border, and the operator never sees it. There is no
recovery path from the phone: the Border never re-pushes spontaneously.

### It was a deliberate decision, documented in the source

This was not an oversight. The old doc comment:

> *"In-progress turns go too. That's deliberate: the Border keeps working and
> reconciliation no longer has a local row to reconcile against, so a cleared
> in-flight answer simply never appears. Callers should warn when anything is
> still running."*

And the confirmation dialog **described the data loss rather than preventing
it**:

> *"A request is still in progress. The Border will finish it, but the answer
> will no longer appear here."*

Someone saw this exact failure, wrote it down, and shipped a warning instead of
a fix. Justin is right that a warning is the wrong answer: **clearing history
should not cancel the future.** An operator tidying a transcript is not asking
to throw away a running request, and no amount of dialog copy makes that
mapping intuitive.

Worth stating plainly: deleting the local row **never cancelled anything**. The
Border kept working either way. So the old behaviour bought nothing — it only
discarded the operator's ability to see the result.

---

## Fix

`clear()` now preserves non-terminal turns by default:

```dart
Future<void> clear({bool includeInProgress = false}) async {
  await load();
  final kept = includeInProgress
      ? const <ConversationTurn>[]
      : _turns.where((t) => !_isTerminal(t.state)).toList();
  ...
}
```

Reuses the existing `_isTerminal` helper (`completed` / `failed` / `cancelled`),
so "in progress" means the same thing here as it does in `updateState`'s
terminal-state guard and in `hasInProgressTurns` — one definition, three call
sites.

Three details that matter:

1. **Photos of surviving turns are retained.** A preserved turn still renders,
   so deleting its `photo_*.jpg` would leave a broken `[Photo unavailable]` tile
   attached to a live request. Only finished turns' photos are removed, so the
   original disk-growth problem this method exists to solve is still solved.
2. **The file is rewritten, not deleted, when anything survives.** Preserving a
   turn in memory alone would lose it on the next cold start — and reconciliation
   after a restart is precisely when it matters most.
3. **`includeInProgress: true`** retains the old all-or-nothing behaviour for a
   caller that has explicitly confirmed that intent. Nothing in the app uses it
   yet; it exists so the capability isn't lost.

### UI

`main.dart` dialog copy, now truthful:

- Title/body: *"Deletes **finished** requests from this phone."*
- When something is running: *"Requests still in progress will be kept so their
  answers can still arrive."*

### Not changed — deliberately

`MessageFeedStore.clear()` (the Feed tab's "Clear all messages") still deletes
everything, correctly. Feed entries are **already-delivered pushes** with no
pending state and nothing in flight to protect. Only the Chat conversation store
had this defect.

---

## The tests were asserting the bug

Both failing tests had been **encoding the defect as the expected contract**,
which is why 126 green tests said nothing about it:

`test/clear_and_revocation_test.dart`
```dart
await store.addPending('t1', 'first');
await store.addPending('t2', 'second');   // both PENDING
await store.clear();
expect(store.turns, isEmpty);             // asserted the data loss
```

`test/conversation_store_test.dart` — same shape: two pending turns, asserting
both vanish.

Neither ever marked a turn terminal, so neither exercised what clearing history
is actually for. This is the same class of gap as the mic bug: **a green suite
that tests the wrong contract is worse than no test**, because it actively
defends the defect against change.

Rewritten to mark turns terminal first, plus six new cases:

| Test | Asserts |
|---|---|
| removes finished turns and the backing file | normal clear still works |
| **an in-progress turn SURVIVES a clear** | the regression |
| a `working` turn survives too, not just `pending` | both non-terminal states |
| a surviving turn is still there after a restart | the rewrite actually persists |
| `includeInProgress: true` clears everything | opt-in escape hatch |
| a finished turn cleared alongside a survivor stays gone on restart | no accidental resurrection |
| keeps an in-flight turn's photo on disk | photo retention, both directions |

---

## Verification

```
flutter analyze     → No issues found!
flutter test        → 132/132 passed   (126 before; 2 rewritten, +6 new)
flutter build apk   → ✓ Built app-debug.apk  (exit 0)
```

**Not verified on-device.** The fix is store-level logic with direct unit
coverage, but the end-to-end path worth confirming by hand is: submit a request,
clear chat while it is still working, then let the answer arrive and check it
appears.

---

## Related

Same session, same codebase:
- `BUG_mic_recording.md` — mic hang/no-record, six root causes, fixed.
- `MIC_HOTFIX_ANDROID_COMPAT.md` — Android 15/16 verified, 17 unverifiable.
- Still outstanding: **the repo has no git remote.** None of these fixes exist
  anywhere but this disk.
