import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'reference_workflows_view.dart';

/// Compatibility entry point for the Workflows destination.
///
/// The Workflows page is now rendered by [ReferenceWorkflowsView]. The shell
/// keeps its existing public contract so Home and the remaining destinations
/// stay frozen while the page-by-page Desktop design pass continues.
class ControlCenterView extends StatelessWidget {
  const ControlCenterView({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => ReferenceWorkflowsView(
        projection: projection,
        snapshot: operationalSnapshot,
        status: operationalStatus,
        onRefreshRequested: onRefreshRequested,
        onNavigate: (section) => _navigationNotice(context, section),
      );

  void _navigationNotice(BuildContext context, DesktopSection section) {
    final label = section.localizedLabel(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$label: use the persistent Desktop navigation to open this destination.'),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}
