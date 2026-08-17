import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'reference_desktop_shell_v10.dart';

/// Final resize guard for the approved Home design.
///
/// Wide windows render the reference-faithful V10 shell directly. Compact or
/// DPI-compressed Windows sizes scale that exact shell on a verified 1280x800
/// design canvas; they never route back to the legacy Home implementation.
class ReferenceDesktopShellV11 extends StatelessWidget {
  const ReferenceDesktopShellV11({
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

  Widget _shell() => ReferenceDesktopShellV10(
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

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final compact =
              constraints.maxWidth < 1280 || constraints.maxHeight < 800;
          if (!compact) return _shell();

          const designHeight = 800.0;
          final ratioMatchedWidth = constraints.maxHeight > 0
              ? constraints.maxWidth * designHeight / constraints.maxHeight
              : 1280.0;
          final designWidth = math.max(1280.0, ratioMatchedWidth);

          return ClipRect(
            key: const Key('reference-scaled-viewport-v9'),
            child: SizedBox.expand(
              child: FittedBox(
                fit: BoxFit.contain,
                alignment: Alignment.topLeft,
                child: SizedBox(
                  width: designWidth,
                  height: designHeight,
                  child: _shell(),
                ),
              ),
            ),
          );
        },
      );
}
