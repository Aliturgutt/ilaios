import 'package:flutter/material.dart';

import 'app/desktop_bootstrap.dart';
import 'control_plane/local_runtime.dart';

export 'app/desktop_app.dart';
export 'control_plane/projection.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  DesktopRuntime runtime;
  try {
    runtime = await DesktopRuntime.resolve();
  } on Object catch (error) {
    runtime = DesktopRuntimeFailure.from(error);
  }
  runApp(DesktopBootstrap(config: runtime.config, runtime: runtime));
}

class DesktopRuntimeFailure extends DesktopRuntime {
  DesktopRuntimeFailure._(String status)
      : super.unavailable(status: status);

  factory DesktopRuntimeFailure.from(Object error) =>
      DesktopRuntimeFailure._('Local control plane bootstrap failed: $error');
}
