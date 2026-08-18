import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'reference_costs_view_v3.dart';
import 'reference_settings_view.dart';
import 'usage_stats_view.dart';

/// Compatibility entry point used by every Desktop shell generation.
///
/// Existing callers keep their original constructor contract. The approved
/// reference-faithful Costs surface remains the default, while a bounded
/// Usage & Stats projection can be opened without adding a second telemetry
/// authority. Both surfaces render only authenticated OperationalSnapshot data.
class CostsView extends StatefulWidget {
  const CostsView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  State<CostsView> createState() => _CostsViewState();
}

class _CostsViewState extends State<CostsView> {
  var _showStats = false;

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    return Stack(
      children: [
        Positioned.fill(
          child: _showStats
              ? UsageStatsView(
                  snapshot: widget.snapshot,
                  status: widget.status,
                )
              : ReferenceCostsViewV3(
                  snapshot: widget.snapshot,
                  status: widget.status,
                ),
        ),
        Positioned(
          right: 22,
          bottom: 18,
          child: Semantics(
            button: true,
            label: _showStats
                ? (tr ? 'Maliyetler ekranına dön' : 'Return to Costs')
                : (tr ? 'Kullanım ve istatistikleri aç' : 'Open Usage & Stats'),
            child: FilledButton.tonalIcon(
              key: const Key('costs-stats-toggle'),
              onPressed: () => setState(() => _showStats = !_showStats),
              icon: Icon(
                _showStats ? Icons.paid_outlined : Icons.query_stats_outlined,
                size: 18,
              ),
              label: Text(
                _showStats
                    ? (tr ? 'Maliyetler' : 'Costs')
                    : (tr ? 'Kullanım ve İstatistikler' : 'Usage & Stats'),
              ),
            ),
          ),
        ),
      ],
    );
  }
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
