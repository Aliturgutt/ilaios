import 'package:flutter/material.dart';

import 'app/desktop_bootstrap.dart';
import 'control_plane/config.dart';

export 'app/desktop_app.dart';
export 'control_plane/projection.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final config = await ControlPlaneConfig.fromEnvironment();
  runApp(DesktopBootstrap(config: config));
}
