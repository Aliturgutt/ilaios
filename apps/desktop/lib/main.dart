import 'package:flutter/material.dart';
import 'package:multiview_desktop/multiview_desktop.dart';

import 'app/desktop_bootstrap.dart';
import 'features/dashboard/reference_desktop_shell_v11.dart';
import 'control_plane/local_runtime.dart';

export 'app/desktop_app.dart';
export 'control_plane/projection.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final runtime = await DesktopRuntime.resolve();
  ReferenceDesktopShellV11.nativeAssistantWindowEnabled = true;
  runMultiApp(
    home: (context, id) =>
        DesktopBootstrap(config: runtime.config, runtime: runtime),
  );
}
