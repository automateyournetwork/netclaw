import 'dart:convert';
import 'dart:io';
import 'package:integration_test/integration_test_driver.dart';

/// Host-side evidence export, before Flutter tears down/uninstalls the app.
/// NETCLAW_NATIVE_REPORT names a fresh JSON file in an existing private 0700
/// directory. Neither report contents nor credentials are printed to stdout.
Future<void> main() async {
  final destination = Platform.environment['NETCLAW_NATIVE_REPORT'];
  if (destination == null || !destination.startsWith('/')) {
    throw StateError('Set an absolute private NETCLAW_NATIVE_REPORT path');
  }
  final file = File(destination);
  if (FileSystemEntity.typeSync(file.parent.path, followLinks: false) !=
          FileSystemEntityType.directory ||
      file.parent.statSync().mode & 0x3f != 0 ||
      FileSystemEntity.typeSync(destination, followLinks: false) !=
          FileSystemEntityType.notFound) {
    throw StateError(
      'Evidence requires a fresh file in an existing private directory',
    );
  }
  await integrationDriver(
    timeout: const Duration(minutes: 10),
    writeResponseOnFailure: true,
    responseDataCallback: (data) async {
      final evidence = data?['r04a_evidence'];
      if (evidence is! Map<String, dynamic>) {
        throw StateError(
          'Native test supplied no completed evidence; no success inferred',
        );
      }
      await file.create(exclusive: true);
      final chmod = await Process.run('chmod', ['600', destination]);
      if (chmod.exitCode != 0) {
        throw StateError('Could not protect native evidence file');
      }
      await file.writeAsString(
        const JsonEncoder.withIndent('  ').convert(evidence),
        flush: true,
      );
    },
  );
}
