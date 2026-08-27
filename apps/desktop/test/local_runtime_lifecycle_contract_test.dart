import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('bundled runtime is detached from the launching shell but keeps app cleanup', () {
    final runtimeSource =
        File('lib/control_plane/local_runtime.dart').readAsStringSync();
    final bootstrapSource = File('lib/app/desktop_bootstrap.dart').readAsStringSync();

    expect(runtimeSource, contains('ProcessStartMode.detachedWithStdio'));
    expect(runtimeSource, isNot(contains('mode: ProcessStartMode.normal')));
    expect(bootstrapSource, contains('widget.runtime?.dispose()'));
    expect(runtimeSource, contains('void dispose()'));
    expect(runtimeSource, contains('_shutdownBundledRuntime()'));
    expect(runtimeSource, contains("/v1/runtime/shutdown"));
    expect(runtimeSource, contains('await process.stdin.close()'));
    expect(runtimeSource, contains('process.kill()'));
  });
}
