import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'desktop_shell.dart';
import 'reference_desktop_shell_v2.dart';

/// Accessibility-aware entry point for the reference Desktop composition.
///
/// The approved wide composition is used from 1180 logical pixels upward.
/// At very high text scaling, a 1180–1399px window has materially less usable
/// horizontal/vertical space, so it deliberately falls back to the already
/// verified compact shell instead of clipping content. Normal-scale behavior
/// remains unchanged and the 1536x1024 reference continues to use the wide UI.
class ReferenceDesktopShellV3 extends StatelessWidget {
  const ReferenceDesktopShellV3({
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
  final Future<void> Function(
    String requestId,
    GovernanceDecision decision,
  )? onGovernanceDecision;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final textScale = MediaQuery.textScalerOf(context).scale(1);
          final accessibilityCompact =
              textScale >= 1.45 && constraints.maxWidth < 1400;

          if (accessibilityCompact) {
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

          return ReferenceDesktopShellV2(
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
        },
      );
}
