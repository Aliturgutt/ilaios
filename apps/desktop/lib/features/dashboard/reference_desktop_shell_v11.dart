import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/desktop_identity_action_scope.dart';
import '../../identity/identity_client.dart';
import '../create/governed_lifecycle_projection.dart';
import '../deliveries/delivery_identity_scope.dart';
import 'agent_provisioning_scope.dart';
import 'home_runtime_binding.dart';
import 'reference_desktop_shell_v10.dart';

/// Final resize guard for the approved Desktop design.
///
/// Normal Windows client areas, including DPI-compressed viewports such as
/// 1382x733, render V10 at native 1:1 size so typography is not artificially
/// reduced. Smaller desktop windows use the bounded 1280x900 safety canvas
/// needed to preserve the complete approved composition without RenderFlex
/// overflow. The child V10 shell therefore never sees compact constraints when
/// this outer safety fit is active, avoiding double scaling.
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
    this.onProvisionAgent,
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
  final Future<void> Function(String agentId)? onProvisionAgent;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  Widget _shell() => DesktopIdentityActionScope(
        onSignIn: onSignIn,
        onLogout: onLogout,
        child: DeliveryIdentityScope(
          session: userSession,
          child: AgentProvisioningScope(
            onProvisionAgent: onProvisionAgent,
            child: HomeRuntimeBinding(
              userSession: userSession,
              onPromptSubmit: onPromptSubmit,
              child: ReferenceDesktopShellV10(
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
                onProvisionAgent: onProvisionAgent,
                onGovernanceDecision: onGovernanceDecision,
              ),
            ),
          ),
        ),
      );

  Widget _shellWithIdentityExit(BuildContext context) {
    final shell = _shell();
    if (userSession == null || onLogout == null) return shell;
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    return Stack(
      children: [
        Positioned.fill(child: shell),
        Positioned(
          top: 8,
          right: 12,
          child: Semantics(
            button: true,
            label: tr ? 'Google oturumundan çık' : 'Sign out of Google session',
            child: OutlinedButton.icon(
              key: const Key('desktop-identity-logout'),
              onPressed: onLogout,
              icon: const Icon(Icons.logout, size: 14),
              label: Text(tr ? 'Çıkış' : 'Sign out'),
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (userSession == null) {
      GovernedLifecycleProjectionStore.clear();
    } else {
      GovernedLifecycleProjectionStore.replace(operationalSnapshot);
    }
    return LayoutBuilder(
      builder: (context, constraints) {
        const compactWidthThreshold = 1320.0;
        const compactHeightThreshold = 720.0;
        const designWidthFloor = 1280.0;
        const designHeight = 900.0;

        final compact = constraints.maxWidth <= compactWidthThreshold ||
            constraints.maxHeight < compactHeightThreshold;
        if (!compact) return _shellWithIdentityExit(context);

        final ratioMatchedWidth = constraints.maxHeight > 0
            ? constraints.maxWidth * designHeight / constraints.maxHeight
            : designWidthFloor;
        final designWidth = math.max(designWidthFloor, ratioMatchedWidth);

        return ClipRect(
          key: const Key('reference-scaled-viewport-v9'),
          child: SizedBox.expand(
            child: FittedBox(
              fit: BoxFit.contain,
              alignment: Alignment.topLeft,
              child: SizedBox(
                width: designWidth,
                height: designHeight,
                child: _shellWithIdentityExit(context),
              ),
            ),
          ),
        );
      },
    );
  }
}
