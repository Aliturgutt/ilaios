import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'desktop_shell.dart';
import 'reference_desktop_shell_v5.dart';

/// Hardened fixed-viewport Desktop routing guard for the approved reference.
///
/// The normal Windows dashboard keeps the complete Home composition in one
/// viewport without page-level scrolling. The reference UI uses a compact
/// typography scaler so fixed-height agent/artifact cards remain overflow-free
/// at the supported desktop geometry. Enlarged text deliberately falls back to
/// the verified responsive shell for accessibility.
class ReferenceDesktopShellV8 extends StatelessWidget {
  const ReferenceDesktopShellV8({
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

    final sanitizedSnapshot = _withTruthfulProjectFallback(operationalSnapshot);
    final media = MediaQuery.of(context);
    return MediaQuery(
      data: media.copyWith(textScaler: const TextScaler.linear(.90)),
      child: ReferenceDesktopShellV5(
        projection: projection,
        operationalSnapshot: sanitizedSnapshot,
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
      ),
    );
  }

  OperationalSnapshot _withTruthfulProjectFallback(OperationalSnapshot source) {
    if (source.liveEvents.isEmpty) return source;
    final events = <Map<String, Object?>>[
      for (final event in source.liveEvents) Map<String, Object?>.from(event),
    ];
    final latest = events.last;
    final hasProjectIdentity = <String>[
      'project_name',
      'project',
      'workspace',
      'goal',
      'objective',
    ].any((key) {
      final value = latest[key];
      return value is String && value.trim().isNotEmpty;
    });
    if (!hasProjectIdentity && latest.containsKey('job_id')) {
      latest['project_name'] = '—';
    }
    return OperationalSnapshot(
      runtimeRoutes: source.runtimeRoutes,
      schedulerState: source.schedulerState,
      grantsState: source.grantsState,
      governanceState: source.governanceState,
      evidenceRecords: source.evidenceRecords,
      liveEvents: events,
    );
  }
}
