import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../../presentation/desktop_runtime_status.dart';
import '../navigation/desktop_section.dart';
import 'home_runtime_binding.dart';
import 'reference_home_dashboard_v3.dart';
import 'reference_home_truth_sanitizer.dart';

/// Compatibility entry point kept for the established Desktop shell.
///
/// The actual Home implementation lives in [ReferenceHomeDashboardV3]. Wide
/// Desktop windows with a short logical content height (for example 1280x800
/// after the shell bars are removed) preserve native typography size and allow
/// vertical scrolling of the verified 744px Home safety canvas instead of
/// shrinking the entire surface. Windows text scaling uses the same strategy:
/// the safety canvas grows with the system scale and remains vertically
/// scrollable rather than compressing or shrinking readable text.
class ReferenceHomeDashboardV2 extends StatelessWidget {
  const ReferenceHomeDashboardV2({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.userSession,
    this.onPromptSubmit,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final ValueChanged<DesktopSection> onNavigate;
  final DesktopUserSession? userSession;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final VoidCallback? onRefreshRequested;

  Widget _home(BuildContext context) {
    final binding = HomeRuntimeBinding.maybeOf(context);
    final locale = IlaiosLocaleScope.of(context).locale;
    final presentedStatus = presentDesktopRuntimeStatus(
      status,
      connected: projection.connected,
      turkish: locale == IlaiosLocale.turkish,
    );
    return ReferenceHomeDashboardV3(
      projection: projection,
      snapshot: sanitizeReferenceHomeSnapshot(snapshot),
      status: presentedStatus.label,
      userSession: userSession ?? binding?.userSession,
      onNavigate: onNavigate,
      onPromptSubmit: onPromptSubmit ?? binding?.onPromptSubmit,
      onRefreshRequested: onRefreshRequested,
    );
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          const baseSafetyHeight = 744.0;
          final textScale = MediaQuery.textScalerOf(context).scale(1);
          final scaledSafetyHeight = baseSafetyHeight * textScale.clamp(1.0, 1.5);
          final needsReadableScroll = constraints.maxWidth >= 1000 &&
              (constraints.maxHeight < baseSafetyHeight || textScale > 1.0);

          if (needsReadableScroll) {
            return SingleChildScrollView(
              key: const Key('command-center-short-viewport-scroll'),
              primary: false,
              physics: const ClampingScrollPhysics(),
              child: SizedBox(
                width: constraints.maxWidth,
                height: scaledSafetyHeight,
                child: _home(context),
              ),
            );
          }
          return _home(context);
        },
      );
}
