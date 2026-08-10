import 'package:flutter/material.dart';

import '../control_plane/client.dart';
import '../control_plane/operational_snapshot.dart';
import '../control_plane/projection.dart';
import '../features/dashboard/desktop_shell.dart';
import 'ilaios_theme.dart';

class IlaiosDesktopApp extends StatelessWidget {
  const IlaiosDesktopApp({
    super.key,
    this.projection = const ControlPlaneProjection.unavailable(),
    this.operationalSnapshot = const OperationalSnapshot.unavailable(),
    this.operationalStatus = 'Operational APIs not connected',
    this.approverId,
    this.onRefreshRequested,
    this.onGovernanceDecision,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final String? approverId;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ILAIOS Desktop',
      debugShowCheckedModeBanner: false,
      theme: IlaiosTheme.dark,
      home: DesktopShell(
        projection: projection,
        operationalSnapshot: operationalSnapshot,
        operationalStatus: operationalStatus,
        approverId: approverId,
        onRefreshRequested: onRefreshRequested,
        onGovernanceDecision: onGovernanceDecision,
      ),
    );
  }
}
