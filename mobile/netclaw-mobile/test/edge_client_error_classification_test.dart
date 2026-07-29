import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';

void main() {
  group('isRevokedByBorder', () {
    test('-32023 (_ERR_NOT_TRUSTED) is treated as a genuine revocation', () {
      final err = EdgeClientException('-32023', 'pinned-key auth failed');
      expect(isRevokedByBorder(err), isTrue);
    });

    test('a timeout is NOT treated as a revocation', () {
      final err = EdgeClientException('timeout', 'in2n/hello timed out');
      expect(isRevokedByBorder(err), isFalse);
    });

    test('a connection_error is NOT treated as a revocation', () {
      final err = EdgeClientException('connection_error', 'connection closed');
      expect(isRevokedByBorder(err), isFalse);
    });

    test('a non-EdgeClientException is NOT treated as a revocation', () {
      expect(isRevokedByBorder(Exception('some socket/TLS failure')), isFalse);
    });
  });
}
