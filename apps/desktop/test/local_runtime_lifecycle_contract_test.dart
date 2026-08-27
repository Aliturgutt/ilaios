import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('bundled runtime is detached from the launching shell but keeps app cleanup', () {
    final runtimeSource =
        File('lib/control_plane/local_runtime.dart').readAsStringSync();
    final bootstrapSource = File('lib/app/desktop_bootstrap.dart').readAsStringSync();
    final sidecarSource =
        File('sidecar/ilaios_control_plane_sidecar.py').readAsStringSync();

    expect(runtimeSource, contains('ProcessStartMode.detachedWithStdio'));
    expect(runtimeSource, isNot(contains('mode: ProcessStartMode.normal')));
    expect(runtimeSource, contains("'--desktop-pid'"));
    expect(runtimeSource, contains("'\$pid'"));
    expect(sidecarSource, contains('parser.add_argument("--desktop-pid", type=int)'));
    expect(sidecarSource, contains('stop_identity_if_desktop_exits'));
    expect(sidecarSource, contains('_wait_for_windows_process_exit(desktop_pid)'));
    expect(bootstrapSource, contains('widget.runtime?.dispose()'));
    expect(runtimeSource, contains('void dispose()'));
    expect(runtimeSource, contains('_shutdownBundledRuntime()'));
    expect(runtimeSource, contains("/v1/runtime/shutdown"));
    expect(runtimeSource, contains('await process.stdin.close()'));
    expect(runtimeSource, contains('process.kill()'));
  });
}
