import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/endpoint_recovery.dart';

void main() {
  test(
    'region label is display-only; unknown or spoofed names stay unknown',
    () {
      expect(
        regionLabel('https://nne1-3fa9c2.automateyournetwork.com'),
        'Montreal',
      );
      expect(regionLabel('ew1-b71d04.automateyournetwork.com'), 'Belgium');
      expect(
        regionLabel('wss://ase1-9c2e55.automateyournetwork.com/ws'),
        'Singapore',
      );
      for (final bad in [
        'https://evil.example/nne1-3fa9c2.automateyournetwork.com',
        'nne1-3fa9c.automateyournetwork.com',
        'nne1-3fa9c2.automateyournetwork.com.evil.io',
        '',
        null,
      ]) {
        expect(regionLabel(bad), 'Unknown region');
      }
    },
  );
}
