import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'reference_home_dashboard_v3.dart';

/// Compatibility entry point kept for the established Desktop shell.
///
/// The actual Home implementation now lives in [ReferenceHomeDashboardV3],
/// which matches the approved light/dark Main Control Center references while
/// preserving the same authoritative projection inputs and navigation contract.
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

  @override
  Widget build(BuildContext context) => ReferenceHomeDashboardV3(
        projection: projection,
        snapshot: snapshot,
        status: status,
        onNavigate: onNavigate,
        onRefreshRequested: onRefreshRequested,
      );
}
