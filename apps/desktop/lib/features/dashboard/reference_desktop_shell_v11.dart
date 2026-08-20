import 'dart:collection';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../create/governed_lifecycle_projection.dart';
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

  OperationalSnapshot _projectionSafeSnapshot() {
    final events = operationalSnapshot.liveEvents;
    if (events.isEmpty) return operationalSnapshot;
    return OperationalSnapshot(
      runtimeRoutes: operationalSnapshot.runtimeRoutes,
      schedulerState: operationalSnapshot.schedulerState,
      grantsState: operationalSnapshot.grantsState,
      governanceState: operationalSnapshot.governanceState,
      evidenceRecords: operationalSnapshot.evidenceRecords,
      liveEvents: _AuthoritySafeLiveEvents(
        events,
        schedulerState: operationalSnapshot.schedulerState,
        governanceState: operationalSnapshot.governanceState,
      ),
      agentState: operationalSnapshot.agentState,
    );
  }

  Widget _shell() => AgentProvisioningScope(
        onProvisionAgent: onProvisionAgent,
        child: HomeRuntimeBinding(
          userSession: userSession,
          onPromptSubmit: onPromptSubmit,
          child: ReferenceDesktopShellV10(
            projection: projection,
            operationalSnapshot: _projectionSafeSnapshot(),
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
      );

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
        if (!compact) return _shell();

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
                child: _shell(),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _AuthoritySafeLiveEvents extends ListBase<Map<String, Object?>> {
  _AuthoritySafeLiveEvents(
    this._events, {
    required Map<String, Object?> schedulerState,
    required Map<String, Object?> governanceState,
  }) : _authoritativeSources = <Map<String, Object?>>[
          schedulerState,
          governanceState,
        ];

  static const _authorityGroups = <List<String>>[
    <String>['session_id', 'workspace_session_id', 'run_id', 'execution_id'],
    <String>['started_at', 'start_time', 'session_started_at'],
    <String>['elapsed', 'duration', 'session_duration'],
    <String>['owner', 'principal_id', 'user', 'created_by'],
    <String>['workspace_mode', 'mode', 'execution_mode'],
    <String>['project_name', 'project', 'workspace', 'goal', 'objective'],
    <String>['branch', 'git_branch', 'source_branch'],
    <String>['environment', 'env', 'runtime_environment'],
    <String>['sync_state', 'synchronization', 'sync_status'],
    <String>['preview_url', 'browser_url', 'url', 'localhost_url'],
    <String>['last_save', 'saved_at', 'last_saved_at'],
  ];

  final List<Map<String, Object?>> _events;
  final List<Map<String, Object?>> _authoritativeSources;

  @override
  int get length => _events.length;

  @override
  set length(int value) => throw UnsupportedError('read-only projection');

  @override
  Map<String, Object?> operator [](int index) => _events[index];

  @override
  void operator []=(int index, Map<String, Object?> value) =>
      throw UnsupportedError('read-only projection');

  @override
  Map<String, Object?> get last {
    if (_events.isEmpty) throw StateError('No elements');
    final event = Map<String, Object?>.of(_events.last);
    for (final group in _authorityGroups) {
      if (_hasAuthoritativeValue(group)) {
        for (final key in group) {
          event.remove(key);
        }
      }
    }
    return event;
  }

  bool _hasAuthoritativeValue(List<String> keys) {
    for (final source in _authoritativeSources) {
      for (final key in keys) {
        final value = source[key];
        if (value is String && value.trim().isNotEmpty) return true;
        if (value is num || value is bool) return true;
      }
    }
    return false;
  }
}
