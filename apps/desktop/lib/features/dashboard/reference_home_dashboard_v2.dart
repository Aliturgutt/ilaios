import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'reference_home_dashboard_v3.dart';

/// Compatibility entry point kept for the established Desktop shell.
///
/// The actual Home implementation lives in [ReferenceHomeDashboardV3]. Wide
/// Desktop windows with a short logical content height (for example 1280x800
/// after the shell bars are removed) uniformly fit a verified 720px Home
/// canvas instead of allowing a sub-pixel flex overflow or introducing a
/// page-level scroll. Normal reference sizes render natively at 1:1.
class ReferenceHomeDashboardV2 extends StatelessWidget {
  const ReferenceHomeDashboardV2({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  Widget _home() => ReferenceHomeDashboardV3(
        projection: projection,
        snapshot: snapshot,
        status: status,
        onNavigate: onNavigate,
        onRefreshRequested: onRefreshRequested,
      );

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth >= 1000 && constraints.maxHeight < 700) {
            return ClipRect(
              child: FittedBox(
                key: const Key('command-center-short-viewport-fit'),
                fit: BoxFit.contain,
                alignment: Alignment.topCenter,
                child: SizedBox(
                  width: constraints.maxWidth,
                  height: 700,
                  child: _home(),
                ),
              ),
            );
          }
          return _home();
        },
      );
}
