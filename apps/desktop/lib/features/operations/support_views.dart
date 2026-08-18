import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'reference_costs_view_v2.dart';
import 'reference_settings_view.dart';

/// Compatibility entry point used by every Desktop shell generation.
///
/// Existing callers keep their original constructor contract while the visible
/// surface is now the approved reference-faithful Costs design. Runtime cost
/// telemetry remains authority-derived and missing values stay unavailable.
class CostsView extends StatelessWidget {
  const CostsView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  Widget build(BuildContext context) => ReferenceCostsViewV2(
        snapshot: snapshot,
        status: status,
      );
}

/// Compatibility entry point used by every Desktop shell generation.
///
/// Existing callers keep their original constructor contract while the visible
/// surface is the approved reference-faithful Settings design.
class SettingsView extends StatelessWidget {
  const SettingsView({
    required this.projection,
    required this.identityStatus,
    required this.userSession,
    required this.providers,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String identityStatus;
  final DesktopUserSession? userSession;
  final List<IdentityProviderOption> providers;

  @override
  Widget build(BuildContext context) {
    final mode = Theme.of(context).brightness == Brightness.dark
        ? ThemeMode.dark
        : ThemeMode.light;
    return ReferenceSettingsView(
      projection: projection,
      identityStatus: identityStatus,
      userSession: userSession,
      providers: providers,
      themeMode: mode,
    );
  }
}
