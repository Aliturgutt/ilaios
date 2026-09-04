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
/// The actual Home implementation lives in [ReferenceHomeDashboardV3], which
/// owns compact/short-window and text-scale scrolling. This compatibility
/// layer only preserves runtime/status sanitization and forwards the canonical
/// governed Home bindings; it must not add a second scrolling authority.
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
  Widget build(BuildContext context) => _home(context);
}
