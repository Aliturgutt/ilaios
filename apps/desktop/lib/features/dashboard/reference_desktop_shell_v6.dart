import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'desktop_shell.dart';
import 'reference_desktop_shell_v5.dart';

/// Accessibility guard for the fixed reference dashboard.
///
/// The approved single-viewport composition is used at the normal Desktop text
/// scale. Enlarged text uses the already verified responsive shell so Windows
/// accessibility scaling cannot force clipped or overflowing fixed geometry.
class ReferenceDesktopShellV6 extends StatelessWidget {
  const ReferenceDesktopShellV6({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.themeMode = ThemeMode.dark,
    this.onThemeModeChanged,
    this.onSignIn,
    this.onLogout,
    this.onPromptSubmit,
    this.onSaveArtifact,
    this.onRefreshRequested,
    this.onGovernanceDecision,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final String? approverId;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  @override
  Widget build(BuildContext context) {
    final textScale = MediaQuery.textScalerOf(context).scale(1);
    if (textScale >= 1.2) {
      return DesktopShell(
        projection: projection,
        operationalSnapshot: operationalSnapshot,
        operationalStatus: operationalStatus,
        approverId: approverId,
        identityProviders: identityProviders,
        userSession: userSession,
        identityStatus: identityStatus,
        themeMode: themeMode,
        onThemeModeChanged: onThemeModeChanged,
        onSignIn: onSignIn,
        onLogout: onLogout,
        onPromptSubmit: onPromptSubmit,
        onSaveArtifact: onSaveArtifact,
        onRefreshRequested: onRefreshRequested,
        onGovernanceDecision: onGovernanceDecision,
      );
    }

    return ReferenceDesktopShellV5(
      projection: projection,
      operationalSnapshot: operationalSnapshot,
      operationalStatus: operationalStatus,
      approverId: approverId,
      identityProviders: identityProviders,
      userSession: userSession,
      identityStatus: identityStatus,
      themeMode: themeMode,
      onThemeModeChanged: onThemeModeChanged,
      onSignIn: onSignIn,
      onLogout: onLogout,
      onPromptSubmit: onPromptSubmit,
      onSaveArtifact: onSaveArtifact,
      onRefreshRequested: onRefreshRequested,
      onGovernanceDecision: onGovernanceDecision,
    );
  }
}
