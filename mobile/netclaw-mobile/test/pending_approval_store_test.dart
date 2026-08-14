import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/pending_approval_store.dart';

void main() {
  test('an approval appended during a background window survives to the next load', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_pending_approval_test_');
    addTearDown(() => dir.delete(recursive: true));

    final store = PendingApprovalStore(dir);
    await store.append({'approval_id': 42, 'target_name': 'core-router-01'});

    final drained = await store.loadAndClear();
    expect(drained, hasLength(1));
    expect(drained.single['approval_id'], 42);
    expect(drained.single['target_name'], 'core-router-01');
  });

  test('loadAndClear empties the store so the same approval is never replayed twice', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_pending_approval_test_');
    addTearDown(() => dir.delete(recursive: true));

    final store = PendingApprovalStore(dir);
    await store.append({'approval_id': 1});
    await store.loadAndClear();

    expect(await store.loadAndClear(), isEmpty);
  });

  test('multiple approvals queued in one window all survive, oldest first', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_pending_approval_test_');
    addTearDown(() => dir.delete(recursive: true));

    final store = PendingApprovalStore(dir);
    await store.append({'approval_id': 1});
    await store.append({'approval_id': 2});
    await store.append({'approval_id': 3});

    final drained = await store.loadAndClear();
    expect(drained.map((p) => p['approval_id']), [1, 2, 3]);
  });

  test('a store that was never written to loads as empty, not an error', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_pending_approval_test_');
    addTearDown(() => dir.delete(recursive: true));

    expect(await PendingApprovalStore(dir).loadAndClear(), isEmpty);
  });
}
