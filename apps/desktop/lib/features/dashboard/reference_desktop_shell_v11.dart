import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/desktop_identity_action_scope.dart';
import '../../identity/identity_client.dart';
import '../create/governed_lifecycle_projection.dart';
import '../create/reference_asset_picker.dart';
import '../deliveries/delivery_identity_scope.dart';
import 'agent_provisioning_scope.dart';
import 'home_runtime_binding.dart';
import 'reference_desktop_shell_v10.dart';

/// Final resize guard for the approved Desktop design.
///
/// All supported Windows client areas preserve native Flutter typography and
/// the caller's text scaling. Each presentation surface owns its scrolling so
/// navigation and the status bar remain within the actual client area.
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
    this.referenceAssets,
    this.onThemeModeChanged,
    this.onSignIn,
    this.onLogout,
    this.onPromptSubmit,
    this.onSaveArtifact,
    this.onFetchLiState,
    this.onFetchLiMemories,
    this.onRememberLiMemory,
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
  final ReferenceAssetPickerController? referenceAssets;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final Future<DesktopLiState> Function()? onFetchLiState;
  final Future<List<DesktopLiMemory>> Function()? onFetchLiMemories;
  final Future<DesktopLiMemory> Function(String kind, String content)?
      onRememberLiMemory;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String agentId)? onProvisionAgent;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  Widget _shell() => ReferenceAssetPickerScope(
        controller: referenceAssets,
        child: DesktopIdentityActionScope(
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
                  referenceAssets: referenceAssets,
                  onThemeModeChanged: onThemeModeChanged,
                  onSignIn: onSignIn,
                  onLogout: onLogout,
                  onPromptSubmit: onPromptSubmit,
                  onSaveArtifact: onSaveArtifact,
                  onFetchLiState: onFetchLiState,
                  onFetchLiMemories: onFetchLiMemories,
                  onRememberLiMemory: onRememberLiMemory,
                  onRefreshRequested: onRefreshRequested,
                  onProvisionAgent: onProvisionAgent,
                  onGovernanceDecision: onGovernanceDecision,
                ),
              ),
            ),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    if (userSession == null) {
      GovernedLifecycleProjectionStore.clear();
    } else {
      GovernedLifecycleProjectionStore.replace(operationalSnapshot);
    }

    return SizedBox.expand(
      key: const Key('reference-responsive-viewport-v11'),
      child: _shell(),
    );
  }
}
