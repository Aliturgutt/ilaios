import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'reference_settings_view.dart';

/// Authority-preserving Costs surface retained for every historical shell.
/// Cost values are rendered only when the operational snapshot actually
/// exposes them; unsupported telemetry remains unavailable.
class CostsView extends StatelessWidget {
  const CostsView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  Widget build(BuildContext context) {
    final sources = <Map<String, Object?>>[
      snapshot.governanceState,
      snapshot.schedulerState,
      ..._mapList(snapshot.governanceState['costs']),
    ];
    final values = <({String label, String? value, IconData icon, Color accent})>[
      (
        label: context.tr('costs.totalUsd'),
        value: _firstValue(sources, const ['total_cost_usd', 'cost_usd']),
        icon: Icons.attach_money,
        accent: IlaiosTheme.enterpriseCyan,
      ),
      (
        label: context.tr('costs.totalMinor'),
        value: _firstValue(sources, const ['total_cost_minor', 'spent_minor', 'used_minor']),
        icon: Icons.calculate_outlined,
        accent: IlaiosTheme.coreBlue,
      ),
      (
        label: context.tr('costs.budgetUsd'),
        value: _firstValue(sources, const ['budget_usd']),
        icon: Icons.account_balance_wallet_outlined,
        accent: IlaiosTheme.violet,
      ),
      (
        label: context.tr('costs.budgetCapMinor'),
        value: _firstValue(sources, const ['budget_minor', 'hard_cap_minor']),
        icon: Icons.speed_outlined,
        accent: IlaiosTheme.coreBlue,
      ),
    ];
    final hasTelemetry = values.any((item) => item.value != null);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.paid_outlined, color: IlaiosTheme.coreBlue),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.tr('costs.title'),
                      style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w700),
                    ),
                    Text(
                      _localizedStatus(context, status),
                      style: TextStyle(
                        fontSize: 9.5,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final item in values)
                _CostMetric(
                  label: item.label,
                  value: item.value ?? context.tr('common.unavailable'),
                  icon: item.icon,
                  accent: item.accent,
                ),
              _CostMetric(
                label: context.tr('costs.tokenUsage'),
                value: context.tr('common.unavailable'),
                icon: Icons.token_outlined,
                accent: IlaiosTheme.enterpriseCyan,
              ),
              _CostMetric(
                label: context.tr('costs.gpuRuntime'),
                value: context.tr('common.unavailable'),
                icon: Icons.memory_outlined,
                accent: IlaiosTheme.violet,
              ),
              _CostMetric(
                label: context.tr('costs.providerModel'),
                value: context.tr('common.unavailable'),
                icon: Icons.hub_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
            ],
          ),
          if (!hasTelemetry) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(13),
              decoration: BoxDecoration(
                color: IlaiosTheme.coreBlue.withValues(alpha: .08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: IlaiosTheme.coreBlue.withValues(alpha: .25)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline, size: 18, color: IlaiosTheme.coreBlue),
                  const SizedBox(width: 9),
                  Expanded(
                    child: Text(
                      context.tr('costs.noTelemetry'),
                      style: const TextStyle(fontSize: 9),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Compatibility entry point used by every Desktop shell generation.
///
/// Existing callers keep their original constructor contract while the visible
/// surface is now the approved reference-faithful Settings design.
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

class _CostMetric extends StatelessWidget {
  const _CostMetric({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) => Container(
        width: 220,
        height: 96,
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 18, color: accent),
            const Spacer(),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 8.5,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ],
        ),
      );
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return value
      .whereType<Map<Object?, Object?>>()
      .map(
        (item) => item.map(
          (key, child) => MapEntry(key.toString(), child),
        ),
      )
      .toList(growable: false);
}

String? _firstValue(
  List<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final source in sources) {
    for (final key in keys) {
      final value = source[key];
      if (value == null) continue;
      final text = value.toString().trim();
      if (text.isNotEmpty) return text;
    }
  }
  return null;
}

String _localizedStatus(BuildContext context, String status) {
  final normalized = status.trim().toLowerCase();
  if (context.ilaiosLocale.locale != IlaiosLocale.turkish) return status;
  if (normalized.contains('not connected') ||
      normalized.contains('unavailable') ||
      normalized.contains('offline')) {
    return 'Yetkili çalışma zamanı kullanılamıyor';
  }
  if (normalized.contains('connected') || normalized.contains('operational')) {
    return 'Yetkili çalışma zamanı bağlı';
  }
  return status;
}
