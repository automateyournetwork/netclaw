import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/enrollment_store.dart';

void main() {
  test('a saved enrollment persists across a simulated app restart', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_enrollment_test_');
    addTearDown(() => dir.delete(recursive: true));

    final original = StoredEnrollment(
      memberId: 'risk/123',
      keyFingerprint: 'abcd1234',
      borderHost: '10.0.2.2',
      borderPort: 28443,
      clawDomain: '10.0.2.2',
    );
    await EnrollmentStore(dir).save(original);

    // A fresh store instance over the same directory -- mirrors a real
    // app restart, where nothing but the file itself carries over.
    final reloaded = await EnrollmentStore(dir).load();

    expect(reloaded, isNotNull);
    expect(reloaded!.memberId, original.memberId);
    expect(reloaded.keyFingerprint, original.keyFingerprint);
    expect(reloaded.borderHost, original.borderHost);
    expect(reloaded.borderPort, original.borderPort);
    expect(reloaded.clawDomain, original.clawDomain);
  });

  test('load() returns null when nothing has ever been saved', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_enrollment_test_');
    addTearDown(() => dir.delete(recursive: true));

    expect(await EnrollmentStore(dir).load(), isNull);
  });

  test('clear() removes a saved enrollment', () async {
    final dir = await Directory.systemTemp.createTemp('ncfed_enrollment_test_');
    addTearDown(() => dir.delete(recursive: true));
    final store = EnrollmentStore(dir);
    await store.save(const StoredEnrollment(
      memberId: 'risk/123',
      keyFingerprint: 'abcd1234',
      borderHost: '10.0.2.2',
      borderPort: 28443,
      clawDomain: '10.0.2.2',
    ));

    await store.clear();

    expect(await store.load(), isNull);
  });
}
