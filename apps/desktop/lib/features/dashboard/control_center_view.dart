import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'reference_workflows_view.dart';

/// Compatibility entry point for the Workflows destination.
///
/// The Workflows page is now rendered by [ReferenceWorkflowsView]. Canonical
/// shells provide [onNavigate] so in-surface actions use the persistent Desktop
/// navigation. Older compatibility shells may omit it and remain fail-closed
/// with an explicit notice rather than pretending navigation succeeded.
class ControlCenterView extends StatelessWidget {
  const ControlCenterView({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.onRefreshRequested,
    this.onNavigate,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final VoidCallback? onRefreshRequested;
  final ValueChanged<DesktopSection>? onNavigate;

  @override
  Widget build(BuildContext context) => ReferenceWorkflowsView(
        projection: projection,
        snapshot: operationalSnapshot,
        status: operationalStatus,
        onRefreshRequested: onRefreshRequested,
        onNavigate: onNavigate ?? (section) => _navigationNotice(context, section),
      );

  void _navigationNotice(BuildContext context, DesktopSection section) {
    final label = section.localizedLabel(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '$label: use the persistent Desktop navigation to open this destination.',
        ),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}
