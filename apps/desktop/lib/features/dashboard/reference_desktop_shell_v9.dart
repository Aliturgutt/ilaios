import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'reference_desktop_shell_v5.dart';

/// Final Home shell guard for the approved light/dark command-center design.
///
/// Unlike the earlier shell versions, resizing the Windows window never routes
/// back to the legacy responsive Home. Compact windows render the exact same
/// desktop design canvas and scale it uniformly, preserving one visual family
/// at every supported desktop size.
class ReferenceDesktopShellV9 extends StatelessWidget {
  const ReferenceDesktopShellV9({
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
    final sanitizedSnapshot = _withTruthfulProjectFallback(operationalSnapshot);
    final outerMedia = MediaQuery.of(context);

    Widget designCanvas() => MediaQuery(
          data: outerMedia.copyWith(textScaler: const TextScaler.linear(.90)),
          child: Stack(
            children: [
              ReferenceDesktopShellV5(
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
              const Positioned(
                left: 0,
                top: 0,
                width: 250,
                height: 94,
                child: _ReferenceBrandOverlay(),
              ),
            ],
          ),
        );

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1280 || constraints.maxHeight < 800;
        if (!compact) return designCanvas();

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
                child: designCanvas(),
              ),
            ),
          ),
        );
      },
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

/// Uses untouched canonical horizontal masters from the ILAIOS brand catalog.
/// The files under apps/desktop/assets/brand are byte-for-byte mirrors of the
/// canonical catalog blobs, placed inside Flutter's own asset root so Windows
/// release builds can always resolve them from AssetManifest at runtime.
class _ReferenceBrandOverlay extends StatelessWidget {
  const _ReferenceBrandOverlay();

  static const _darkAsset =
      '../../brand/assets/02-ilaios-primary-horizontal-dark.jpg';
  static const _lightAsset =
      '../../brand/assets/13-ilaios-primary-horizontal-light.jpg';

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final asset = isDark ? _darkAsset : _lightAsset;

    return IgnorePointer(
      child: Semantics(
        label: 'ILAIOS canonical brand lockup',
        image: true,
        child: Container(
          key: const Key('reference-brand-lockup-v9'),
          color: theme.colorScheme.surfaceContainerLow,
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          alignment: Alignment.centerLeft,
          child: Image.asset(
            asset,
            key: Key(
              isDark
                  ? 'reference-brand-horizontal-dark'
                  : 'reference-brand-horizontal-light',
            ),
            width: 210,
            height: 70,
            fit: BoxFit.contain,
            alignment: Alignment.centerLeft,
            filterQuality: FilterQuality.high,
            gaplessPlayback: true,
            errorBuilder: (context, error, stackTrace) => const SizedBox.shrink(
              key: Key('reference-brand-load-error'),
            ),
          ),
        ),
      ),
    );
  }
}
