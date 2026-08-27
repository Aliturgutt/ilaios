import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('bundled runtime is detached from the launching shell but keeps app cleanup', () {
    final source = File('lib/control_plane/local_runtime.dart').readAsStringSync();

    expect(source, contains('ProcessStartMode.detachedWithStdio'));
    expect(source, isNot(contains('mode: ProcessStartMode.normal')));
    expect(source, contains("/v1/runtime/shutdown"));
    expect(source, contains('await process.stdin.close()'));
    expect(source, contains('process.kill()'));
  });
}
