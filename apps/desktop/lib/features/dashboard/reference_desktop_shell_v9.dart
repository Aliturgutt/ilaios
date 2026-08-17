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

class _ReferenceBrandOverlay extends StatelessWidget {
  const _ReferenceBrandOverlay();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return IgnorePointer(
      child: Semantics(
        label: 'ILAIOS',
        image: true,
        child: Container(
          key: const Key('reference-brand-lockup-v9'),
          color: scheme.surfaceContainerLow,
          padding: const EdgeInsets.fromLTRB(20, 17, 14, 15),
          alignment: Alignment.topLeft,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                width: 45,
                height: 45,
                child: CustomPaint(
                  painter: _IlaiosOrbitMarkPainter(
                    foreground: scheme.onSurface,
                    accent: const Color(0xFF00C2D1),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'ILAIOS',
                  maxLines: 1,
                  overflow: TextOverflow.clip,
                  style: TextStyle(
                    color: scheme.onSurface,
                    fontSize: 22.5,
                    height: 1,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 4.4,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _IlaiosOrbitMarkPainter extends CustomPainter {
  const _IlaiosOrbitMarkPainter({
    required this.foreground,
    required this.accent,
  });

  final Color foreground;
  final Color accent;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final outer = Rect.fromCircle(center: center, radius: size.width * .40);
    final inner = Rect.fromCircle(center: center, radius: size.width * .29);

    final mainPaint = Paint()
      ..color = foreground
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeCap = StrokeCap.round;
    final accentPaint = Paint()
      ..color = accent
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(outer, -.78, 2.10, false, mainPaint);
    canvas.drawArc(outer, 1.78, 1.48, false, mainPaint);
    canvas.drawArc(outer, 3.55, .58, false, accentPaint);
    canvas.drawArc(inner, -.28, 2.55, false, mainPaint);
    canvas.drawArc(inner, 2.72, 1.55, false, mainPaint);

    final stemX = center.dx;
    canvas.drawLine(
      Offset(stemX, size.height * .28),
      Offset(stemX, size.height * .69),
      accentPaint,
    );
    canvas.drawLine(
      Offset(size.width * .42, size.height * .28),
      Offset(size.width * .58, size.height * .28),
      mainPaint,
    );
    canvas.drawLine(
      Offset(size.width * .42, size.height * .70),
      Offset(size.width * .58, size.height * .70),
      mainPaint,
    );

    canvas.drawCircle(
      Offset(size.width * .78, size.height * .25),
      1.8,
      Paint()..color = accent,
    );
  }

  @override
  bool shouldRepaint(covariant _IlaiosOrbitMarkPainter oldDelegate) =>
      oldDelegate.foreground != foreground || oldDelegate.accent != accent;
}
