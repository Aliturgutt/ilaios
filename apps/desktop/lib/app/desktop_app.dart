import 'package:flutter/material.dart';

import '../control_plane/projection.dart';
import '../features/dashboard/desktop_shell.dart';

class IlaiosDesktopApp extends StatelessWidget {
  const IlaiosDesktopApp({
    super.key,
    this.projection = const ControlPlaneProjection.unavailable(),
    this.onRefreshRequested,
  });

  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ILAIOS Desktop',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF3154A4)),
      ),
      home: DesktopShell(
        projection: projection,
        onRefreshRequested: onRefreshRequested,
      ),
    );
  }
}
