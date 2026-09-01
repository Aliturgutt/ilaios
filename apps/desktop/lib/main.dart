import 'package:flutter/material.dart';

import 'app/desktop_bootstrap.dart';
import 'control_plane/local_runtime.dart';

export 'app/desktop_app.dart';
export 'control_plane/projection.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final runtime = await DesktopRuntime.resolve();
  runApp(DesktopBootstrap(config: runtime.config, runtime: runtime));
}
