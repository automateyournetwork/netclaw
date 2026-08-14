import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';
import 'package:netclaw_mobile/ncfed/pending_open_intent.dart';

/// Spec 107, contract §1. The intent exists because a notification tap and the
/// tapped message's arrival are concurrent — see pending_open_intent.dart for the
/// measured timings that make the old single-read approach always lose.

EdgeMessage _msg(String iso, {String content = 'hello'}) => EdgeMessage(
      contentType: MessageContentType.text,
      content: content,
      designatedBy: 'agent',
      pushedAt: DateTime.parse(iso),
    );

void main() {
  test('resolves immediately when the message is already present (§1.3)', () {
    final opened = <EdgeMessage>[];
    final intent = PendingOpenIntent(onOpen: opened.add);
    final messages = [_msg('2026-08-13T16:45:34Z')];

    intent.record('2026-08-13T16:45:34Z');
    final resolved = intent.tryResolve(messages);

    expect(resolved, isTrue);
    expect(opened, hasLength(1));
    expect(intent.isPending, isFalse);
    intent.dispose();
  });

  test('resolves when the message arrives AFTER the tap (§1.4)', () {
    // The actual production bug: the message lands ~3s after a cold-start tap.
    final opened = <EdgeMessage>[];
    final intent = PendingOpenIntent(onOpen: opened.add);
    final messages = <EdgeMessage>[];

    intent.record('2026-08-13T16:45:34Z');
    expect(intent.tryResolve(messages), isFalse, reason: 'nothing to match yet');
    expect(opened, isEmpty);
    expect(intent.isPending, isTrue, reason: 'must keep waiting, not give up');

    messages.add(_msg('2026-08-13T16:45:34Z'));
    expect(intent.tryResolve(messages), isTrue);
    expect(opened, hasLength(1));
    intent.dispose();
  });

  test('a second record discards the first (§1.2)', () {
    final opened = <EdgeMessage>[];
    final intent = PendingOpenIntent(onOpen: opened.add);

    intent.record('2026-08-13T16:45:34Z');
    intent.record('2026-08-13T17:00:00Z');
    expect(intent.identifier, '2026-08-13T17:00:00Z');

    // The first-tapped message arriving must NOT open anything now.
    expect(intent.tryResolve([_msg('2026-08-13T16:45:34Z')]), isFalse);
    expect(opened, isEmpty);

    expect(intent.tryResolve([_msg('2026-08-13T17:00:00Z')]), isTrue);
    expect(opened, hasLength(1));
    intent.dispose();
  });

  test('onOpen fires exactly once per tap (§1.6)', () {
    final opened = <EdgeMessage>[];
    final intent = PendingOpenIntent(onOpen: opened.add);
    final messages = [_msg('2026-08-13T16:45:34Z')];

    intent.record('2026-08-13T16:45:34Z');
    intent.tryResolve(messages);
    // Every later feed change re-offers the same list; must not re-open.
    intent.tryResolve(messages);
    intent.tryResolve(messages);

    expect(opened, hasLength(1));
    intent.dispose();
  });

  test('expires within the bound, and does NOT fire onOpen (§1.5, §1.6)', () async {
    final opened = <EdgeMessage>[];
    var expired = false;
    final intent = PendingOpenIntent(
      onOpen: opened.add,
      onExpire: () => expired = true,
      timeout: const Duration(milliseconds: 30),
    );

    intent.record('2026-08-13T16:45:34Z');
    await Future<void>.delayed(const Duration(milliseconds: 80));

    expect(expired, isTrue, reason: 'FR-003: must stop waiting');
    expect(opened, isEmpty, reason: 'expiry must never open a message');
    expect(intent.isPending, isFalse);

    // A message arriving after expiry must not retroactively navigate.
    expect(intent.tryResolve([_msg('2026-08-13T16:45:34Z')]), isFalse);
    expect(opened, isEmpty);
    intent.dispose();
  });

  test('resolving cancels the expiry, so onExpire never fires after', () async {
    final opened = <EdgeMessage>[];
    var expired = false;
    final intent = PendingOpenIntent(
      onOpen: opened.add,
      onExpire: () => expired = true,
      timeout: const Duration(milliseconds: 30),
    );

    intent.record('2026-08-13T16:45:34Z');
    intent.tryResolve([_msg('2026-08-13T16:45:34Z')]);
    await Future<void>.delayed(const Duration(milliseconds: 80));

    expect(opened, hasLength(1));
    expect(expired, isFalse, reason: 'a resolved intent must not also expire');
    intent.dispose();
  });

  test('cancel abandons without firing either callback', () async {
    final opened = <EdgeMessage>[];
    var expired = false;
    final intent = PendingOpenIntent(
      onOpen: opened.add,
      onExpire: () => expired = true,
      timeout: const Duration(milliseconds: 30),
    );

    intent.record('2026-08-13T16:45:34Z');
    intent.cancel();
    await Future<void>.delayed(const Duration(milliseconds: 80));

    expect(opened, isEmpty);
    expect(expired, isFalse);
    expect(intent.isPending, isFalse);
  });

  test('nothing pending means tryResolve is a cheap no-op (FR-011)', () {
    final opened = <EdgeMessage>[];
    final intent = PendingOpenIntent(onOpen: opened.add);
    expect(intent.tryResolve([_msg('2026-08-13T16:45:34Z')]), isFalse);
    expect(opened, isEmpty);
    intent.dispose();
  });

  test('matches the same instant across timezone spellings', () {
    // The Border sends `Z`; a differently-formatted offset for the same moment
    // must still match, or dedup and deep-linking would silently disagree.
    final opened = <EdgeMessage>[];
    final intent = PendingOpenIntent(onOpen: opened.add);

    intent.record('2026-08-13T12:45:34-04:00'); // == 16:45:34Z
    expect(intent.tryResolve([_msg('2026-08-13T16:45:34Z')]), isTrue);
    expect(opened, hasLength(1));
    intent.dispose();
  });

  test('an unparseable identifier matches nothing rather than throwing', () {
    final opened = <EdgeMessage>[];
    final intent = PendingOpenIntent(onOpen: opened.add);

    intent.record('not-a-timestamp');
    expect(intent.tryResolve([_msg('2026-08-13T16:45:34Z')]), isFalse);
    expect(opened, isEmpty);
    intent.dispose();
  });
}
